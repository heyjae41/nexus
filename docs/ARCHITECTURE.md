# NEXUS 아키텍처

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
NEXUS 테이블은 접두어 없이 아래 이름으로 추가하며 기존 테이블은 절대 건드리지 않는다.

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
`NEWSLETTER_STIBEE_LISTS`="listId:이름" 설정) + KMA 인사이트 뉴스레터
(`selectInsightSubList.do` JSON)에서 최근 `NEWSLETTER_WINDOW_DAYS`(기본 7일) 발행분 전체를
articles(article_type='newsletter', source_type='stibee'/'kma')로 저장한다.
`source_url`(스티비 stib.ee 영구 링크 / KMA 상세 페이지 URL) 기준으로 중복을 제거하고,
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
- `GET /api/home` — 섹션별 최신 글 번들(메인화면 1회 호출)
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
- `POST /api/internal/brunch/run` · `POST /api/internal/newsletter/run` · `POST /api/internal/meetup/run` · `POST /api/internal/classes/run` — 수집 수동 실행

## 테스트 전략 (TDD)

- 위치: `/test` (루트). `test/backend`(단위), `test/api`(FastAPI TestClient), `test/e2e`(Playwright, 옵션).
- 단위/API 테스트 DB: SQLite in-memory(SQLAlchemy 공용 타입만 사용) — 로컬 PG 불필요.
- 캐시 테스트: InMemory 백엔드로 정책(버전 무효화) 검증 + Redis 연동은 통합 마커.
- 품질 게이트: ruff(문법/린트), radon(복잡도 B 이상), jscpd(중복), code-reviewer 에이전트 리뷰.

## 배포 (Docker)

- `docker-compose.yml`: backend, frontend(nginx), postgres, redis — 내부 네트워크로 연결, DB/Redis 포트는 외부 미노출(로컬 개발 스택과 충돌 방지). 웹 포트만 공개.
- 설정은 전부 `.env` 환경변수로 주입.
