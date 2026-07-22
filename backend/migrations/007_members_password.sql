-- 007: 회원 인증 정책 전환 — 이메일 제거, 비밀번호(PBKDF2 해시) 도입
-- 기존 회원의 password_hash 는 NULL(레거시) — 로그인 시 인증 실패로 처리되며,
-- 정책 전환 시점에 회원 데이터가 없다면 영향 없음.
-- 실행: PGPASSWORD=... psql -h <host> -U <user> -d <db> -f backend/migrations/007_members_password.sql
ALTER TABLE members ADD COLUMN IF NOT EXISTS password_hash VARCHAR(300);
DROP INDEX IF EXISTS ux_members_email;
ALTER TABLE members DROP COLUMN IF EXISTS email;
