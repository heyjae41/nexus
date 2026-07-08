# NEXUS — BC카드 AI사업팀 커뮤니케이션 채널

퇴근 후 30분, 금융 AI 한 스푼. 직장인을 위한 AI 팁·BC카드 AI 전환 사례·행사(밋플)·핫딜을
제공하는 B2C 반응형 웹서비스입니다. Claude Design 시안을 기반으로 구현했습니다.

## 구성

| 경로 | 설명 |
|---|---|
| `frontend/` | React(Vite) SPA — 반응형(PC/모바일) |
| `backend/` | FastAPI — 공개 API + 인제스트/브런치 수집 스케줄러 |
| `test/` | 모든 테스트 (backend 단위 / api / frontend / e2e) |
| `contents/` | 텔레그램(hermes agent) 발행 글이 저장되는 폴더 |
| `.claude/skills/nexus-writer/` | hermes agent 가 호출하는 글 생성 스킬 + 도구 |
| `docs/` | 아키텍처(DB 스키마·캐시 정책) / 디자인 명세 |

## 빠른 시작 (로컬 개발)

사전 요구: Python 3.11+, Node 22+, PostgreSQL, Redis(선택 — 없으면 InMemory 캐시로 폴백)

```bash
cp .env.example .env               # 환경변수 설정 (DB 접속정보 등)

# 백엔드
uv venv .venv --python 3.11 && . .venv/bin/activate
pip install -r backend/requirements-dev.txt
(cd backend && python -m app.seed) # 테이블 생성 + 카테고리/샘플 글 시드
PYTHONPATH=backend uvicorn app.main:app --port 8000 --reload

# 프론트엔드 (새 터미널)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

## 테스트

```bash
. .venv/bin/activate
python -m pytest test                          # 단위 + API (SQLite in-memory, PG 불필요)
python -m pytest test --cov=backend/app        # 커버리지 (기준 80%+)
cd frontend && npm test                        # 프론트엔드 컴포넌트 테스트

# E2E (옵션): backend(8000) + frontend dev(5173) 실행 상태에서
cd frontend && npm run e2e                     # Playwright 스모크 (test/e2e)
```

품질 검사:
```bash
ruff check backend test        # 문법/린트
radon cc backend/app -n C -s   # 복잡도 (C 이상 출력 시 리팩토링)
npx jscpd backend/app frontend/src --min-tokens 40   # 중복 코드
```

## 배포 (Docker)

```bash
docker compose up -d --build   # http://localhost:8080
```
postgres/redis 는 내부 네트워크 전용(포트 미노출)이며 설정은 `.env` 로 주입됩니다.

## 콘텐츠 파이프라인

1. **텔레그램 발행**: 팀원이 hermes agent(텔레그램 봇)에게 글감을 보내면
   `nexus-writer` 스킬이 4분 분량 글 + 개념 애니메이션 키비주얼을 생성해
   `contents/날짜_글유형_제목.html` (유형: 뉴스레터/컬럼/가이드) 로 저장합니다.
   - **작가 권한**: 문서 루트 `.writer_whitelist` 에 등록된 텔레그램 userid 만 발행 가능
     (fail-closed, `.writer_whitelist.example` 참고 — 파일은 git 미추적).
   - **대화 세션**: 작가(userid)별로 대화 맥락이 DB에 분리 저장되어 혼재되지 않고,
     서버 재기동에도 유지됩니다. 대화가 길어지면 요약으로 자동 압축(토큰 비용 제어),
     "초기화" 요청 시 리셋됩니다.
2. **인제스트**: 저장 직후 도구가 즉시 반영을 시도하고(지연 0초), 실패 시
   1분 주기 스케줄러가 안전망으로 반영합니다. 파일이 원본(감사/복구/재처리용)으로 남고
   DB 입력 시 캐시가 즉시 무효화됩니다 → 메인/목록에 바로 반영.
3. **브런치 수집(12시간 주기)**: brunch.co.kr 의 AI 관련 글 중 기간 내
   `댓글수+좋아요수` 최다 글 1건을 선정해 목록에 노출합니다.
   클릭 시 원글로 이동하며 항상 `?ref=nexus.bccard.ai` 가 붙습니다.

수동 실행: `POST /api/internal/ingest/run`, `POST /api/internal/brunch/run`

## 캐시 정책

cache-aside + **네임스페이스 버전 무효화** (`nexus:v{N}:*`).
신규 글 등록 등 쓰기 발생 시 버전 키 INCR → 이전 캐시 전체 즉시 무효(O(1)).
상세: `docs/ARCHITECTURE.md`
