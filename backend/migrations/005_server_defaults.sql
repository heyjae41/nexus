-- 005: DB 레벨 DEFAULT 부여 — ORM 우회(raw SQL/배치) INSERT 도 ARCHITECTURE.md 명세대로 동작
-- 실행: PGPASSWORD=... psql -h <host> -U <user> -d <db> -f backend/migrations/005_server_defaults.sql
ALTER TABLE categories ALTER COLUMN display_order SET DEFAULT 0;
ALTER TABLE categories ALTER COLUMN is_active SET DEFAULT true;
ALTER TABLE categories ALTER COLUMN created_at SET DEFAULT now();

ALTER TABLE articles ALTER COLUMN read_minutes SET DEFAULT 4;
ALTER TABLE articles ALTER COLUMN likes_count SET DEFAULT 0;
ALTER TABLE articles ALTER COLUMN comments_count SET DEFAULT 0;
ALTER TABLE articles ALTER COLUMN view_count SET DEFAULT 0;
ALTER TABLE articles ALTER COLUMN status SET DEFAULT 'published';
ALTER TABLE articles ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE articles ALTER COLUMN updated_at SET DEFAULT now();

ALTER TABLE members ALTER COLUMN created_at SET DEFAULT now();

ALTER TABLE community_posts ALTER COLUMN likes_count SET DEFAULT 0;
ALTER TABLE community_posts ALTER COLUMN comments_count SET DEFAULT 0;
ALTER TABLE community_posts ALTER COLUMN status SET DEFAULT 'published';
ALTER TABLE community_posts ALTER COLUMN created_at SET DEFAULT now();

ALTER TABLE community_post_likes ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE community_comments ALTER COLUMN created_at SET DEFAULT now();

ALTER TABLE meetup_events ALTER COLUMN view_count SET DEFAULT 0;
ALTER TABLE meetup_events ALTER COLUMN status SET DEFAULT 'published';
ALTER TABLE meetup_events ALTER COLUMN collected_at SET DEFAULT now();

ALTER TABLE meetup_collect_runs ALTER COLUMN candidates_count SET DEFAULT 0;
ALTER TABLE meetup_collect_runs ALTER COLUMN added_count SET DEFAULT 0;
ALTER TABLE meetup_collect_runs ALTER COLUMN created_at SET DEFAULT now();

ALTER TABLE writer_sessions ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE writer_messages ALTER COLUMN created_at SET DEFAULT now();

ALTER TABLE brunch_collect_runs ALTER COLUMN candidates_count SET DEFAULT 0;
ALTER TABLE brunch_collect_runs ALTER COLUMN created_at SET DEFAULT now();
