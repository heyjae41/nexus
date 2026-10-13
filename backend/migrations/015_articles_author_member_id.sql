-- 015: 직접 작성 글의 작성자를 닉네임이 아니라 회원 ID 로 묶는다 (보안 점검 2026-10 HIGH 2).
-- 닉네임은 바꾸거나 탈회 후 남이 선점할 수 있어 권한 키로 쓸 수 없다.
ALTER TABLE articles ADD COLUMN IF NOT EXISTS author_member_id INTEGER
    REFERENCES members(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_articles_author_member ON articles (author_member_id);
-- 기존 authored 글 백필: 같은 닉네임이면서 어드민이고 글보다 먼저 가입한 회원에게만 연결한다.
-- (옛 닉네임을 나중에 선점한 계정에게 소유권이 넘어가지 않도록.) 연결 안 된 글은 아무도 수정 불가 —
-- 필요하면 목록을 확인하고 수동으로 author_member_id 를 지정한다.
UPDATE articles a SET author_member_id = m.id
  FROM members m
 WHERE a.source_type = 'authored' AND a.author_member_id IS NULL
   AND m.nickname = a.author_name
   AND m.access_role = 'admin'
   AND m.created_at <= a.created_at;
