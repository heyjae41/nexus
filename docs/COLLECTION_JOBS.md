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
      ├─ FastCampus
      ├─ Daker Hackathons
      └─ DACON Competitions
```

- `ingest`는 외부 크롤러가 아니라 내부 HTML 파일을 DB에 발행하는 작업이다.
- `brunch`는 최근 12시간 AI 관련 글 중 키워드별 인기글을 최대 1건씩 선정한다.
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
Brunch → Event-us → Luma AI → Luma TECH → FastCampus → Daker → DACON
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

조회 URL:

```text
https://brunch.co.kr/keyword/인공지능
https://brunch.co.kr/keyword/AI
https://brunch.co.kr/keyword/머신러닝
https://brunch.co.kr/keyword/데이터과학
```

각 URL은 서로 독립적으로 후보를 조회하고 선정한다.

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
ai, 인공지능, 머신러닝, 데이터과학, 딥러닝, 생성형, gpt, llm,
챗봇, 프롬프트, 클로드, 제미나이, copilot, 코파일럿, 에이전트
```

이미 저장된 `source_url`은 제외한다.

### 5.3 인기글 선정

각 키워드 페이지의 신규 AI 후보 중 다음 점수가 가장 높은 글을 한 건씩 선정한다.

```text
좋아요 수 + 댓글 수
```

따라서 한 주기에서 정상적으로 최대 4건이 선정된다. 같은 글이 여러 키워드
페이지에 겹치면 먼저 처리된 키워드에서 저장되고, 이후 키워드에서는 기존
`source_url`을 제외한 차순위 글을 선정한다. 해당 키워드에 시간 창 내 신규
후보가 없으면 실제 선정 건수는 4건보다 적을 수 있다.

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

`brunch_collect_runs`에는 키워드별로 실행 이력 한 행이 기록되므로 정기 수집
한 주기에 최대 4개의 이력 행이 생성된다. 현재 테이블에는 키워드 컬럼이 없어
이력 행만으로 어느 키워드의 실행인지 직접 식별할 수는 없다.

필드:

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

## 6. Classes (FastCampus · Daker · DACON)

### 6.1 역할과 실행 주기

클래스 영역은 FastCampus AI 과정뿐 아니라 Daker의 모집중·진행중 해커톤과
DACON의 참가신청중 경진대회를 `courses` 테이블에 동기화한다. FastCampus는
지정 배지 과정을 수집하고, Daker/DACON은 현재 참가 가능한 항목만 수집한다.
모든 소스는 신규 추가, 기존 항목 갱신, 더 이상 대상이 아닌 항목 숨김을 수행한다.

관련 코드:

- `backend/app/services/fastcampus_fetcher.py`
- `backend/app/services/fastcampus_collector.py`
- `backend/app/services/daker_fetcher.py`
- `backend/app/services/dacon_fetcher.py`
- `backend/app/services/class_opportunities.py`
- `backend/app/repositories/courses.py`
- `backend/app/api/routes.py`

정기 실행은 12시간 `collect_chain`의 마지막 세 단계다.

```text
Brunch → Event-us → Luma AI → Luma TECH → FastCampus → Daker → DACON
```

### 6.2 대상 카테고리

| 코드 | 표시명 | 예상 외부 카테고리 ID | 페이지 |
|---|---|---:|---|
| `DATASCIENCEDL` | AI TECH | 39 | `/category_online_datasciencedl` |
| `AICREATIVE` | AI CREATIVE | 921 | `/category_online_aicreative` |
| `BIZ` | AI/업무생산성 | 1 | `/category_online_biz` |

응답의 카테고리 ID가 예상값과 다르면 사이트 스키마나 라우팅이 바뀐 것으로
간주하고 수집을 실패시킨다.

### 6.3 외부 API 조회

수집기는 다음 FastCampus 공개 API를 사용한다.

```text
GET /.api/courses/recommended/best
GET /.api/courses/marketing/latest
GET /.api/categories/{category_code}
GET /.api/courses/products?id={course_ids}
```

처리 순서:

1. 전체 BEST 과정 ID를 조회한다.
2. 전체 NEW 과정 ID를 조회한다.
3. 세 카테고리의 과정 목록과 원본 순위를 조회한다.
4. 대상 배지가 하나 이상 있는 과정만 선택한다.
5. 선택한 과정 ID를 최대 100개씩 묶어 상품/가격 정보를 조회한다.
6. 과정과 상품 정보를 `FastCampusCandidate`로 변환한다.

상품이 여러 개면 `state=NORMAL`이고 구매 가능한 상품을 우선 사용한다. 해당
상품이 없으면 첫 번째 상품을 사용하고, 상품 자체가 없으면 가격은 `NULL`이 된다.

### 6.4 후보 선정 기준

허용 배지:

```text
얼리버드, 인기 급상승, BEST, NEW
```

- `BEST`: recommended/best API의 카테고리별 ID 목록
- `NEW`: marketing/latest API의 카테고리별 ID 목록
- `얼리버드`, `인기 급상승`: 과정 카드의 `highlightBadgeTitle`

하나의 과정이 여러 배지를 가질 수 있다. 같은 과정 ID가 여러 카테고리에
등장하면 앞서 처리한 카테고리의 후보 하나만 유지한다. 일반 과정처럼 대상
배지가 하나도 없는 과정은 수집하지 않는다.

### 6.5 후보 필드

DB에 반영할 후보에는 다음 정보가 포함된다.

- 외부 과정 ID와 카테고리 코드/표시명/페이지 URL
- 카테고리 내 원본 순위
- 제목과 요약
- 과정 URL과 썸네일
- 하위 카테고리와 과정 형식
- 수강 자격
- 러닝타임(분)
- 판매가와 정가
- 복수 배지

러닝타임 `HH:MM`은 분 단위로 변환하며, 파싱할 수 없으면 `NULL`로 둔다.

### 6.6 Upsert와 숨김 처리

중복 식별자는 `courses.source_id`이며 `source_id`와 `source_url` 모두 DB UNIQUE
제약이 있다.

수집 결과 반영:

- 신규 ID: `Course` 추가, `status=published`
- 기존 ID: 제목, 가격, 배지, 순위 등 변경 필드 갱신
- 이전에는 공개됐지만 이번 완료 카테고리 후보에 없는 ID: `status=hidden`
- 숨김 과정이 다시 후보에 들어오면 `status=published`로 복구

숨김은 수집을 완료한 카테고리에만 적용한다. 일부 카테고리만 수집한 경우 다른
카테고리의 과정을 잘못 숨기지 않는다. 실제 목록 API도 `status=published`만
반환하므로 숨김 처리는 사용자 화면에서 즉시 제외되는 효과가 있다.

### 6.7 불완전 응답 방어

외부 API 장애나 스키마 변경으로 공개 과정을 대량 숨기는 사고를 막기 위해
fail-closed 검증을 수행한다.

- 전체 후보 또는 완료 카테고리가 비어 있으면 반영 중단
- 완료되지 않은 카테고리 후보가 섞이면 반영 중단
- 완료 카테고리마다 후보가 최소 1건은 있어야 함
- 기존 공개 과정이 4건 이상인 카테고리에서 신규 후보가 기존의 절반 미만으로
  급감하면 반영 중단
- 카테고리 ID 불일치, 빈 과정 목록, 필수 필드 누락, 상품 응답 형식 오류 시 실패
- 세 카테고리/API 중 하나라도 실패하면 전체 후보 반영을 수행하지 않음

검증 실패 시 기존 공개/숨김 상태를 롤백하고 `failed` 실행 이력만 별도 커밋한다.

### 6.8 동시성과 트랜잭션

동일 프로세스에서는 `threading.Lock`으로 수동 실행과 스케줄 실행을 직렬화한다.
PostgreSQL에서는 transaction advisory lock을 추가로 사용해 여러 API 프로세스가
동시에 같은 배치를 반영하지 못하게 한다.

후보 검증, upsert, 숨김, 성공 이력은 하나의 DB 트랜잭션으로 커밋된다. 실패하면
전체 변경을 롤백한 뒤 실패 이력을 기록한다.

### 6.9 캐시와 수집 이력

`fastcampus_collect_runs`에는 다음을 기록한다.

- 상태: `success`, `failed`
- 후보 수
- 신규 추가 수
- 변경 갱신 수
- 숨김 수
- 오류 메시지와 실행 시각

신규·갱신·숨김 중 하나라도 발생한 경우에만 캐시 버전을 증가시킨다. 완전히
동일한 멱등 실행에서는 캐시를 유지한다.

### 6.10 목록 API

```text
GET /api/classes?page=1&size=20
GET /api/classes?category=DATASCIENCEDL
GET /api/classes?category=AICREATIVE
GET /api/classes?category=BIZ
GET /api/classes?category=DAKER
GET /api/classes?category=DACON
```

공개 항목만 반환하며 정렬 순서는 AI TECH → AI CREATIVE → AI/업무생산성 →
해커톤 → 경진대회, 각 카테고리 안에서는 원본 순위 순이다. 원본 링크에는
`ref=nexus.bccard.ai`를 붙이고 외부 링크로 직렬화한다. 응답의 `sourceType`은
`fastcampus`, `daker`, `dacon` 중 하나이며, 프런트엔드는 이를 사용해 강의의
가격/학습시간 카드와 해커톤·경진대회의 상태/총상금 카드를 구분한다.

### 6.11 현재 운영 현황

조사 시점 FastCampus 공개 API 결과:

| 카테고리 | 후보 수 |
|---|---:|
| AI TECH | 19 |
| AI CREATIVE | 16 |
| AI/업무생산성 | 21 |
| 합계 | 56 |

후보의 배지 출현 수는 `NEW` 33, `BEST` 16, `인기 급상승` 9, `얼리버드` 4다.
한 과정이 여러 배지를 가질 수 있으므로 배지 합계는 후보 수보다 클 수 있다.

운영 DB에는 과정 62건(공개 56, 숨김 6)과 수집 이력 18건이 있다. 최근 정기
실행은 후보 56건을 처리해 신규 0건, 갱신 13건, 숨김 1건으로 성공했다.

### 6.12 Daker 해커톤

공식 공개 API:

```text
GET https://daker.ai/api/hackathons/public-list
```

다음 조건을 모두 만족하는 항목만 가져온다.

- `status == published`
- `isPracticeMode != true`
- `lastStageEndDate` 또는 `endDate`가 현재 UTC 시각 이후
- `registrationDeadline`이 현재 시각 이후면 `모집중`, 이미 지났지만 대회 종료
  전이면 `진행중`

상태와 종료일 필드가 누락되면 후보 0건으로 간주하지 않고 스키마 오류로
수집을 중단한다. 외부 ID에는 `daker:` 접두어를 붙이며, 제목·tagline·주최사·
상금·헤더 이미지·slug 상세 링크를 저장한다. 2026-07-22 실제 공개 API 검증
결과는 모집중 5건, 진행중 1건이다.

### 6.13 DACON 경진대회

공식 공개 API:

```text
GET https://app.dacon.io/api/v1/competition/list?offset={page}&range=
```

0페이지부터 페이지당 15건을 순회하며 15건 미만 페이지에서 종료한다. 무한
페이지 순회를 막기 위해 최대 50페이지까지만 허용한다. 화면의 `참가신청중`과
동일하게 다음 조건을 모두 만족하는 항목만 가져온다.

- `practice == 1`
- KST로 해석한 `period_start`가 아직 미래이거나 `period_dday >= 0`

세 상태 필드가 누락되거나 값 형식이 바뀌면 스키마 오류로 중단한다. 외부 ID에는
`dacon:` 접두어를 붙이며, 제목·키워드·상금·로고·공식 overview 링크를 저장한다.
API의 `prize`는 만원 단위이므로 원 단위로 변환한다. 2026-07-22 실제 공개 API
검증 결과는 참가신청중 1건이다.

### 6.14 소스 간 중복과 동기화

Daker/DACON 후보는 다음 순서로 중복을 판정한다.

1. 같은 소스의 접두어 포함 `source_id`가 있으면 갱신 대상으로 식별한다.
2. 갱신 대상 자신을 제외한 모든 기존 행 및 같은 배치 후보의 정규화 URL이 같으면
   반영을 건너뛴다. URL 비교 시 query/fragment와 끝 `/`를 제거하고 scheme/host를
   소문자로 바꾼다.
3. 갱신 대상 자신을 제외한 공개 중인 모든 소스 및 같은 배치 후보의 정규화 제목이
   같으면 반영을 건너뛴다. 제목은 Unicode NFKC와 casefold를 적용한 뒤 공백·
   문장부호를 제거한다.
4. 이번 정상 응답에서 사라졌거나 중복으로 건너뛴 같은 소스의 기존 공개 항목은
   `status=hidden`으로 바꾼다. 다시 대상 상태가 되고 중복도 없으면 `published`로
   복구한다.

따라서 FastCampus·Daker·DACON 간 제목 중복도 저장하지 않는다. 숨김 제목은
새로운 활성 항목을 가로막지 않지만, DB의 `source_url UNIQUE` 제약을 지키기 위해
동일 URL은 숨김 상태여도 중복으로 처리한다.

동일 프로세스는 `threading.Lock`, PostgreSQL은 transaction advisory lock으로
수동·정기 실행을 직렬화한다. 신규·갱신·숨김이 있으면 캐시 버전을 증가시킨다.

## 7. 수동 실행 API

`backend/app/api/internal.py`는 스케줄러와 같은 코드 경로를 수동으로 실행한다.

| API | 기능 |
|---|---|
| `POST /api/internal/ingest/run` | `/contents` 즉시 스캔 |
| `POST /api/internal/meetup/run` | Event-us + Luma 전체 수집 |
| `POST /api/internal/brunch/run` | Brunch 즉시 수집 |
| `POST /api/internal/classes/run` | FastCampus + Daker + DACON 즉시 수집 |

클래스 수동 실행은 세 외부 응답을 모두 먼저 조회·검증한 뒤 DB 반영을 시작한다.
응답에는 전체 합계와 `sources.fastcampus`, `sources.daker`, `sources.dacon`별
`candidates`, `added`, `updated`, `hidden`, `skipped` 수가 포함된다.

외부 포트 80의 Nginx는 `/api/internal/` 요청에 HTTP 403을 반환한다. FastAPI
자체의 내부 API에는 인증 의존성이 없으므로 운영 Uvicorn은 Hermes Agent 서버의
`127.0.0.1:8000`에만 바인딩한다. host network를 사용하는 Nginx 컨테이너만
`127.0.0.1:8000`으로 일반 API를 프록시하며, 8000 포트를 외부에 열지 않는다.

## 8. 캐시 무효화

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

## 9. 현재 운영 구성과 데이터 현황

조사 시점의 실제 서비스 구성:

```text
nexus-frontend-production 컨테이너
├─ 외부 포트 80
├─ Nginx + 정적 프런트엔드
├─ host network
└─ /api 요청 → 127.0.0.1:8000

Hermes Agent 서버 호스트
└─ Uvicorn 127.0.0.1:8000
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
| FastCampus 과정 | 62 |
| FastCampus 공개 과정 | 56 |
| FastCampus 숨김 과정 | 6 |
| FastCampus 수집 이력 | 18 |

현재 `/contents`의 HTML 1개는 DB Article ID 7로 반영되어 있다.

최근 Brunch 실행 예:

```text
2026-07-22 04:31 UTC
status=success
window candidates=5
picked_article_id=27
```

최근 Meetup 실행에서는 후보 99건 중 신규 0건이 `success`로 기록되었고, 이전 실행 중 후보 77건에서 신규 1건이 추가된 기록이 있다.

최근 FastCampus 실행에서는 후보 56건 중 신규 0건, 갱신 13건, 숨김 1건이
`success`로 기록됐다.

운영 현황 수치는 조사 시점의 스냅샷이며 이후 달라질 수 있다.

## 10. 장점과 개선 필요 사항

### 10.1 잘 되어 있는 부분

- 재실행해도 중복 저장되지 않는 멱등성
- 애플리케이션 사전 조회와 DB UNIQUE 제약의 이중 방어
- 스케줄러와 수동 실행의 동시 수집 레이스 처리
- Meetup의 이벤트별 SAVEPOINT
- FastCampus의 프로세스 락, PostgreSQL advisory lock, 급감 방어
- FastCampus의 신규/갱신/숨김 전체 동기화와 실패 시 롤백
- 외부 소스 하나가 실패해도 다음 수집 단계 진행
- 신규 데이터 반영 후 즉시 캐시 무효화
- Redis 장애가 DB 쓰기와 API 가용성을 중단하지 않도록 폴백
- 수동 실행과 자동 실행이 핵심 수집 함수를 공유

### 10.2 개선 필요 사항

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
12. Uvicorn을 다시 `0.0.0.0:8000`에 바인딩하면 내부 API의 Nginx 차단을
    우회할 수 있으므로 루프백 바인딩을 유지해야 한다.
13. `scheduler.py` 상단 설명과 일부 기존 아키텍처 문서가 현재의 Meetup/Luma/FastCampus 체인을 완전히 반영하지 못한다.

## 11. 검증

다음 테스트 모듈을 실제 실행했다.

```text
test/backend/test_scheduler.py
test/backend/test_ingest_service.py
test/backend/test_meetup_collector.py
test/backend/test_meetup_fetcher.py
test/backend/test_brunch.py
test/backend/test_brunch_fetcher.py
test/backend/test_fastcampus_collector.py
test/backend/test_fastcampus_fetcher.py
test/api/test_classes_api.py
```

결과:

```text
66 passed
```

검증 범위에는 잡 등록 주기, 체인 순서와 실패 격리, ingest 즉시 반영과 중복
처리, Meetup 후보 수집과 동시성, Brunch 파싱·AI 필터·인기글 선정·중복 처리,
FastCampus 공개 API 파싱·배지 필터·upsert·숨김·급감 방어·동시성·목록 API가
포함된다.
