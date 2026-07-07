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

### articles — 글(뉴스레터/컬럼/가이드 + 브런치 수집글)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | SERIAL PK | |
| category_id | INT FK→categories.id NOT NULL | 노출 섹션 |
| article_type | VARCHAR(20) NOT NULL | newsletter / column / guide / brunch |
| title | VARCHAR(300) NOT NULL | |
| summary | VARCHAR(500) | 목록 카드 요약 |
| body_html | TEXT | 본문(내부 글). 브런치 글은 NULL |
| key_visual_html | TEXT | 개념 애니메이션 키비주얼(내부 글 필수) |
| author_name | VARCHAR(100) | |
| source_type | VARCHAR(20) NOT NULL | internal / brunch |
| source_url | VARCHAR(1000) | 브런치 원글 URL |
| content_filename | VARCHAR(300) UNIQUE | 인제스트 파일명(중복 방지 키) |
| read_minutes | INT NOT NULL DEFAULT 4 | |
| likes_count | INT NOT NULL DEFAULT 0 | |
| comments_count | INT NOT NULL DEFAULT 0 | |
| view_count | INT NOT NULL DEFAULT 0 | |
| status | VARCHAR(20) NOT NULL DEFAULT 'published' | published / hidden |
| published_at | TIMESTAMPTZ NOT NULL | 목록 정렬 기준 |
| created_at / updated_at | TIMESTAMPTZ | |

- 링크 규칙: `source_type='brunch'` → 클릭 시 `source_url + '?ref=nexus.bccard.ai'`(기존 쿼리 있으면 `&`)로 이동. `internal` → `/articles/{id}` 상세.
- 인덱스: `(category_id, status, published_at DESC)`, `(article_type, published_at DESC)`.

### brunch_collect_runs — 브런치 수집 이력(12시간 주기)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | SERIAL PK | |
| window_start / window_end | TIMESTAMPTZ NOT NULL | 수집 대상 기간 |
| status | VARCHAR(20) NOT NULL | success / empty / failed |
| candidates_count | INT NOT NULL DEFAULT 0 | 후보 글 수 |
| picked_article_id | INT FK→articles.id | 선정된 글 |
| error_message | TEXT | |
| created_at | TIMESTAMPTZ DEFAULT now() | |

선정 규칙: 기간 내 AI 관련 글 중 `댓글수 + 좋아요수` 최대 글 1건 → articles(source_type='brunch')로 저장.

## 캐시 정책 (Redis 사용 결정)

**Redis 채택 이유**: API 프로세스와 스케줄러가 동시에 쓰기(신규 글)를 발생시키므로 프로세스 간 일관된 무효화가 필요.
로컬/배포 환경에 Redis가 이미 존재. Redis 미가용 시 동일 인터페이스의 InMemory 캐시로 자동 폴백(개발/테스트 용).

- **패턴**: cache-aside + **네임스페이스 버전 무효화**.
  - 버전 키 `nexus:ver:articles` 를 캐시 키에 포함: `nexus:v{N}:home`, `nexus:v{N}:articles:list:{cat}:{type}:{page}`, `nexus:v{N}:categories`
  - **쓰기 발생 시(신규 글 인제스트, 브런치 선정, 좋아요) 버전 키를 INCR** → 이전 캐시는 즉시 무효(다음 조회는 DB에서 최신 반영). O(1), SCAN 불필요 — 공용 Redis에 안전.
  - 글 상세(`/api/articles/{id}`)는 **캐시하지 않는다** — 매 조회가 view_count 를 증가시키므로(쓰기 동반) 캐시 이득이 없다.
- **TTL**: 300초(안전망). 무효화가 주 메커니즘이므로 TTL은 잔존 키 정리용.
- 키 프리픽스 `nexus:` 로 동일 Redis의 타 프로젝트 키와 격리.

## API (요약)

- `GET /api/health`
- `GET /api/categories` — 활성 메뉴(노출 순서)
- `GET /api/home` — 섹션별 최신 글 번들(메인화면 1회 호출)
- `GET /api/articles?category=&type=&page=&size=` — 목록(카드 필드 포함)
- `GET /api/articles/{id}` — 상세(view_count 증가)
- `POST /api/articles/{id}/like`
- `POST /api/internal/ingest/run` — 인제스트 수동 실행(스케줄러와 동일 코드 경로, 테스트용)
- `POST /api/internal/brunch/run` — 수집 수동 실행

## 테스트 전략 (TDD)

- 위치: `/test` (루트). `test/backend`(단위), `test/api`(FastAPI TestClient), `test/e2e`(Playwright, 옵션).
- 단위/API 테스트 DB: SQLite in-memory(SQLAlchemy 공용 타입만 사용) — 로컬 PG 불필요.
- 캐시 테스트: InMemory 백엔드로 정책(버전 무효화) 검증 + Redis 연동은 통합 마커.
- 품질 게이트: ruff(문법/린트), radon(복잡도 B 이상), jscpd(중복), code-reviewer 에이전트 리뷰.

## 배포 (Docker)

- `docker-compose.yml`: backend, frontend(nginx), postgres, redis — 내부 네트워크로 연결, DB/Redis 포트는 외부 미노출(로컬 개발 스택과 충돌 방지). 웹 포트만 공개.
- 설정은 전부 `.env` 환경변수로 주입.
