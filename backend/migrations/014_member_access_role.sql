-- 014: 회원 서비스 권한. 프로필 role(기획자/개발자)과 분리한다.
-- user: 일반 사용자, admin: 큐레이션 글쓰기·권한관리.
ALTER TABLE members ADD COLUMN IF NOT EXISTS access_role VARCHAR(20) NOT NULL DEFAULT 'user';
