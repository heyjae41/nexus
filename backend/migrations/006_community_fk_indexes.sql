-- 006: community FK 조회 인덱스 — PG 는 FK 컬럼에 자동 인덱스를 만들지 않는다
-- (게시글별 댓글 조회, 탈회 시 회원 연결 해제 경로의 seq scan 방지)
-- 실행: PGPASSWORD=... psql -h <host> -U <user> -d <db> -f backend/migrations/006_community_fk_indexes.sql
CREATE INDEX IF NOT EXISTS ix_community_posts_member ON community_posts (member_id);
CREATE INDEX IF NOT EXISTS ix_community_comments_post ON community_comments (post_id);
CREATE INDEX IF NOT EXISTS ix_community_comments_member ON community_comments (member_id);
