# NEXUS 프로젝트 — Claude Code 작업 규칙

BC카드 AI사업팀 커뮤니케이션 채널 (React + FastAPI + PostgreSQL + Redis).
처음 왔다면 `docs/SETUP.md`(환경 구성) → `docs/ARCHITECTURE.md`(구조) 순서로 읽는다.

## 작업 방식 (필수)

- **TDD**: 프로덕션 코드 작성 전에 `/test` 아래 실패하는 테스트부터 작성한다 (RED→GREEN→REFACTOR).
  - `test/backend` 단위, `test/api` FastAPI TestClient, `test/frontend` vitest, `test/e2e` Playwright(옵션)
  - 테스트 DB 는 SQLite in-memory (`test/conftest.py` 의 `db`/`engine` 픽스처, PG 불필요)
- **품질 게이트** (커밋 전 전부 통과): `python -m pytest test` · `ruff check backend test` ·
  `radon cc backend/app -n C -s`(출력 없어야 함) · `npx jscpd --min-tokens 40` ·
  프론트 변경 시 `npm run build && npx vitest run && npm run lint`
- **코드리뷰**: 기능 단위 완료 시 code-reviewer 에이전트 리뷰를 거치고 CRITICAL/HIGH 는 반드시 수정
- **브랜치**: main 직접 커밋 금지 — `feat/*` 브랜치 → 게이트 통과 → `--no-ff` 병합 → push
- 커밋 메시지는 한국어 컨벤셔널 커밋 (`feat:`, `fix:`, `docs:`, `test:`, `chore:`)

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
   (create_all 은 신규 테이블만 만든다).
7. **브라우저 dialog 금지**: 프론트에서 `alert()/confirm()` 사용 금지 — 인라인 UI 로 처리.

## 자주 쓰는 명령

```bash
PYTHONPATH=backend uvicorn app.main:app --port 8000 --reload   # 백엔드 (루트에서)
cd frontend && npm run dev                                      # 프론트
(cd backend && python -m app.seed)                              # 시드 (멱등)
curl -X POST localhost:8000/api/internal/meetup/run             # 수집 수동 실행
```

## 구조 요약

- `backend/app/` — api(라우터) / services(수집·인제스트·스킬 로직) / repositories(DB 조회) /
  models.py / cache.py(버전 무효화) / seed.py
- `frontend/src/` — views(페이지) / components / api/client.js / styles(tokens.css 디자인 토큰)
- UI 는 `docs/DESIGN_SPEC.md` 의 픽셀 명세를 따른다 (색상·타이포·브레이크포인트 860/560px)
