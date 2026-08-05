-- card.Pick 국가별 필터: 이벤트 대상 지역 컬럼 추가
-- 값: 쉼표 구분 지역명 (예: '일본' / '동남아,베트남' / '해외공통' / '국내·기타')
-- 백필은 수집기 재실행(_apply_updates)이 수행한다.
ALTER TABLE card_benefits ADD COLUMN IF NOT EXISTS countries VARCHAR(200);
