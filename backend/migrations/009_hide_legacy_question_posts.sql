-- 질문 배지는 폐지되었다. 기존 글은 삭제하지 않고 숨겨 관리자 복구 가능성을 보존한다.
UPDATE community_posts
SET status = 'hidden'
WHERE tag = '질문' AND status = 'published';
