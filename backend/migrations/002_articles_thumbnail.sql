-- 002: articles 대표 이미지 컬럼 추가 (브런치 수집 글 썸네일)
-- 실행: PGPASSWORD=... psql -h <host> -U <user> -d <db> -f backend/migrations/002_articles_thumbnail.sql
ALTER TABLE articles ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(1000);
