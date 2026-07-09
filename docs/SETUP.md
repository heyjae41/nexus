# NEXUS 개발환경 구성 가이드 (신규 서버 온보딩)

GitHub 저장소에서 클론한 뒤 현재 개발환경과 동일하게 구성하고
모든 프로세스(백엔드·프론트엔드·수집 체인·테스트)를 실행하는 절차입니다.

## 0. 사전 요구사항

| 항목 | 버전 | 비고 |
|---|---|---|
| Python | 3.11+ | `uv` 또는 venv |
| Node.js | 22+ | npm 포함 |
| PostgreSQL | 14+ | 로컬 또는 Docker |
| Redis | 7+ | 선택 — 없으면 InMemory 캐시로 자동 폴백 |
| Docker | 최신 | 배포 스택 실행 시에만 필요 |

## 1. 클론 및 환경변수

```bash
git clone https://github.com/heyjae41/nexus.git && cd nexus
cp .env.example .env
# .env 에서 DB 접속정보(DB_PASSWORD 등)를 환경에 맞게 수정
```

`.env` 는 git 미추적이다. 전 설정 항목은 `.env.example` 에 주석과 함께 정리되어 있다.

## 2. 데이터베이스 준비

```bash
# DB 생성 (이미 있으면 생략)
psql -h localhost -U postgres -d template1 -c "CREATE DATABASE paybooc_ai;"
```

- 테이블 생성과 시드(카테고리 5종 + 샘플 큐레이션 글 6건 + 커뮤니티 샘플 글 5건)는
  3단계의 `python -m app.seed` 가 멱등하게 수행한다.
- **기존 DB 를 이어받는 경우**: `backend/migrations/*.sql` 을 번호 순서대로 적용한다.
  (신규 DB 는 create_all 이 최신 스키마로 생성하므로 불필요)

## 3. 백엔드

```bash
uv venv .venv --python 3.11 && . .venv/bin/activate
pip install -r backend/requirements-dev.txt   # 사내망 TLS 이슈 시 uv 대신 pip 사용
(cd backend && python -m app.seed)            # 테이블 생성 + 시드 (멱등)
PYTHONPATH=backend uvicorn app.main:app --port 8000 --reload
```

기동과 함께 스케줄러가 시작된다:
- **인제스트** 1분 주기 — `contents/*.html` → DB (저장 도구가 즉시 반영도 시도)
- **수집 체인** 12시간 주기 — 브런치 → event-us → luma AI → luma TECH 순차

수동 트리거(내부 API, 로컬에서만 접근):
```bash
curl -X POST localhost:8000/api/internal/ingest/run
curl -X POST localhost:8000/api/internal/brunch/run
curl -X POST localhost:8000/api/internal/meetup/run   # event-us + luma 전체
```

## 4. 프론트엔드

```bash
cd frontend && npm install && npm run dev    # http://localhost:5173 (API 는 8000 으로 프록시)
```

## 5. 텔레그램 발행 스킬 (hermes agent)

- 작가 화이트리스트: 루트에 `.writer_whitelist` 파일 생성 (git 미추적, `.writer_whitelist.example` 참고).
  등록되지 않은 텔레그램 userid 는 모든 발행/세션 도구가 차단한다 (fail-closed).
- hermes agent 는 `.claude/skills/nexus-writer/SKILL.md` 의 호출 규격대로
  `telegram_user_id`(메타데이터 출처)와 글감을 전달한다. 도구 실행은 프로젝트 venv 를 사용한다.

## 6. 테스트·품질 게이트

```bash
. .venv/bin/activate
python -m pytest test                          # 백엔드 단위 + API (SQLite in-memory — PG 불필요)
python -m pytest test --cov=backend/app        # 커버리지 (기준 80%+)
cd frontend && npm test                        # 프론트 컴포넌트 테스트 (vitest)
npm run lint                                   # ESLint
cd .. && ruff check backend test               # 파이썬 린트
radon cc backend/app -n C -s                   # 복잡도 (출력 없어야 정상)
npx jscpd backend/app frontend/src --min-tokens 40   # 중복 코드

# E2E (옵션): backend(8000) + frontend dev(5173) 실행 상태에서
cd frontend && npx playwright install chromium && npm run e2e
```

## 7. Docker 배포 스택 (선택)

```bash
docker compose up -d --build    # http://localhost:8080
```
postgres/redis 포함 4개 컨테이너. DB/Redis 포트는 외부 미노출, `/api/internal/*` 는 nginx 가 차단.

## 8. 알려진 환경 이슈

- 사내망에서 `uv pip install` 이 TLS(UnknownIssuer) 로 실패할 수 있다 → `python -m pip install` 사용.
- Vite 개발 서버가 켜진 상태에서 git 브랜치 전환 시 설정 파일이 일시적으로 사라지면
  서버가 잘못된 상태로 자동 재시작될 수 있다 → 증상(빈 화면, "React is not defined") 시 `npm run dev` 재실행.
- 공유 Redis 를 쓰는 경우 키 프리픽스 `nexus:` 로 격리되어 있으니 그대로 두면 된다.

## 9. 문서 지도

| 문서 | 내용 |
|---|---|
| `README.md` | 서비스 개요·콘텐츠 파이프라인·캐시 정책 요약 |
| `docs/ARCHITECTURE.md` | 시스템 구성·DB 스키마·캐시 정책 상세 |
| `docs/DESIGN_SPEC.md` | Claude Design 시안 기반 UI 구현 명세 (프론트 수정 시 기준) |
| `CLAUDE.md` | Claude Code 작업 규칙 (TDD·품질 게이트·프로젝트 관례) |
| `.claude/skills/nexus-writer/SKILL.md` | 텔레그램 글 발행 스킬 규격 |
