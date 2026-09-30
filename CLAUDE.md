# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# EDU.AI 프로젝트 — Claude Code 작업 규칙

BC카드 AI사업팀 커뮤니케이션 채널 (React + FastAPI + PostgreSQL + Redis).
처음 왔다면 `docs/SETUP.md`(환경 구성) → `docs/ARCHITECTURE.md`(DB 스키마·캐시·API) →
`docs/COLLECTION_JOBS.md`(수집잡) 순서로 읽는다. 배포·운영(GitLab/Jenkins/EKS, ExternalSecret,
SUPER_ADMIN 동작 등) 사실은 `AGENTS.md` 의 "Learned Workspace Facts" 에 있다 — 여기에 중복하지 않는다.

## 작업 방식 (필수)

- **TDD**: 프로덕션 코드 작성 전에 `/test` 아래 실패하는 테스트부터 작성한다 (RED→GREEN→REFACTOR).
  - `test/backend` 단위, `test/api` FastAPI TestClient, `test/frontend` vitest, `test/e2e` Playwright(옵션)
  - 테스트 DB 는 SQLite in-memory (`test/conftest.py` 의 `db`/`engine` 픽스처, PG 불필요)
- **품질 게이트** (커밋 전 전부 통과, `.github/workflows/ci.yml` 과 동일): `python -m pytest test` ·
  `ruff check backend test` · `radon cc backend/app -n C -s`(출력 없어야 함) ·
  `npx jscpd --min-tokens 40`("Found 0 clones" 이어야 함) ·
  프론트 변경 시 `cd frontend && npm run build && npx vitest run && npm run lint`
- **코드리뷰**: 기능 단위 완료 시 code-reviewer 에이전트 리뷰를 거치고 CRITICAL/HIGH 는 반드시 수정
- **브랜치**: main 직접 커밋 금지 — `feat/*` 브랜치 → 게이트 통과 → `--no-ff` 병합 → push
- 커밋 메시지는 한국어 컨벤셔널 커밋 (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `content:`)

## 핵심 불변식 (깨뜨리면 안 됨)

1. **캐시 정책**: DB 쓰기(글/이벤트/좋아요/댓글)가 발생하는 모든 경로는 `cache.bump_version()` 을
   호출해야 한다 — "DB 반영사항은 항상 즉시 조회 가능" 이 제품 요구사항이다.
2. **외부 링크 규칙**: 수집 콘텐츠(브런치/밋업)의 이동 URL 에는 항상 `?ref=nexus.bccard.ai` 를
   부착한다 (`app/services/links.py` 의 `with_ref` 사용).
3. **인제스트 명명규칙**: `contents/yyyymmdd_글유형_제목.html` (유형: 뉴스레터/컬럼/가이드).
4. **작가 화이트리스트 fail-closed**: `.writer_whitelist` 미등록 사용자는 발행/세션 도구가 차단.
   스킬 지시 우회를 막기 위해 도구 자체 검증을 제거하지 말 것.
5. **paybooc_ai DB 공유 주의**: `bc_merchant_validation`, `naver_merchant_capture` 테이블은
   타 프로젝트 소유 — 절대 수정/삭제 금지.
6. **스키마 변경**: 기존 테이블 ALTER 는 `backend/migrations/NNN_*.sql` 로 기록한다
   (create_all 은 신규 테이블만 만든다). 모든 DEFAULT 는 `server_default` 로도 정의한다.
7. **브라우저 dialog 금지**: 프론트에서 `alert()/confirm()` 사용 금지 — 인라인 UI 로 처리.
8. **테스트에서 실 DB 접속 금지**: `test/conftest.py` 의 autouse 가드가 `postgresql` URL 엔진 생성을
   막는다. 스케줄러/수집 체인 테스트는 fetch 단계를 반드시 mock 한다 (가드 우회 금지).
9. **영구 파일은 `settings.media_dir` 아래에만**: 배포 파드는 `/app/media` 에 S3 마운트, 이미지가
   `MEDIA_DIR`/`MEDIA_REQUIRE_MOUNT=true` 고정. 그 밖의 컨테이너 경로는 휘발성. S3 마운트는 rename·덮어쓰기를
   거부하므로 임시파일→rename 패턴 금지, 새 이름으로 쓰거나 존재하면 건너뛴다 (`docs/ARCHITECTURE.md` 영구 미디어 저장소).

## 자주 쓰는 명령

```bash
. .venv/bin/activate                                           # 루트 venv (사내망 TLS 이슈 시 uv 대신 pip)
PYTHONPATH=backend uvicorn app.main:app --port 8000 --reload   # 백엔드 (루트에서)
cd frontend && npm run dev                                      # 프론트 — http://localhost:80, /api → :8000 프록시
(cd backend && python -m app.seed)                              # 시드 (멱등, 테이블 create_all 포함)
(cd backend && python -m app.collect_once)                      # 수집 체인 1회 실행 (K8s CronJob 엔트리)
curl -X POST localhost:8000/api/internal/{ingest,brunch,newsletter,meetup,classes,cardpick}/run  # 수집 수동 실행
curl -X POST localhost:8000/api/internal/media/backfill        # 사라진 인제스트 썸네일 재생성
docker compose up -d --build                                    # 전체 스택 — http://localhost:8080

# 테스트 (pytest.ini 가 testpaths=test, pythonpath=backend 를 잡아 주므로 루트에서 실행)
python -m pytest test/api/test_api.py -k home                   # 단일 파일 / 키워드
python -m pytest test --cov=backend/app                         # 커버리지 (80%+ 목표)
python -m pytest test -m "not integration"                      # PG/Redis 필요한 통합 테스트 제외
cd frontend && npx vitest run Home.test.jsx                     # 프론트 단일 테스트 (파일명 필터)
cd frontend && npm run e2e                                      # Playwright — backend(8000)+vite(80) 기동 필요
                                                                # 주소 다르면 E2E_BASE_URL / E2E_API 로 지정
```

## 구조와 흐름

### 백엔드 (`backend/app/`)

- **계층**: `api/*.py`(라우터) → `repositories/*.py`(DB 조회·쓰기, Session 인자) → `serializers.py`(모델→camelCase dict).
  도메인 로직은 `services/` 에 두고 라우터는 얇게 유지한다.
- **응답 봉투**: 모든 응답은 `serializers.api_response()` 가 만드는 `{success, data?, error?, meta?}`.
  HTTPException 은 `main.py` 의 핸들러가 같은 형태로 변환한다. 목록 API 는 `api/common.py` 의
  `page_query()`(page/size ≤ 50) + `cached_page_response()`(items + meta.total/page/limit) 를 재사용한다.
- **라우터 프리픽스**: `routes.py` 공개 `/api`, `auth.py` `/api/auth`(쿠키 세션 `nexus_session`),
  `admin.py` `/api/admin`(글쓰기·미디어 업로드·권한관리, `access_role=admin` 필요),
  `community.py`, `internal.py` `/api/internal`(수집 수동 실행). 오류 시맨틱: 403 권한/온보딩, 404 없음, 400 검증.
- **캐시**: `cache.py` 의 `VersionedCache.get_or_set(key, loader)` — 키는 `nexus:v{N}:...` 로 버전 네임스페이스.
  Redis 미가용/장애 시 InMemory 폴백·캐시 우회. 글 상세는 view_count 증가 때문에 캐시하지 않는다.
- **스케줄러**: API 프로세스 안의 APScheduler (`services/scheduler.py`). `ingest_contents`(60초, contents/*.html→DB)
  와 `collect_chain`(12시간: brunch→newsletter→event-us→luma→cardpick→fastcampus→daker→dacon, 단계 실패해도 계속).
  `ENABLE_CRAWL_SCHEDULER=false` 면 수집 체인을 빼고 `collect_once` 로 분리 실행한다. 수집기는
  `*_fetcher.py`(외부 HTTP → 후보) + `*_collector.py`(DB upsert + bump_version) 짝으로 되어 있다.
- **설정**: `config.py` 의 pydantic `Settings` (루트 `.env`, `get_settings()` 는 lru_cache — 테스트에서는
  monkeypatch 로 속성 교체). `main.py` 는 `create_app(cache=, enable_scheduler=, log_secrets=)` 팩토리.
- **마이그레이션 폴더 두 개**: `backend/migrations/NNN_*.sql` 은 증분 ALTER 기록,
  루트 `migration/` 은 로컬→개발서버 전체 이관 번들(export/import/verify, 타 프로젝트 테이블 제외).

### 프론트엔드 (`frontend/src/`)

- `App.jsx` 가 라우팅·인증 상태(`fetchCurrentMember` 로 세션 복원)를 쥐고 views 로 내려준다.
  `views/`(페이지, `views/admin/` 어드민) / `components/` / `hooks/` / `utils/` / `api/client.js`.
- `api/client.js` 는 `credentials: 'include'` 로 호출하고 응답의 `.data` 를 풀어서 반환한다.
- UI 는 `docs/DESIGN_SPEC.md` 의 픽셀 명세를 따른다 (색상·타이포·브레이크포인트 860/560px, `styles/tokens.css`).

### 테스트 관례

- `test/api/conftest.py` 의 `client` 픽스처: SQLite StaticPool + InMemory 캐시 + 스케줄러 off 로
  `create_app` 을 띄운다. `client.session_factory`/`client.cache` 로 직접 접근, `seed(client)` 로 기본 데이터.
- `test/backend/shared.py`: `make_cache()`, `seed_curation(db)`, fetcher 용 `FakeResponse`/`JsonResponse`.
  외부 HTML/JSON 샘플은 `test/fixtures/`.
- 프론트 테스트는 `frontend/` 밖(`test/frontend/`)에 있다 — `vitest.config.js` 의 커스텀 resolve 플러그인이
  `frontend/node_modules` 로 연결하고, `npm run lint` 는 스크립트 안에서 루트로 이동해 `test/frontend`·`test/e2e` 까지 검사한다.
  `useNavigate` 를 검증하려면 `test/frontend/helpers.js` 의 `mockNavigate` 를 view 보다 먼저 import 한다.
- E2E 스펙은 `test/e2e/*.spec.js`, 결과물은 `test/e2e/artifacts/`.

### 콘텐츠 파이프라인

텔레그램(hermes agent) → `.claude/skills/nexus-writer/`(check_writer → session → save_article) →
`contents/*.html` → 인제스트 잡(즉시 시도 + 60초 안전망) → `articles`(source_type=internal).
어드민 직접 작성 글은 source `authored` 로 발행 후 24시간 카테고리 상단 고정(`AUTHORED_PRIORITY_HOURS`).
