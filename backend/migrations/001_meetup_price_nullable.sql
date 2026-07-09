-- 001: meetup_events 가격 컬럼 nullable 전환 (luma 등 가격 미제공 소스 지원)
-- 적용 대상: 이 마이그레이션 이전에 생성된 DB (신규 DB 는 create_all 이 nullable 로 생성)
-- 실행: PGPASSWORD=... psql -h <host> -U <user> -d <db> -f backend/migrations/001_meetup_price_nullable.sql
ALTER TABLE meetup_events ALTER COLUMN price_min DROP NOT NULL;
ALTER TABLE meetup_events ALTER COLUMN is_free DROP NOT NULL;
