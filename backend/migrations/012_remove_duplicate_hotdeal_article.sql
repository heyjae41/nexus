-- 같은 원고가 파일명만 달리 두 번 인제스트된 중복 글 제거 (articles/42).
-- 원본 파일(contents/20260724_가이드_핫딜탐색AI에게맡기는법.html)은 저장소에서 함께 삭제되어
-- 재인제스트되지 않는다. 하이픈 파일명 본(articles/45)이 유지본이다.
DELETE FROM articles
WHERE content_filename = '20260724_가이드_핫딜탐색AI에게맡기는법.html';
