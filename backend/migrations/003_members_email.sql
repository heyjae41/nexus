-- 003: members 이메일 컬럼 추가 (최초 1회 등록, 수정 불가 정책)
-- 실행: PGPASSWORD=... psql -h <host> -U <user> -d <db> -f backend/migrations/003_members_email.sql
ALTER TABLE members ADD COLUMN IF NOT EXISTS email VARCHAR(200);
CREATE UNIQUE INDEX IF NOT EXISTS ux_members_email ON members (email);
