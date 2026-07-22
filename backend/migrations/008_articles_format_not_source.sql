-- article_type 은 수집 사이트가 아니라 글의 속성/포맷을 나타낸다.
-- 기존 브런치 수집 글은 에세이형 외부 컬럼으로 재분류한다.
UPDATE articles
SET article_type = 'column', updated_at = CURRENT_TIMESTAMP
WHERE article_type = 'brunch';