# EDU.AI 아키텍처

BC카드 AI사업팀 고객 커뮤니케이션 채널 — B2C 반응형 웹서비스.

## 시스템 구성

```
[React (Vite) SPA] ──HTTP──> [FastAPI Backend] ──SQL──> [PostgreSQL: paybooc_ai]
                                   │  │
                                   │  └──> [Redis: 캐시 (prefix nexus:)]
                                   │
                    ┌──────────────┴──────────────┐
        [Ingest Scheduler (60초)]      [Brunch Collector (12시간)]
         /contents/*.html → DB          brunch.co.kr AI글 수집 → DB
                                   
[Telegram → hermes agent] → Claude Skill(.claude/skills/nexus-writer) → /contents/*.html
```

- **frontend/**: React + Vite. 반응형(PC/모바일). Claude Design 시안(docs/DESIGN_SPEC.md) 기반.
- **backend/**: Python FastAPI. API + 스케줄러(인제스트/브런치 수집) 동일 프로세스(APScheduler).
- **test/**: 모든 테스트(단위/ API / E2E) 관리. TDD로 개발.
- **contents/**: 텔레그램 발행 글이 떨어지는 폴더. `yyyymmdd_글유형_제목.html` 명명규칙.
- **.claude/skills/nexus-writer/**: hermes agent가 호출하는 글 생성 스킬 + 도구.

## 데이터베이스 스키마 (PostgreSQL `paybooc_ai`)

주의: 이 DB에는 다른 프로젝트 테이블(bc_merchant_validation, naver_merchant_capture)이 이미 존재한다.
EDU.AI 테이블은 접두어 없이 아래 이름으로 추가하며 기존 테이블은 절대 건드리지 않는다.

### categories — 메인화면 섹션/메뉴
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | SERIAL PK | |
| slug | VARCHAR(50) UNIQUE NOT NULL | curation, class, community, meetpl, hotdeal |
| name | VARCHAR(100) NOT NULL | 표시명 (큐레이션, 클래스, …) |
| description | VARCHAR(300) | 섹션 부제 |
| display_order | INT NOT NULL DEFAULT 0 | 메인 노출 순서 |
| is_active | BOOLEAN NOT NULL DEFAULT true | 메뉴 노출 여부 |
| created_at | TIMESTAMPTZ DEFAULT now() | |

### articles — 글(뉴스레터/컬럼/가이드, 내부·외부 수집 출처 공통)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | SERIAL PK | |
| category_id | INT FK→categories.id NOT NULL | 노출 섹션 |
| article_type | VARCHAR(20) NOT NULL | 글 포맷: newsletter / column / guide |
| title | VARCHAR(300) NOT NULL | |
| summary | VARCHAR(500) | 목록 카드 요약 |
| body_html | TEXT | 본문(내부 글). 브런치 글은 NULL |
| key_visual_html | TEXT | 개념 애니메이션 키비주얼(내부 글 필수) |
| author_name | VARCHAR(100) | |
| source_type | VARCHAR(20) NOT NULL | 수집 출처: internal / brunch / stibee / kma (UI 뱃지로 사용하지 않음) |
| source_url | VARCHAR(1000) UNIQUE | 수집 원문 URL (동시 수집 중복 방지 키) |
| thumbnail_url | VARCHAR(1000) | 목록 카드 대표 이미지 |
| content_filename | VARCHAR(300) UNIQUE | 인제스트 파일명(중복 방지 키) |
| read_minutes | INT NOT NULL DEFAULT 4 | |
| likes_count | INT NOT NULL DEFAULT 0 | |
| comments_count | INT NOT NULL DEFAULT 0 | |
| view_count | INT NOT NULL DEFAULT 0 | |
| status | VARCHAR(20) NOT NULL DEFAULT 'published' | published / hidden |
| published_at | TIMESTAMPTZ NOT NULL | 목록 정렬 기준 |
| created_at / updated_at | TIMESTAMPTZ | |

- 링크 규칙: 수집 출처(`brunch`/`stibee`/`kma`) → 클릭 시 `source_url + '?ref=nexus.bccard.ai'`(기존 쿼리 있으면 `&`)로 이동. `internal` → `/articles/{id}` 상세.
- 인덱스: `(category_id, status, published_at DESC)`, `(article_type, published_at DESC)`.

### brunch_collect_runs — 브런치 수집 이력(12시간 주기)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | SERIAL PK | |
| window_start / window_end | TIMESTAMPTZ NOT NULL | 수집 대상 기간 |
| status | VARCHAR(20) NOT NULL | success / empty / duplicate(동시 수집 감지) / failed |
| candidates_count | INT NOT NULL DEFAULT 0 | 후보 글 수 |
| picked_article_id | INT FK→articles.id | 선정된 글 |
| error_message | TEXT | |
| created_at | TIMESTAMPTZ DEFAULT now() | |

선정 규칙: 기간 내 AI 관련 글 중 `댓글수 + 좋아요수` 최대 글 1건 → articles(source_type='brunch')로 저장.
`published_at` 은 원글 발행시각을 그대로 저장한다 (없으면 window_end 폴백) — 수집 글이 포맷과
무관하게 같은 기준으로 시간순 정렬되게 하기 위함. 목록 정렬은 전 구간 `published_at DESC` 단일 기준.

### newsletter_collect_runs — 뉴스레터 수집 이력(12시간 주기, 수집 체인 2단계)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | SERIAL PK | |
| status | VARCHAR(20) NOT NULL | success / empty / failed |
| candidates_count / added_count | INT NOT NULL DEFAULT 0 | 최근 기간 후보 수 / 신규 반영 수 |
| error_message | TEXT | |
| created_at | TIMESTAMPTZ DEFAULT now() | |

수집 규칙: 스티비 아카이브 3종(`page.stibee.com/archives/{listId}/emails` JSON, 목록은
`NEWSLETTER_STIBEE_LISTS`="listId:이름" 설정) + AI타임스 메인 대표기사(grid-1 블록 CSS selector,
발행시각은 기사 상세 `article:published_time` 메타, 실패 시 수집 시각 폴백) + KMA 인사이트 뉴스레터
(`selectInsightSubList.do` JSON)에서 최근 `NEWSLETTER_WINDOW_DAYS`(기본 7일) 발행분 전체를
articles(article_type='newsletter', source_type='stibee'/'aitimes'/'kma')로 저장한다.
`source_url`(스티비 stib.ee 영구 링크 / AI타임스·KMA 상세 페이지 URL) 기준으로 중복을 제거하고,
스티비 "(재발송)" 메일은 원본과 중복이므로 건너뛴다. 소스 단위 실패는 다른 소스 수집을 막지 않는다.

### members — 회원(닉네임 식별 + 비밀번호 인증)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | SERIAL PK | |
| nickname | VARCHAR(50) UNIQUE NOT NULL | 식별자 |
| password_hash | VARCHAR(300) | PBKDF2-SHA256 해시 (NULL=정책 도입 이전 레거시, 로그인 불가) |
| role / interests | VARCHAR(20) / VARCHAR(300) | 프로필 |
| created_at | TIMESTAMPTZ DEFAULT now() | |

- **비밀번호 정책**: 영문·숫자를 각 1자 이상 포함한 8자 이상 (특수문자·대소문자 조합은 선택). 위반 시 400 + 부족 항목 메시지.
- `POST /api/members` 는 신규 닉네임이면 **가입**, 기존 닉네임이면 **비밀번호 검증 후 로그인**(불일치 401).
- 평문 비밀번호는 저장·직렬화·로깅하지 않는다 (`serialize_member` 에서 해시 비노출).
- 이메일 항목은 007 마이그레이션에서 제거됨.

### community_posts — 커뮤니티 글
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | SERIAL PK | |
| member_id | INT FK→members.id (NULL 허용) | 탈회 시 NULL(작성자명은 보존) |
| author_name | VARCHAR(50) NOT NULL | 표시용 스냅샷 |
| tag | VARCHAR(20) NOT NULL | 자료/노하우/팁/기술자료 |
| title / body | VARCHAR(300) / TEXT NOT NULL | |
| likes_count / comments_count | INT NOT NULL DEFAULT 0 | 캐시 카운터 |
| status | VARCHAR(20) NOT NULL DEFAULT 'published' | published / hidden |
| created_at | TIMESTAMPTZ DEFAULT now() | |

인덱스: `(status, created_at)`, `(member_id)`.

### community_post_likes — 글 좋아요 (회원당 1개 토글)
복합 PK `(post_id, member_id)` — FK→community_posts.id / members.id. 어뷰징 방지의 원천.

### community_comments — 커뮤니티 댓글
`id PK, post_id FK NOT NULL, member_id FK(NULL 허용), author_name, body, created_at`.
인덱스: `(post_id)`, `(member_id)`.

### meetup_events — meet.pl 밋업 (event-us/luma 수집)
`id PK, source_id UNIQUE, source_url UNIQUE, title, host_name, event_start/end,
place/area/address, price_min(NULL=미상), is_free, view_count, event_system_type,
category, cover_image_url, status, collected_at`. 인덱스: `(event_start)`.

### meetup_collect_runs — 밋업 수집 이력
`id PK, status(success/empty/failed), candidates_count, added_count, error_message, created_at`.

### courses / fastcampus_collect_runs — 수집형 클래스·참가 기회
`courses`: FastCampus 과정, Daker 해커톤, DACON 경진대회의 소스별 ID(`source_id`)와
URL을 UNIQUE로 보존한다. FastCampus 과정은 세 대상 카테고리, 목록 순위, 제목/설명/
이미지/가격/과정 형식/수강 대상/러닝타임/복수 배지를 저장한다. Daker/DACON 항목은
`daker:`/`dacon:` ID 접두어와 상태, 주최사/키워드, 상금·혜택을 같은 필드에 매핑한다.
FastCampus 공개 대상 배지는 `얼리버드`, `인기 급상승`, `BEST`, `NEW`로 제한한다. 재수집 시 upsert하며
대상 배지를 잃은 기존 과정은 삭제 대신 `status='hidden'` 처리한다. 단, 카테고리 ID·BEST/NEW
응답 구조·카테고리별 대상 과정 존재 여부를 먼저 검증하고, 기존 공개 건수 대비 50% 초과 급감 시
전체 반영을 중단한다. 숨김은 수집 완료가 확인된 카테고리에만 적용한다. 수동 실행과 스케줄 실행은
프로세스 락 및 PostgreSQL transaction advisory lock으로 직렬화한다.

`fastcampus_collect_runs`: `status(success/empty/failed), candidates_count, added_count,
updated_count, hidden_count, error_message, created_at`.

### writer_sessions / writer_messages — 텔레그램 작가 세션
`writer_sessions`: `telegram_user_id BIGINT PK, summary TEXT(압축 요약), updated_at`.
`writer_messages`: `id PK, telegram_user_id BIGINT, role VARCHAR(12), content TEXT, created_at`.
인덱스: `(telegram_user_id, created_at)` — 작가별 대화 완전 분리.

### DEFAULT/마이그레이션 규칙
- 모든 DEFAULT 는 **DB 레벨(server_default)로도** 정의한다 — ORM 우회(raw SQL/배치) INSERT 도 동작 (`005_server_defaults.sql`).
- 스키마 변경은 `backend/migrations/NNN_*.sql` 로 기록 (create_all 은 신규 테이블만).

### 좋아요 정책 (의도된 비대칭)
- **커뮤니티 글**: 회원 기반 토글 — `community_post_likes` 로 회원당 1개 강제, `liked` 반환.
- **아티클**: 익명 증가 전용(회원 식별 없음, 감소 API 없음) — 비로그인 독자도 반응 가능하게 한
  프로토타입 정책. 프론트는 세션당 1회만 POST 하여 중복 증가를 완화한다.
  회원 기반 통일 여부는 정식 로그인 도입 시 재검토.

## 캐시 정책 (Redis 사용 결정)

**Redis 채택 이유**: API 프로세스와 스케줄러가 동시에 쓰기(신규 글)를 발생시키므로 프로세스 간 일관된 무효화가 필요.
로컬/배포 환경에 Redis가 이미 존재. Redis 미가용 시 동일 인터페이스의 InMemory 캐시로 자동 폴백(개발/테스트 용).

- **패턴**: cache-aside + **네임스페이스 버전 무효화**.
  - 버전 키 `nexus:ver:articles` 를 캐시 키에 포함: `nexus:v{N}:home`, `nexus:v{N}:articles:list:{cat}:{type}:{page}`, `nexus:v{N}:categories`
  - **쓰기 발생 시(신규 글 인제스트, 브런치 선정, 좋아요) 버전 키를 INCR** → 이전 캐시는 즉시 무효(다음 조회는 DB에서 최신 반영). O(1), SCAN 불필요 — 공용 Redis에 안전.
  - 글 상세(`/api/articles/{id}`)는 **캐시하지 않는다** — 매 조회가 view_count 를 증가시키므로(쓰기 동반) 캐시 이득이 없다.
- **TTL**: 300초(안전망). 무효화가 주 메커니즘이므로 TTL은 잔존 키 정리용.
- 키 프리픽스 `nexus:` 로 동일 Redis의 타 프로젝트 키와 격리.
- **운영 노트**:
  - 버전 키(`nexus:ver:articles`)는 TTL 없음 — Redis 는 `noeviction`(기본) 전제.
    `maxmemory` + 축출 정책 도입 시 버전 키 보호를 함께 검토할 것.
  - 구버전 캐시 키(`nexus:v{N-1}:*`)는 능동 삭제하지 않고 TTL(300초)로 정리된다 —
    버전이 짧은 주기로 여러 번 오르면 세대가 일시 공존하므로 메모리 사용량 모니터링 권장.
  - 동시 캐시 미스는 프로세스 내 single-flight 로 로더(DB 조회)를 1회만 실행한다(스탬피드 방지).
  - 기동 후 Redis 런타임 장애 시 예외를 전파하지 않고 캐시 우회(매 요청 DB 조회)로 동작한다.

## API (요약)

- `GET /api/health`
- `GET /api/categories` — 활성 메뉴(노출 순서)
- `GET /api/home` — 섹션별 최신 글 번들(메인화면 1회 호출). 큐레이션 섹션은 포맷별
  (컬럼→뉴스레터→가이드) 최신 1건씩 노출 — 건수 많은 포맷의 독점 방지 (목록 페이지는 시간순 그대로)
- `GET /api/articles?category=&type=&page=&size=` — 목록(카드 필드 포함)
- `GET /api/articles/{id}` — 상세(view_count 증가)
- `POST /api/articles/{id}/like` — 익명 증가 전용(위 '좋아요 정책' 참고)
- `GET /api/classes?category=&page=&size=` — 수집형 클래스·참가 기회 목록. 카테고리 코드: `DATASCIENCEDL`, `AICREATIVE`, `BIZ`, `DAKER`, `DACON`.
  정렬은 `source_rank` 우선(카테고리별 1위들이 섞여 상단 노출, 동률은 카테고리 우선순위) — 홈 '지금 뜨는 클래스'도 이 순서의 상위 4건.
- `GET /api/events?category=&page=&size=` — 밋업 목록(배지: `IT/프로그래밍`, `AI`, `경제/금융`; 미지정 시 전체)
- `POST /api/members` — 가입 또는 로그인(닉네임+비밀번호, 위 members 정책 참고) · `GET/PATCH/DELETE /api/members/{id}` — 프로필/탈회
- `GET /api/community/posts?tag=&page=&size=` · `POST /api/community/posts` · `GET /api/community/posts/{id}` — 커뮤니티 글
- `DELETE /api/community/posts/{id}` — 요청 본문 `memberId/password` 인증 후 본인 글 삭제(댓글/좋아요 포함)
- `POST /api/community/posts/{id}/comments` · `POST /api/community/posts/{id}/like` — 댓글/토글 좋아요
- 오류 시맨틱: 온보딩 미완료 403 / 대상 리소스 없음 404 / 검증 실패 400
- `POST /api/internal/ingest/run` — 인제스트 수동 실행(스케줄러와 동일 코드 경로, 테스트용)
- `POST /api/admin/articles` · `PATCH /api/admin/articles/{id}` — 어드민 글 생성(어드민)·수정(작성자). 단일 JSON.
- `POST /api/admin/articles/parts` — 같은 저장을 8KB 미만 조각으로. 앞단 WAF(AWS 공통 규칙
  `SizeRestrictions_BODY`, 8KB 고정)가 큰 요청 본문을 403 HTML 로 거절하므로 프론트는 항상 이 경로를
  쓴다. 매 조각에 제목·요약·유형 메타를 함께 싣고, 마지막 조각이 도착한 요청이 곧 저장이다(생성 201·수정 200).
  조각 저장소는 이미지 조각과 같은 Redis(`nexus:imgup:*`, 600초 TTL)이고, Redis 미가용 시 프로세스 메모리
  폴백이라 다중 파드에서는 Redis 가 필요하다. `POST /api/admin/media/parts` 는 본문 이미지 조각.
- `POST /api/internal/media/backfill` — 사라진 인제스트 썸네일 재생성(위 '영구 미디어 저장소')
- `POST /api/internal/content/resanitize` — 저장된 글 본문·키비주얼 재정화(위 '콘텐츠 보안')
- `POST /api/internal/brunch/run` · `POST /api/internal/newsletter/run` · `POST /api/internal/meetup/run` · `POST /api/internal/classes/run` — 수집 수동 실행

## 테스트 전략 (TDD)

- 위치: `/test` (루트). `test/backend`(단위), `test/api`(FastAPI TestClient), `test/e2e`(Playwright, 옵션).
- 단위/API 테스트 DB: SQLite in-memory(SQLAlchemy 공용 타입만 사용) — 로컬 PG 불필요.
- 캐시 테스트: InMemory 백엔드로 정책(버전 무효화) 검증 + Redis 연동은 통합 마커.
- 품질 게이트: ruff(문법/린트), radon(복잡도 B 이상), jscpd(중복), code-reviewer 에이전트 리뷰.

## 콘텐츠 보안 (보안 점검 2026-10 반영)

- **HTML 새니타이저** (`services/html_sanitize.py`): 프로필(허용 태그·속성 정책) 기반 allowlist.
  어드민 본문은 `/api/media` 이미지만, 인제스트 본문(`content_sanitize.sanitize_ingest_html`)은
  h1/figure/table/data:image 까지, 키비주얼(`sanitize_key_visual_html`)은 SMIL 애니메이션 SVG 허용 목록.
  출력은 `decode_contents()` 로 재이스케이프하고 CDATA·선언·PI 노드를 제거한다 — 둘 다 과거에
  저장형 XSS 우회 경로였다(회귀 테스트 `test_html_sanitize.py`, `test_ingest_sanitize.py`).
- **직접 작성 글 수정 권한**: `articles.author_member_id`(015) 와 현재 `access_role=admin` 으로 판정한다.
  닉네임은 바꾸거나 탈회 후 남이 선점할 수 있어 권한 키로 쓰지 않는다. 015 이전 글(NULL)은 아무도 수정 불가.
- **수퍼어드민 닉네임 보호**: `SUPER_ADMIN` 에 있는 닉네임으로 개명할 수 없고, 그 계정은 개명·탈회할 수
  없다 — 닉네임이 비면 남이 선점해 권한관리를 얻는다. 최초 가입은 허용(신규 환경 부트스트랩).
- **발행 도구 fail-closed**: `save_article.py` 는 사용자 id 로 `.writer_whitelist` 를 직접 검사하고 미등록이면
  `DENIED` 를 출력하고 아무것도 쓰지 않는다. 호스트(hermes)가 넣는 `NEXUS_TELEGRAM_USER_ID` 가 있으면 그것만
  믿고(`--user` 는 같을 때만 허용, 빈 값은 거부), 없을 때만 `--user` 를 쓴다. 모델이 고르는 `--user` 는
  프롬프트 인젝션에 약하므로 hermes 쪽에서 환경변수를 넣어 주는 것이 진짜 게이트다.
- **키비주얼 CSS**: `<style>` 은 `<svg>` 안에서만, 외부 요청(url/@import/image-set)·CSS 이스케이프·
  `position:fixed` 는 차단. `fill`/`filter` 등의 `url()` 은 `#id` 참조만. SPA 전체 디페이스·피싱 오버레이 방지.
- **기존 저장분 재정화**: `POST /api/internal/content/resanitize` 가 internal·authored 글을 현재 정책으로 다시
  거른다(바뀐 글만 갱신, 캐시 버전 증가). 정화 도입 이전 글은 인제스트가 재처리하지 않으므로 배포 후 1회 실행.
- **015 배포 순서**: ① DB 백업 → ② `015_articles_author_member_id.sql` 적용(멱등) → ③ 백필 결과 확인
  (`author_member_id IS NULL` 인 authored 글은 수동 지정) → ④ 백엔드 배포 → ⑤ resanitize 1회 → ⑥ hermes 에
  `NEXUS_TELEGRAM_USER_ID` 주입. ORM 에 컬럼이 추가되어 015 전에 새 백엔드를 띄우면 글 조회가 전부 실패한다.

- **내부 API 접근 통제** (`api/internal_access.py`): nginx 의 `/api/internal/` 403 과 별개로 앱도 거른다 —
  `X-Internal-Token` 이 `INTERNAL_API_TOKEN` 과 일치(빈 설정은 절대 일치하지 않음)하거나 정확히 127.0.0.1/::1 에서
  온 요청만 허용(127.0.0.0/8 전체를 받으면 서비스 메시 사이드카 경유 요청이 다 통과한다). 운영 호출은 파드 안에서
  `python -m app.internal_call content/resanitize` 로 한다 — 이미지에 curl 이 없다. 테스트 픽스처는 토큰을 기본 헤더로 붙인다.
- **프록시 신뢰 경계** (`docker/nginx.conf`): TLS 는 ALB 가 끝내므로 `$scheme` 은 항상 http — 앞단의
  `X-Forwarded-Proto` 를 map 으로 넘겨야 백엔드가 Secure 쿠키를 발급한다(목록이면 첫 값). 레이트리밋은
  `real_ip` 모듈로 신뢰 홉(ALB 가 있는 dev VPC 대역만 — RFC1918 전체를 신뢰하면 사설 주소 클라이언트가 XFF 를
  조작한다)을 건너뛴 실제 클라이언트 IP 기준이며, 좋아요 리밋 경로는 `[^/]+` 로 잡아 `+1`·`1_0`·`%201` 같은
  정수 변형 우회를 막는다. 운영 VPC 로 옮기면 `set_real_ip_from` 대역을 바꿔야 한다.
- **보안 응답 헤더** (`docker/security-headers.conf`): CSP(인라인 스크립트 금지, `frame-ancestors 'none'`),
  nosniff, X-Frame-Options, Referrer-Policy, https 요청에만 HSTS. `add_header` 는 상속되지 않으므로 403 블록을
  뺀 **모든 location 이 include** 해야 하고, 그래서 GA 부트스트랩은 `frontend/public/ga-init.js` 정적 파일이다.
  새 외부 도메인(스크립트·API·폰트)을 쓰면 CSP 에 추가할 것 (가드: `NginxSecurityHeaders.test.js`).
- **작가 도구 SSRF 방어** (`services/safe_fetch.py`): `fetch_reference.py` 는 공개 http(s) 주소만 가져온다 —
  DNS 를 한 번 풀어 사설·루프백·링크로컬(메타데이터)·CGNAT·전환 주소(mapped/6to4/Teredo/NAT64)에 박힌 사설 IPv4 를
  거부하고, **검사한 IP 로 직접 연결**(Host·SNI 는 원래 호스트명)해 DNS 리바인딩을 막는다. 리다이렉트 홉마다
  재검사(최대 3), 본문 2MB·전체 40초 상한, 환경 프록시 무시(trust_env=False).
- **작가 id 출처 공통화** (`services/writer_identity.py`): `check_writer.py`·`session.py`·`save_article.py` 가
  같은 규칙(`NEXUS_TELEGRAM_USER_ID` 우선, argv 는 같을 때만, 빈 값 거부)을 쓴다 — 사칭 id 로 다른 작가의
  세션을 읽거나 지울 수 없다.

- **LOW 조치 (2026-10)**: `SUPER_ADMIN` 은 설정 여부만 로그; 목록 `page` ≤ 1000, `category`/`type` 은 슬러그
  패턴만(캐시 키 오염 방지); 미발행 글 좋아요 404; PBKDF2 600k(기존 해시는 저장된 반복 횟수로 그대로 검증)와
  없는 닉네임에도 더미 해시 1회(타이밍 열거 방지), `nickname-available` 도 nginx 인증 리밋; 업로드 조각은 회원당
  열린 업로드 8개까지; svg 썸네일은 블록리스트 대신 키비주얼 허용목록; `with_ref`/`safe_href` 는 http(s)·상대 경로만
  (프로토콜 상대 `//`·`/\` 차단, 안전하지 않은 외부 링크는 카드가 비링크로 렌더); 커버 URL 은 CSS `url("…")` 로
  인용; 발행 도구는 덮어쓰기 거부·발행일 범위(과거 30일~내일)·`read_minutes` 1~10·제어문자 제거·파일명 255 바이트;
  세션 도구는 저장 텍스트의 `===` 구분선을 무력화; 화이트리스트 파일이 깨져도 fail-closed; Redis URL 로그 마스킹;
  compose 기본 DB 비밀번호 제거; CI jscpd 버전 고정.
  백엔드 컨테이너는 비루트 `USER 1000:1000` 으로 돈다(아래 '영구 미디어 저장소'의 실행 계정 항목).
  **미조치**: GitHub Actions SHA 고정, 익명 좋아요의 캐시 버전 bump(불변식 1 — nginx 리밋 경로 수정으로 완화).

## 영구 미디어 저장소 (`MEDIA_DIR`)

에디터 본문 이미지(`authored/`)와 인제스트 썸네일(`thumbnails/`)은 전부 `settings.media_dir` 아래에만
쓰고 `/api/media/...` 로 서빙한다. 컨테이너 파일시스템은 휘발성이라 배포 파드는 `/app/media` 에 S3 를
마운트하며, `docker/backend.Dockerfile` 이 `MEDIA_DIR=/app/media` 를 고정한다(파드는 `.env` 를 읽지 않음).
재기동과 무관하게 보관해야 하는 파일은 모두 이 경로 아래에 둔다. S3 마운트는 rename·덮어쓰기를 거부하므로
새 파일은 임의 이름으로 쓰고(에디터 이미지), 같은 내용은 해시 이름으로 재사용한다(썸네일, `open('xb')` 로
동시 쓰기 경합도 흡수).

- **기동 검증**: `MEDIA_REQUIRE_MOUNT=true`(배포 이미지 기본값)면 `media_dir` 이 마운트 포인트가 아닐 때
  `create_app` 이 RuntimeError 로 기동을 거부한다 — 마운트 누락 시 휘발성 디렉터리에 쓰다 다시 잃는 사고 방지.
  실행 계정이 `media_dir` 에 쓸 수 없을 때도(`os.access`) 같은 방식으로 거부한다.
  기동 로그에 `[media] dir=... mount=yes|no writable=yes|no` 한 줄이 남는다. 로컬/CI 는 false.
- **실행 계정**: `docker/backend.Dockerfile` 은 빌드(pip·COPY·`compileall`)를 root 로 마친 뒤 `USER 1000:1000`
  으로 전환한다. `/app` 은 root 소유 0755 라 코드·`contents/` 는 읽기 전용이고, 쓰기는 `media_dir` 아래뿐이다.
  uid 1000 은 dev 파드의 S3 마운트(PV `nexus-s3-pv-dev`, mountpoint-s3 `allow_other,default_permissions`)가
  `/app/media` 를 보여 주는 소유자 uid(1000, 0755) 와 같아야 쓸 수 있어서 정한 값이다 — PV `mountOptions` 의
  `uid` 를 바꾸면 Dockerfile 의 `USER` 도 같이 바꾼다. 로컬 compose 의 `./media` 바인드 마운트도 uid 1000 이
  쓸 수 있어야 한다(`docs/SETUP.md`). 배포 매니페스트에는 `securityContext.runAsNonRoot: true` 를 함께 두는 것을
  권장한다(이미지의 숫자 uid 로 검증 가능).
- **복구**: 마운트 이전에 인제스트돼 파일이 사라진 썸네일은 `POST /api/internal/media/backfill` 이
  DB 의 `key_visual_html` 로 같은 URL(내용 해시)에 재생성한다. 에디터로 올린 본문 이미지는 원본이 DB 에
  없어 복구할 수 없다(재업로드 필요).

## 배포 (Docker)

- `docker-compose.yml`: backend, frontend(nginx), postgres, redis — 내부 네트워크로 연결, DB/Redis 포트는 외부 미노출(로컬 개발 스택과 충돌 방지). 웹 포트만 공개.
- 설정은 전부 `.env` 환경변수로 주입.
