# NEXUS 수집잡 구조 및 운영 가이드

> 조사 기준: 2026-07-22 08:09 CEST
>
> 대상 소스: `/root/dev/nexus`
>
> 주요 범위: `ingest`, `meetup`, `brunch`, APScheduler 수집 체인

## 1. 개요

NEXUS의 수집 기능은 FastAPI 프로세스 내부의 APScheduler가 실행한다. 등록된 최상위 잡은 두 개다.

```text
FastAPI 시작
└─ APScheduler BackgroundScheduler 시작
   ├─ ingest_contents (60초 간격)
   │  └─ /contents/*.html → articles
   └─ collect_chain (12시간 간격)
      ├─ Brunch
      ├─ Event-us Meetup
      ├─ Luma AI
      ├─ Luma TECH
      └─ FastCampus
```

- `ingest`는 외부 크롤러가 아니라 내부 HTML 파일을 DB에 발행하는 작업이다.
- `brunch`는 최근 12시간 AI 관련 글 중 인기글 1건을 선정한다.
- `meetup`은 Event-us 및 Luma에서 찾은 신규 이벤트 전체를 저장한다.
- 신규 데이터가 반영되면 Redis 캐시 네임스페이스 버전을 올려 기존 조회 캐시를 즉시 무효화한다.

주요 코드:

- 앱 시작/종료: `backend/app/main.py`
- 잡 등록과 실행 체인: `backend/app/services/scheduler.py`
- 설정: `backend/app/config.py`
- 수동 실행 API: `backend/app/api/internal.py`
- 캐시: `backend/app/cache.py`

## 2. 스케줄러 메커니즘

### 2.1 앱 생명주기

`backend/app/main.py`의 FastAPI lifespan에서 캐시와 스케줄러가 시작된다.

1. Redis 연결을 시도해 `VersionedCache`를 생성한다.
2. `build_scheduler(cache)`로 APScheduler를 구성한다.
3. FastAPI 시작 시 `scheduler.start()`를 호출한다.
4. FastAPI 종료 시 `scheduler.shutdown(wait=False)`를 호출한다.

스케줄러는 별도 워커나 독립 서비스가 아니라 API 프로세스 안에서 실행된다.

### 2.2 등록 잡

`backend/app/services/scheduler.py` 기준:

| 잡 ID | 트리거 | 기본 주기 | 실행 함수 |
|---|---|---:|---|
| `ingest_contents` | interval | 60초 | `run_ingest_job()` |
| `collect_chain` | interval | 12시간 | `run_collect_chain_job()` |

기본 설정:

```text
CONTENTS_DIR=./contents
INGEST_INTERVAL_SECONDS=60
BRUNCH_COLLECT_INTERVAL_HOURS=12
COLLECT_CHAIN_INTERVAL_HOURS=12
MEETUP_QUERY=ai ax
MEETUP_CATEGORIES=IT/프로그래밍,경제/금융
MEETUP_WINDOW_DAYS=14
LUMA_CATEGORIES=cat-ai:AI,cat-tech:TECH
```

스케줄러 타임존은 UTC지만 cron의 고정 시각 실행이 아니라 프로세스 시작을 기준으로 한 interval 방식이다. API가 재시작되면 다음 실행 기준 시각도 다시 잡힌다.

### 2.3 수집 체인

12시간마다 아래 순서로 실행한다.

```text
Brunch → Event-us → Luma AI → Luma TECH → FastCampus
```

각 단계는 독립 DB 세션을 사용한다. 한 단계가 실패해도 예외를 로깅한 뒤 다음 단계로 진행한다. 외부 사이트 하나의 장애가 전체 체인이나 API 서버를 중단시키지 않는다.

다만 현재는 자동 재시도, 지수 백오프, 실패 알림 기능이 없다. 실패한 단계는 수동 실행하거나 다음 정기 주기를 기다려야 한다.

## 3. Ingest

### 3.1 역할

`ingest`는 Hermes/Telegram 글 작성 흐름이 `/contents`에 만든 HTML 파일을 `articles` 테이블에 등록한다.

관련 코드:

- `backend/app/services/ingest.py`
- `backend/app/services/ingest_parser.py`
- `backend/app/services/content_extract.py`
- `.claude/skills/nexus-writer/tools/save_article.py`

전체 흐름:

```text
Telegram 글감
→ nexus-writer 스킬
→ save_article.py
→ /contents/yyyymmdd_글유형_제목.html 저장
→ ingest_now() 즉시 실행
→ 실패 시 60초 스케줄러가 재스캔
→ articles 저장
→ 캐시 버전 증가
→ 화면 노출
```

### 3.2 파일명 규칙

```text
yyyymmdd_글유형_제목.html
```

허용 글 유형:

| 파일명의 글 유형 | DB `article_type` |
|---|---|
| 뉴스레터 | `newsletter` |
| 컬럼 | `column` |
| 가이드 | `guide` |

예시:

```text
20260707_가이드_회의록요약,LLM에게맡기는법.html
```

날짜 형식, 글 유형, 제목이 규칙에 맞지 않으면 해당 파일만 `skipped` 처리한다.

### 3.3 즉시 반영과 안전망

`save_article.py`는 파일을 쓴 직후 `ingest_now()`를 호출한다. 즉시 반영이 성공하면 60초를 기다리지 않고 DB와 화면에 반영된다.

`ingest_now()`는 best-effort 방식이다. DB나 캐시 장애가 나도 작성 작업에 예외를 전파하지 않고 `None`을 반환한다. 파일이 남아 있으므로 60초 주기 `ingest_contents` 잡이 같은 `scan_contents_dir()` 경로를 다시 실행한다.

### 3.4 저장 필드

`_ingest_file()`이 생성하는 Article의 주요 값:

- `category`: `curation`
- `source_type`: `internal`
- `article_type`: 파일명의 글 유형
- `title`: HTML 제목이 있으면 HTML 제목, 없으면 파일명 제목
- `summary`: HTML에서 추출
- `body_html`: HTML 본문
- `key_visual_html`: 키 비주얼 HTML/SVG
- `author_name`: HTML 저자, 없으면 `BC카드 AI사업팀`
- `content_filename`: 원본 파일명
- `read_minutes`: HTML 값, 없으면 4
- `published_at`: 파일명 날짜의 UTC 00:00

### 3.5 중복과 동시성

중복 키는 `articles.content_filename`이다.

1. 배치 시작 시 기존 파일명을 한 번에 조회한다.
2. 기존 파일은 `already`로 계산하고 건너뛴다.
3. DB UNIQUE 제약이 최종 방어선이다.
4. 즉시 실행과 스케줄러가 경합해 UNIQUE 충돌이 발생하면 해당 파일을 `already`로 처리하고 나머지 파일을 계속 처리한다.

### 3.6 캐시와 오류 처리

배치에서 신규 글이 하나 이상 등록된 경우에만 캐시 버전을 한 번 증가시킨다. 변화가 없으면 기존 캐시를 유지한다.

파일 하나의 파싱 오류는 전체 배치를 중단하지 않는다. 다만 잘못된 파일을 별도 격리하거나 이동하지 않기 때문에 파일이 `/contents`에 남으면 60초마다 반복 검사되고 경고 로그가 누적될 수 있다.

Ingest에는 별도 실행 이력 테이블이 없다. 결과는 반환값과 로그로만 확인한다.

## 4. Meetup

### 4.1 수집 범위

현재 Meetup 도메인에는 다음 외부 소스가 들어간다.

- Event-us
- Luma AI
- Luma TECH

주요 코드:

- `backend/app/services/meetup_fetcher.py`
- `backend/app/services/meetup_collector.py`
- `backend/app/services/luma_fetcher.py`
- `backend/app/services/scheduler.py`

### 4.2 Event-us 조회 조건

호출 API:

```text
POST https://api.event-us.kr/api/v1/engine/search
```

기본 조건:

- 검색어: `ai ax`
- 카테고리: `IT/프로그래밍`, `경제/금융`
- 상태: `Start`
- 공개 상태: `open`
- 제외 이벤트가 아닌 항목
- 행사 시작일: KST 기준 오늘부터 14일 이내
- 페이지 크기: 12
- 최대 페이지: 30
- 정렬: 검색 점수 내림차순, ID 내림차순

모든 페이지를 순회하며 `source_url` 기준으로 응답 내 중복을 제거한다.

중간 페이지에서 HTTP 오류가 발생하면 그때까지 모은 후보를 반환한다. 가용성은 높지만 부분 수집이 `success`로 기록될 수 있다.

### 4.3 후보 데이터

각 후보는 다음 값을 가진다.

- 외부 `source_id`
- 제목과 주최자
- 원본 URL
- 시작/종료 시각
- 장소, 지역, 주소
- 최소 가격과 무료 여부
- 조회수
- 행사 방식과 카테고리
- 커버 이미지

### 4.4 DB 반영

`collect_meetups()`는 Brunch와 달리 신규 후보 전체를 저장한다.

중복 키:

- `meetup_events.source_url`
- `meetup_events.source_id`

두 컬럼 모두 DB UNIQUE 제약이 있다. 기존 DB 데이터뿐 아니라 같은 배치 안의 중복도 제거한다.

각 신규 이벤트는 SAVEPOINT 안에서 저장한다. 동시 실행 때문에 한 건에서 UNIQUE 충돌이 발생해도 해당 이벤트만 건너뛰고 나머지 이벤트는 계속 저장한다. NOT NULL이나 FK 오류와 같은 실제 데이터 결함은 전체 배치 실패로 전파한다.

### 4.5 수집 이력

`meetup_collect_runs`에 다음 값을 기록한다.

- `status`: `success`, `empty`, `failed`
- 후보 수
- 신규 추가 수
- 오류 메시지
- 실행 시각

신규 이벤트가 하나 이상 추가된 경우에만 캐시 버전을 증가시킨다.

### 4.6 현재 동작의 한계

현재 Meetup 수집기는 신규 이벤트 추가 전용이다. 기존 `source_id` 또는 `source_url`이 있으면 후보를 건너뛴다.

따라서 원본의 다음 변경은 기존 DB에 동기화되지 않는다.

- 제목, 시간, 장소 변경
- 가격 변경
- 조회수 증가
- 이미지 변경
- 행사 취소 또는 삭제

원본에서 사라진 이벤트를 숨기거나 만료 처리하는 로직도 없다.

또한 수동 `/api/internal/meetup/run`은 Event-us와 모든 Luma 후보를 합쳐 한 번에 저장하지만, 정기 수집 체인은 소스별로 `collect_meetups()`를 호출한다. 따라서 수동 실행과 정기 실행의 이력 행 단위가 다르다.

## 5. Brunch

### 5.1 후보 조회

관련 코드:

- `backend/app/services/brunch_fetcher.py`
- `backend/app/services/brunch.py`
- `backend/app/services/publish.py`

기본 조회 URL:

```text
https://brunch.co.kr/keyword/인공지능
```

키워드 페이지의 서버 렌더링 스크립트에 들어 있는 다음 데이터를 추출한다.

```javascript
var articleList = [...]
```

후보 값:

- 제목
- 원본 URL
- 작가
- 좋아요 수
- 댓글 수
- 요약
- 원본 발행 시각
- 썸네일 URL

썸네일은 `kakaocdn.net` 도메인만 허용하고 HTTP URL은 HTTPS로 변환한다.

### 5.2 시간 창과 AI 필터

후보 중 다음 12시간 창에 들어오는 글만 남긴다.

```text
현재 시각 - 12시간 <= 원본 발행 시각 < 현재 시각
```

제목과 요약에 다음 키워드 중 하나가 포함되어야 한다.

```text
ai, 인공지능, 머신러닝, 딥러닝, 생성형, gpt, llm,
챗봇, 프롬프트, 클로드, 제미나이, copilot, 코파일럿, 에이전트
```

이미 저장된 `source_url`은 제외한다.

### 5.3 인기글 선정

신규 AI 후보 중 다음 점수가 가장 높은 글 한 건만 선정한다.

```text
좋아요 수 + 댓글 수
```

동점인 경우 Python `max()` 특성상 후보 목록에서 먼저 나온 글이 선택된다.

### 5.4 DB 저장

선정 글은 `articles`에 다음 형태로 저장된다.

- `category`: `curation`
- `article_type`: `column`
- `source_type`: `brunch`
- `source_url`: Brunch 원본 URL
- `body_html`: 없음
- 제목, 요약, 작가, 썸네일
- 좋아요 수와 댓글 수

중복 키는 `articles.source_url`이며 DB UNIQUE 제약이 있다.

중요한 세부사항: 후보에 원본 `published_at`이 존재하지만 실제 Article의 `published_at`에는 수집 윈도우의 `window_end`, 즉 NEXUS 수집 시각을 저장한다. 목록 정렬은 Brunch 원본 게시 시각이 아니라 NEXUS 수집 시각 기준이다.

### 5.5 수집 이력

`brunch_collect_runs` 필드:

- 수집 시간 창 시작/종료
- `status`: `success`, `empty`, `duplicate`, `failed`
- 시간 창 내 후보 수
- 선정된 Article ID
- 오류 메시지
- 실행 시각

`empty`는 다음 상황을 하나로 표현한다.

- 시간 창 내 후보 없음
- AI 키워드 조건을 만족하는 후보 없음
- AI 후보가 모두 이미 저장됨

동시 실행으로 이미 저장된 URL에서 UNIQUE 충돌이 발생하면 실패가 아니라 `duplicate`로 기록한다.

## 6. 수동 실행 API

`backend/app/api/internal.py`는 스케줄러와 같은 코드 경로를 수동으로 실행한다.

| API | 기능 |
|---|---|
| `POST /api/internal/ingest/run` | `/contents` 즉시 스캔 |
| `POST /api/internal/meetup/run` | Event-us + Luma 전체 수집 |
| `POST /api/internal/brunch/run` | Brunch 즉시 수집 |
| `POST /api/internal/classes/run` | FastCampus 즉시 수집 |

외부 포트 80의 Nginx는 `/api/internal/` 요청에 HTTP 403을 반환한다.

주의: FastAPI 자체의 내부 API에는 인증 의존성이 없다. 현재 백엔드가 Hermes Agent 서버의 `0.0.0.0:8000`에 직접 바인딩되어 있으므로 네트워크/방화벽에서 8000 포트를 허용하면 Nginx 차단을 우회할 수 있다.

## 7. 캐시 무효화

`VersionedCache`는 다음 형태의 키를 사용한다.

```text
{prefix}v{version}:{key}
```

쓰기 성공 시 Redis의 버전 키를 원자적으로 `INCR`한다. 이후 조회는 새 버전의 키를 사용하므로 이전 캐시를 순회 삭제하지 않고 O(1)로 전체 무효화한다.

Redis 장애 처리:

- GET 실패: 캐시 미스로 처리하고 DB 조회
- SET 실패: 캐시 저장 생략
- INCR 실패: 버전 증가 생략
- 앱 시작 시 Redis 연결 실패: 프로세스 내부 메모리 캐시로 폴백

캐시는 수집과 API의 단일 장애점이 되지 않도록 설계되어 있다.

## 8. 현재 운영 구성과 데이터 현황

조사 시점의 실제 서비스 구성:

```text
nexus-frontend-production 컨테이너
├─ 외부 포트 80
├─ Nginx + 정적 프런트엔드
└─ /api 요청 → host.docker.internal:8000

Hermes Agent 서버 호스트
└─ Uvicorn 0.0.0.0:8000
   ├─ FastAPI
   └─ APScheduler

nexus-pg 컨테이너
└─ PostgreSQL, 서버 포트 5432

nexus-redis 컨테이너
└─ Redis, 서버 포트 6379
```

저장소의 `docker-compose.yml` 전체 스택은 조사 시점에 실행 중이 아니었고, 프런트엔드 컨테이너와 서버 호스트의 Uvicorn을 조합한 형태로 서비스되고 있었다.

운영 PostgreSQL 현황:

| 항목 | 건수 |
|---|---:|
| 내부 Article (`source_type=internal`) | 7 |
| Brunch Article (`source_type=brunch`) | 16 |
| Brunch 수집 이력 | 16 |
| Meetup 이벤트 | 143 |
| Meetup 수집 이력 | 42 |

현재 `/contents`의 HTML 1개는 DB Article ID 7로 반영되어 있다.

최근 Brunch 실행 예:

```text
2026-07-22 04:31 UTC
status=success
window candidates=5
picked_article_id=27
```

최근 Meetup 실행에서는 후보 99건 중 신규 0건이 `success`로 기록되었고, 이전 실행 중 후보 77건에서 신규 1건이 추가된 기록이 있다.

운영 현황 수치는 조사 시점의 스냅샷이며 이후 달라질 수 있다.

## 9. 장점과 개선 필요 사항

### 9.1 잘 되어 있는 부분

- 재실행해도 중복 저장되지 않는 멱등성
- 애플리케이션 사전 조회와 DB UNIQUE 제약의 이중 방어
- 스케줄러와 수동 실행의 동시 수집 레이스 처리
- Meetup의 이벤트별 SAVEPOINT
- 외부 소스 하나가 실패해도 다음 수집 단계 진행
- 신규 데이터 반영 후 즉시 캐시 무효화
- Redis 장애가 DB 쓰기와 API 가용성을 중단하지 않도록 폴백
- 수동 실행과 자동 실행이 핵심 수집 함수를 공유

### 9.2 개선 필요 사항

1. 스케줄러가 API 프로세스 내부에 있어 API 재시작 시 interval 기준 시각이 재설정된다.
2. API 다중 워커를 사용하면 워커마다 스케줄러가 실행될 수 있다.
3. APScheduler 잡 저장소가 영속적이지 않다.
4. 자동 재시도, 백오프, 실패 알림이 없다.
5. Ingest 전용 실행 이력 테이블이 없다.
6. 잘못된 ingest 파일을 격리하지 않아 60초마다 반복 검사한다.
7. Meetup이 기존 이벤트 변경과 취소/삭제를 동기화하지 않는다.
8. Event-us 중간 페이지 실패가 부분 수집 `success`로 남을 수 있다.
9. Brunch `empty` 상태만으로 빈 결과의 원인을 구분할 수 없다.
10. Brunch Article이 원본 게시 시각 대신 수집 시각을 사용한다.
11. 수동 Meetup과 정기 Meetup의 수집 이력 단위가 다르다.
12. 백엔드 8000 포트 직접 접근 시 내부 API의 Nginx 차단을 우회할 수 있다.
13. `scheduler.py` 상단 설명과 일부 기존 아키텍처 문서가 현재의 Meetup/Luma/FastCampus 체인을 완전히 반영하지 못한다.

## 10. 검증

다음 테스트 모듈을 실제 실행했다.

```text
test/backend/test_scheduler.py
test/backend/test_ingest_service.py
test/backend/test_meetup_collector.py
test/backend/test_meetup_fetcher.py
test/backend/test_brunch.py
test/backend/test_brunch_fetcher.py
```

결과:

```text
47 passed
```

검증 범위에는 잡 등록 주기, 체인 순서와 실패 격리, ingest 즉시 반영과 중복 처리, Meetup 후보 수집과 동시성, Brunch 파싱·AI 필터·인기글 선정·중복 처리가 포함된다.
