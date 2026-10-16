# EDU.AI PostgreSQL 스키마·데이터 이관

로컬 `paybooc_ai`의 EDU.AI 소유 테이블 17개만 개발 서버 PostgreSQL로 옮기는 도구다.
동일 DB를 공유하는 타 프로젝트 테이블 `bc_merchant_validation`, `naver_merchant_capture`는 덤프·삭제·복원 대상에서 제외한다.

## 포함 파일

- `nexus_tables.txt`: SQLAlchemy 모델(`backend/app/models.py`)과 일치하는 이관 허용 목록
- `schema.sql`: 현재 로컬 DB에서 생성한 EDU.AI DDL 문서(데이터 없음)
- `export.sh`: 로컬 DB의 스키마+데이터 커스텀 덤프 및 검증 매니페스트 생성
- `import.sh`: 기존 EDU.AI 테이블 교체 후 트랜잭션 단위 복원
- `verify.sh`: 테이블별 행 수와 컬럼 정의를 소스 매니페스트와 비교
- `sync_schema_to_dev.sql`: 데이터를 유지한 채 대상 DB 스키마를 현재 모델(마이그레이션 001~015) 기준으로 맞추는 멱등 스크립트
- `bootstrap/`: 신규 서버 최초 이전용으로 검증해 커밋한 스키마·데이터 번들
- `artifacts/`: 이후 export 결과. 개인정보가 포함될 수 있어 Git에서 제외

## 1. 로컬 DB 내보내기

프로젝트 루트 `.env`를 기본으로 사용한다. `.env`는 공백이 든 값도 안전하게 읽으며 셸에서 직접 `source`하지 않는다. 일관된 덤프와 검증 기준을 만들기 위해 먼저 백엔드 프로세스를 중지하여 DB 쓰기를 차단한다.

```bash
bash migration/export.sh
```

다른 환경파일이나 출력 폴더를 지정할 수도 있다.

```bash
bash migration/export.sh ./local.env ./migration/artifacts
```

생성물:

- `migration/artifacts/nexus.dump`
- `migration/artifacts/restore.list`
- `migration/artifacts/SHA256SUMS`
- `migration/artifacts/row_counts.tsv`
- `migration/artifacts/schema_columns.tsv`
- `migration/schema.sql`

## 2. 개발 서버로 전송

커밋된 `bootstrap`은 저장소를 clone/pull하면 함께 내려온다. 이후 새로 생성한 `artifacts`에는 회원 이메일, 커뮤니티 글, 작가 세션 등이 포함될 수 있으므로 공개 저장소나 메신저에 올리지 않고 SSH/SCP 등 암호화된 경로로 전송한다.

```bash
scp -r migration/artifacts user@dev-server:/path/to/nexus/migration/
```

대상 서버에는 DB 접속정보만 담은 환경파일(예: `.env.server`)을 준비한다. 대상 데이터베이스 자체는 미리 생성되어 있어야 한다.

## 3. 대상 DB 가져오기

대상의 기존 EDU.AI 테이블 17개를 삭제한 뒤 덤프 데이터로 교체한다. 삭제·복원·행 수·스키마 검증은 하나의 트랜잭션이므로 중간에 실패하면 기존 EDU.AI 데이터까지 원상 복구된다. `CASCADE`를 사용하지 않으며 타 프로젝트 공유 테이블은 삭제하지 않는다.

API 요청이나 스케줄러 쓰기와 충돌하지 않도록 대상 서버의 백엔드 프로세스를 먼저 중지한다. 복원과 검증이 끝난 뒤 백엔드를 다시 시작한다.

```bash
bash migration/import.sh ./.env.server ./migration/bootstrap/nexus.dump
```

커밋된 `bootstrap` 번들은 테이블 17개와 데이터 1,090행을 포함한다. `row_counts.tsv`, `schema_columns.tsv`, `restore.list`, `SHA256SUMS`는 필수이며 복원 과정에서 자동 검증한다. 수동 재검증:

```bash
bash migration/verify.sh ./.env.server ./migration/bootstrap
```

## 4. 애플리케이션 확인

```bash
curl -fsS http://localhost:8000/api/health
curl -fsS http://localhost:8000/api/home
```

스케줄러는 별도 cron이 아니라 FastAPI 프로세스의 lifespan에서 시작된다(`backend/app/main.py`). 백엔드가 계속 실행 중이어야 하며, interval 작업의 최초 자동 실행은 프로세스 시작 후 12시간 뒤다. 이관 직후 수집 상태를 맞추려면 서버 내부에서 한 번 수동 실행한다.

```bash
curl -X POST http://localhost:8000/api/internal/ingest/run
curl -X POST http://localhost:8000/api/internal/meetup/run
curl -X POST http://localhost:8000/api/internal/brunch/run
```

Docker 배포에서는 nginx가 `/api/internal/*` 외부 호출을 차단하므로 백엔드 컨테이너 내부 또는 서버 localhost에서 실행한다.

## 데이터 유지 스키마 동기화

export/import 는 대상 데이터를 원본 데이터로 **교체**한다. 대상(예: 운영) 데이터를 살린 채 개발에서 추가한
테이블·컬럼만 따라잡으려면 `sync_schema_to_dev.sql` 을 쓴다. 두 스크립트 모두 실행한 PC 에서 env/접속 정보의
DB 로 네트워크 접속하므로, 대상 DB 5432 에 닿는 곳에서 실행한다.

```bash
# 백엔드 중지·백업 후
PGPASSWORD=... psql -h <대상host> -U <user> -d <db> -v ON_ERROR_STOP=1 -f migration/sync_schema_to_dev.sql
```

- 없는 테이블 생성, 없는 컬럼 추가, DEFAULT·NULL 허용·인덱스 정합, 015 작성자 백필(빈 값만)을 한 트랜잭션으로 실행한다.
- 컬럼 삭제(007 `members.email`)와 데이터 보정(008/009/012)은 파일 6) 섹션에 주석으로만 두었다 — 대상 데이터를 보고 해제한다.
- 실행 전 백엔드 Deployment 를 0 으로 줄이고 `collect_once` CronJob 을 중지한다. 테이블 잠금을 5초 안에 못 얻으면 전체 롤백된다.
- `articles.source_url` 중복이 있으면 0) 사전 점검에서 중단된다 — 중복 글을 정리하고 다시 실행한다.
- 7) 검증 쿼리 3개(컬럼·인덱스·제약)를 기준 DB 결과와 diff 한다. 컬럼 타입·길이 차이는 스크립트가 고치지 않으므로 수동 조치한다.
- 8) 점검에서 `author_member_id` 가 빈 직접 작성 글이 나오면(대상 DB 에 `access_role` 이 없던 경우 전원 `user` 라 백필이 안 된다)
  권한관리에서 어드민을 부여한 뒤 5) 백필 UPDATE 만 다시 실행한다. `article_type='brunch'` 건수가 0 이 아니면 008 을 해제한다.
- 첫 줄 `\set` 은 psql 전용이다. GUI 클라이언트에서는 그 줄을 빼고 실행한다.
- `backend/app/models.py` 에서 생성한 파일이므로 모델이나 마이그레이션이 바뀌면 함께 갱신한다.

## 안전 원칙

- 운영/개발 대상 DB에 가져오기 전에 별도 백업을 만든다.
- import는 EDU.AI 테이블 17개만 삭제 후 교체하며 공유 테이블은 삭제하지 않는다.
- `CASCADE`를 사용하지 않으므로 타 프로젝트 객체가 EDU.AI 테이블을 참조하면 삭제하지 않고 전체 작업이 실패한다.
- 덤프·스키마·검증 파일의 SHA-256이 모두 일치해야 복원을 시작한다.
- 덤프는 `--no-owner --no-privileges`로 생성해 로컬 DB role/ACL을 이식하지 않는다.
- 검증된 `restore.list`의 객체만 복원하며, 기존 EDU.AI 삭제·복원·행 수·스키마 검증을 하나의 트랜잭션으로 실행해 부분 반영을 방지한다.
