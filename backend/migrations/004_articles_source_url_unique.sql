-- 004: articles.source_url 유니크 제약 (브런치 스케줄러/수동 트리거 동시 수집 중복 방지)
-- 실행: PGPASSWORD=... psql -h <host> -U <user> -d <db> -f backend/migrations/004_articles_source_url_unique.sql
CREATE UNIQUE INDEX IF NOT EXISTS ux_articles_source_url ON articles (source_url);
