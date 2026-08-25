# EDU.AI 개발환경 구성 가이드 (신규 서버 온보딩)

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
- **수집 체인** 12시간 주기 — 브런치 → event-us → luma AI → luma TECH → 패스트캠퍼스 → Daker 해커톤 → DACON 경진대회 순차

수동 트리거(내부 API, 로컬에서만 접근):
```bash
curl -X POST localhost:8000/api/internal/ingest/run
curl -X POST localhost:8000/api/internal/brunch/run
curl -X POST localhost:8000/api/internal/meetup/run   # event-us + luma 전체
curl -X POST localhost:8000/api/internal/classes/run  # 패스트캠퍼스 + Daker + DACON
```

## 4. 프론트엔드

```bash
cd frontend && npm install && npm run dev    # http://localhost:80 (API 는 8000 으로 프록시)
```

## 5. 텔레그램 발행 스킬 (Hermes Agent)

1. 작가 화이트리스트를 저장소 루트에 만든다. 이 파일은 Git 미추적이며, 등록되지 않은
   Telegram `message.from.id`는 모든 발행·세션 도구가 차단한다(fail-closed).

   ```bash
   cp .writer_whitelist.example .writer_whitelist
   chmod 600 .writer_whitelist
   # 한 줄에 허용할 Telegram userid 하나씩 기록
   ```

2. Hermes가 프로젝트 스킬을 발견하고 도구를 Nexus 작업 디렉터리에서 실행하도록
   `~/.hermes/config.yaml`에 등록한다.

   ```yaml
   terminal:
     cwd: /root/dev/nexus

   skills:
     external_dirs:
       - /root/dev/nexus/.claude/skills
   ```

3. Gateway를 재시작하고 스킬·권한을 확인한다.

   ```bash
   hermes gateway restart
   hermes skills list --source local | grep nexus-writer
   .venv/bin/python .claude/skills/nexus-writer/tools/check_writer.py <userid>
   ```

Hermes는 Telegram Bot API `getUpdates`를 long polling해 메시지를 받는다. 같은 봇 토큰으로
둘 이상의 Gateway가 polling하면 Telegram이 한 요청을 종료하고 `terminated by other
getUpdates request` 충돌을 반환한다. 사용자 PC, 서버, 컨테이너를 통틀어 consumer를 하나만
운영하며, 충돌 시 각 장비의 `hermes gateway status`와 서버의 다음 로그를 확인한다.

```bash
journalctl --user -u hermes-gateway --since "2 minutes ago" --no-pager
```

Hermes Agent는 `.claude/skills/nexus-writer/SKILL.md` 호출 규격대로 메타데이터에서 얻은
`telegram_user_id`와 글감을 전달한다. 본문에 사용자가 직접 적은 ID는 신뢰하지 않으며,
도구 실행에는 프로젝트 venv를 사용한다.

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

# E2E: backend + frontend dev 실행 상태에서 (주소가 다르면 E2E_BASE_URL·E2E_API 로 지정)
cd frontend && npx playwright install chromium && npm run e2e
# CI 의 e2e 잡이 시드된 임시 PG 스택으로 동일 테스트를 자동 실행한다 (.github/workflows/ci.yml)
# 주의: 시드는 백엔드 기동 '전'에 실행 (Redis 없이 인메모리 캐시면 기동 후 시드가 반영되지 않음)
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

## 9. 운영 서버 보안·서비스 구성 (2026-07 반영)

- **방화벽**: ufw 활성 — 공개 포트는 22(SSH)·80(웹)만. 백엔드 8000 은 `docker0` 인터페이스
  (프론트 컨테이너→호스트 프록시)에서만 허용.
- **Docker 포트 차단**: docker 포트포워딩(DNAT)은 ufw INPUT 을 우회하므로 PG(5432)·Redis(6379)는
  `/etc/ufw/after.rules` 의 `DOCKER-USER` 체인 규칙으로 외부(eth0) 유입을 차단한다.
  규칙 수정 후 `ufw reload`.
- **백엔드 서비스**: systemd `nexus-backend.service` (`/etc/systemd/system/`) — 재부팅 자동 기동,
  크래시 시 자동 재시작. 로그: `.omc/logs/uvicorn.log`. 재시작: `systemctl restart nexus-backend`
  (재시작 후 수집 타이머가 리셋되므로 `/api/internal/{ingest,meetup,brunch}/run` 수동 트리거 권장).
- **로그인 rate limit**: nginx 가 `/api/auth/login`·`/api/auth/register`·`/api/members` 를
  IP 당 분당 10회(burst 5)로 제한, 초과 시 429.
- **CI**: `.github/workflows/ci.yml` 이 push/PR 마다 품질 게이트(pytest·ruff·radon·vitest·eslint·build·jscpd)를 실행한다.

## 10. 문서 지도

| 문서 | 내용 |
|---|---|
| `README.md` | 서비스 개요·콘텐츠 파이프라인·캐시 정책 요약 |
| `CHANGELOG.md` | 날짜별 작업 히스토리 (기능·리팩터링·보안·인프라) |
| `docs/ARCHITECTURE.md` | 시스템 구성·DB 스키마·캐시 정책 상세 |
| `docs/DESIGN_SPEC.md` | Claude Design 시안 기반 UI 구현 명세 (프론트 수정 시 기준) |
| `CLAUDE.md` | Claude Code 작업 규칙 (TDD·품질 게이트·프로젝트 관례) |
| `.claude/skills/nexus-writer/SKILL.md` | 텔레그램 글 발행 스킬 규격 |
