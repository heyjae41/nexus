-- 011: HttpOnly 쿠키 기반 서버 로그인 세션
-- 쿠키의 원문 토큰은 저장하지 않고 SHA-256 해시(64자)만 저장한다.
CREATE TABLE IF NOT EXISTS auth_sessions (
    id BIGSERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_member ON auth_sessions(member_id);
