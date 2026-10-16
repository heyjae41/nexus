-- ============================================================================
-- 운영 DB 스키마를 개발(dev RDS) 기준으로 맞추는 동기화 스크립트
-- 기준: backend/app/models.py + backend/migrations/001~015 (dev RDS 에 적용 완료된 상태)
-- 성격: 멱등(IF NOT EXISTS) · 비파괴 — 기존 데이터·테이블을 지우지 않는다.
--       두 번 실행해도 같은 결과. 하나의 트랜잭션이라 중간 실패 시 전부 롤백된다.
-- 대상: EDU.AI 소유 17개 테이블만. bc_merchant_validation / naver_merchant_capture 는 건드리지 않는다.
-- 실행: 백엔드(스케줄러) 중지 → PGPASSWORD=... psql -h <운영host> -U <user> -d <db> -v ON_ERROR_STOP=1 \
--         -f migration/sync_schema_to_dev.sql  → 백엔드 재기동
-- 이 스크립트는 backend/app/models.py 에서 생성했다. 모델이 바뀌면 다시 생성할 것.
-- ============================================================================

\set ON_ERROR_STOP on
BEGIN;
-- 다른 세션이 테이블을 잡고 있으면 무한 대기하지 않고 실패(→ 전체 롤백)한다.
-- 백엔드 Deployment 를 0 으로 줄이고 collect_once CronJob 을 중지한 뒤 실행할 것.
SET LOCAL lock_timeout = '5s';
SET LOCAL search_path = public;

-- 0) 사전 점검 — 004 이전 DB 에 source_url 중복이 있으면 유니크 인덱스 생성 전에 명확한 메시지로 중단한다.
DO $$
DECLARE dup integer;
BEGIN
  SELECT count(*) INTO dup FROM (
    SELECT source_url FROM articles WHERE source_url IS NOT NULL GROUP BY source_url HAVING count(*) > 1
  ) d;
  IF dup > 0 THEN
    RAISE EXCEPTION 'articles.source_url 중복 % 건 — 중복 글을 정리한 뒤 다시 실행 (SELECT source_url, count(*) FROM articles GROUP BY 1 HAVING count(*) > 1)', dup;
  END IF;
END $$;

-- 1) 운영에 아예 없는 테이블 생성 (courses, card_benefits, auth_sessions 등)
CREATE TABLE IF NOT EXISTS card_benefit_collect_runs (
	id SERIAL NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	candidates_count INTEGER DEFAULT 0 NOT NULL, 
	added_count INTEGER DEFAULT 0 NOT NULL, 
	error_message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS card_benefits (
	id SERIAL NOT NULL, 
	source_id VARCHAR(50) NOT NULL, 
	card_company VARCHAR(50) NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	event_period VARCHAR(100) NOT NULL, 
	event_start_date DATE, 
	event_end_date DATE, 
	target_cards VARCHAR(500), 
	benefit_summary VARCHAR(500), 
	countries VARCHAR(200), 
	benefit_tags VARCHAR(200), 
	detail_url VARCHAR(1000) NOT NULL, 
	image_url VARCHAR(1000), 
	status VARCHAR(20) DEFAULT 'published' NOT NULL, 
	collected_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (source_id), 
	UNIQUE (detail_url)
);
CREATE TABLE IF NOT EXISTS categories (
	id SERIAL NOT NULL, 
	slug VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(300), 
	display_order INTEGER DEFAULT 0 NOT NULL, 
	is_active BOOLEAN DEFAULT true NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (slug)
);
CREATE TABLE IF NOT EXISTS courses (
	id SERIAL NOT NULL, 
	source_type VARCHAR(30) NOT NULL, 
	source_id VARCHAR(50) NOT NULL, 
	source_category_code VARCHAR(50) NOT NULL, 
	source_category_name VARCHAR(100) NOT NULL, 
	source_category_url VARCHAR(1000) NOT NULL, 
	source_rank INTEGER DEFAULT 0 NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	summary TEXT, 
	source_url VARCHAR(1000) NOT NULL, 
	thumbnail_url VARCHAR(1000), 
	sub_category_name VARCHAR(100), 
	format_name VARCHAR(100), 
	qualification VARCHAR(100), 
	running_time_minutes INTEGER, 
	sale_price INTEGER, 
	list_price INTEGER, 
	badges VARCHAR(200) NOT NULL, 
	status VARCHAR(20) DEFAULT 'published' NOT NULL, 
	collected_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (source_id), 
	UNIQUE (source_url)
);
CREATE TABLE IF NOT EXISTS fastcampus_collect_runs (
	id SERIAL NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	candidates_count INTEGER DEFAULT 0 NOT NULL, 
	added_count INTEGER DEFAULT 0 NOT NULL, 
	updated_count INTEGER DEFAULT 0 NOT NULL, 
	hidden_count INTEGER DEFAULT 0 NOT NULL, 
	error_message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS meetup_collect_runs (
	id SERIAL NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	candidates_count INTEGER DEFAULT 0 NOT NULL, 
	added_count INTEGER DEFAULT 0 NOT NULL, 
	error_message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS meetup_events (
	id SERIAL NOT NULL, 
	source_id VARCHAR(50) NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	host_name VARCHAR(100), 
	source_url VARCHAR(1000) NOT NULL, 
	event_start TIMESTAMP WITH TIME ZONE, 
	event_end TIMESTAMP WITH TIME ZONE, 
	place VARCHAR(300), 
	area VARCHAR(100), 
	address VARCHAR(300), 
	price_min INTEGER, 
	is_free BOOLEAN, 
	view_count INTEGER DEFAULT 0 NOT NULL, 
	event_system_type VARCHAR(20), 
	category VARCHAR(100), 
	cover_image_url VARCHAR(1000), 
	status VARCHAR(20) DEFAULT 'published' NOT NULL, 
	collected_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (source_id), 
	UNIQUE (source_url)
);
CREATE TABLE IF NOT EXISTS members (
	id SERIAL NOT NULL, 
	nickname VARCHAR(50) NOT NULL, 
	password_hash VARCHAR(300), 
	role VARCHAR(20), 
	interests VARCHAR(300), 
	access_role VARCHAR(20) DEFAULT 'user' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nickname)
);
CREATE TABLE IF NOT EXISTS newsletter_collect_runs (
	id SERIAL NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	candidates_count INTEGER DEFAULT 0 NOT NULL, 
	added_count INTEGER DEFAULT 0 NOT NULL, 
	error_message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS writer_messages (
	id SERIAL NOT NULL, 
	telegram_user_id BIGINT NOT NULL, 
	role VARCHAR(12) NOT NULL, 
	content TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS writer_sessions (
	telegram_user_id BIGINT NOT NULL, 
	summary TEXT, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (telegram_user_id)
);
CREATE TABLE IF NOT EXISTS articles (
	id SERIAL NOT NULL, 
	category_id INTEGER NOT NULL, 
	article_type VARCHAR(20) NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	summary VARCHAR(500), 
	body_html TEXT, 
	key_visual_html TEXT, 
	author_name VARCHAR(100), 
	author_member_id INTEGER, 
	source_type VARCHAR(20) NOT NULL, 
	source_url VARCHAR(1000), 
	thumbnail_url VARCHAR(1000), 
	content_filename VARCHAR(300), 
	read_minutes INTEGER DEFAULT 4 NOT NULL, 
	likes_count INTEGER DEFAULT 0 NOT NULL, 
	comments_count INTEGER DEFAULT 0 NOT NULL, 
	view_count INTEGER DEFAULT 0 NOT NULL, 
	status VARCHAR(20) DEFAULT 'published' NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(category_id) REFERENCES categories (id), 
	FOREIGN KEY(author_member_id) REFERENCES members (id) ON DELETE SET NULL, 
	UNIQUE (source_url), 
	UNIQUE (content_filename)
);
CREATE TABLE IF NOT EXISTS auth_sessions (
	id BIGSERIAL NOT NULL, 
	member_id INTEGER NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(member_id) REFERENCES members (id) ON DELETE CASCADE, 
	UNIQUE (token_hash)
);
CREATE TABLE IF NOT EXISTS community_posts (
	id SERIAL NOT NULL, 
	member_id INTEGER, 
	author_name VARCHAR(50) NOT NULL, 
	tag VARCHAR(20) NOT NULL, 
	title VARCHAR(300) NOT NULL, 
	body TEXT NOT NULL, 
	likes_count INTEGER DEFAULT 0 NOT NULL, 
	comments_count INTEGER DEFAULT 0 NOT NULL, 
	status VARCHAR(20) DEFAULT 'published' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(member_id) REFERENCES members (id)
);
CREATE TABLE IF NOT EXISTS brunch_collect_runs (
	id SERIAL NOT NULL, 
	window_start TIMESTAMP WITH TIME ZONE NOT NULL, 
	window_end TIMESTAMP WITH TIME ZONE NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	candidates_count INTEGER DEFAULT 0 NOT NULL, 
	picked_article_id INTEGER, 
	error_message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(picked_article_id) REFERENCES articles (id)
);
CREATE TABLE IF NOT EXISTS community_comments (
	id SERIAL NOT NULL, 
	post_id INTEGER NOT NULL, 
	member_id INTEGER, 
	author_name VARCHAR(50) NOT NULL, 
	body TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(post_id) REFERENCES community_posts (id), 
	FOREIGN KEY(member_id) REFERENCES members (id)
);
CREATE TABLE IF NOT EXISTS community_post_likes (
	post_id INTEGER NOT NULL, 
	member_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (post_id, member_id), 
	FOREIGN KEY(post_id) REFERENCES community_posts (id), 
	FOREIGN KEY(member_id) REFERENCES members (id)
);

-- 2) 기존 테이블에 빠진 컬럼 추가
--    이력상 추가된 컬럼: articles.thumbnail_url(002), members.password_hash(007),
--    card_benefits.countries(013), members.access_role(014), articles.author_member_id(015).
--    그 밖에 NULL 허용/DEFAULT 있는 모든 모델 컬럼도 혹시 몰라 IF NOT EXISTS 로 보강한다.
ALTER TABLE card_benefit_collect_runs ADD COLUMN IF NOT EXISTS candidates_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE card_benefit_collect_runs ADD COLUMN IF NOT EXISTS added_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE card_benefit_collect_runs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE card_benefit_collect_runs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE card_benefits ADD COLUMN IF NOT EXISTS event_start_date DATE;
ALTER TABLE card_benefits ADD COLUMN IF NOT EXISTS event_end_date DATE;
ALTER TABLE card_benefits ADD COLUMN IF NOT EXISTS target_cards VARCHAR(500);
ALTER TABLE card_benefits ADD COLUMN IF NOT EXISTS benefit_summary VARCHAR(500);
ALTER TABLE card_benefits ADD COLUMN IF NOT EXISTS countries VARCHAR(200);
ALTER TABLE card_benefits ADD COLUMN IF NOT EXISTS benefit_tags VARCHAR(200);
ALTER TABLE card_benefits ADD COLUMN IF NOT EXISTS image_url VARCHAR(1000);
ALTER TABLE card_benefits ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'published' NOT NULL;
ALTER TABLE card_benefits ADD COLUMN IF NOT EXISTS collected_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS description VARCHAR(300);
ALTER TABLE categories ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true NOT NULL;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS source_rank INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(1000);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS sub_category_name VARCHAR(100);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS format_name VARCHAR(100);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS qualification VARCHAR(100);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS running_time_minutes INTEGER;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS sale_price INTEGER;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS list_price INTEGER;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'published' NOT NULL;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS collected_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE fastcampus_collect_runs ADD COLUMN IF NOT EXISTS candidates_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE fastcampus_collect_runs ADD COLUMN IF NOT EXISTS added_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE fastcampus_collect_runs ADD COLUMN IF NOT EXISTS updated_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE fastcampus_collect_runs ADD COLUMN IF NOT EXISTS hidden_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE fastcampus_collect_runs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE fastcampus_collect_runs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE meetup_collect_runs ADD COLUMN IF NOT EXISTS candidates_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE meetup_collect_runs ADD COLUMN IF NOT EXISTS added_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE meetup_collect_runs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE meetup_collect_runs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS host_name VARCHAR(100);
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS event_start TIMESTAMP WITH TIME ZONE;
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS event_end TIMESTAMP WITH TIME ZONE;
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS place VARCHAR(300);
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS area VARCHAR(100);
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS address VARCHAR(300);
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS price_min INTEGER;
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS is_free BOOLEAN;
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS event_system_type VARCHAR(20);
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS category VARCHAR(100);
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS cover_image_url VARCHAR(1000);
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'published' NOT NULL;
ALTER TABLE meetup_events ADD COLUMN IF NOT EXISTS collected_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE members ADD COLUMN IF NOT EXISTS password_hash VARCHAR(300);
ALTER TABLE members ADD COLUMN IF NOT EXISTS role VARCHAR(20);
ALTER TABLE members ADD COLUMN IF NOT EXISTS interests VARCHAR(300);
ALTER TABLE members ADD COLUMN IF NOT EXISTS access_role VARCHAR(20) DEFAULT 'user' NOT NULL;
ALTER TABLE members ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE newsletter_collect_runs ADD COLUMN IF NOT EXISTS candidates_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE newsletter_collect_runs ADD COLUMN IF NOT EXISTS added_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE newsletter_collect_runs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE newsletter_collect_runs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE writer_messages ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE writer_sessions ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE writer_sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS summary VARCHAR(500);
ALTER TABLE articles ADD COLUMN IF NOT EXISTS body_html TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS key_visual_html TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS author_name VARCHAR(100);
ALTER TABLE articles ADD COLUMN IF NOT EXISTS author_member_id INTEGER REFERENCES members(id) ON DELETE SET NULL;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS source_url VARCHAR(1000);
ALTER TABLE articles ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(1000);
ALTER TABLE articles ADD COLUMN IF NOT EXISTS content_filename VARCHAR(300);
ALTER TABLE articles ADD COLUMN IF NOT EXISTS read_minutes INTEGER DEFAULT 4 NOT NULL;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS likes_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS comments_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'published' NOT NULL;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS member_id INTEGER REFERENCES members(id);
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS likes_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS comments_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'published' NOT NULL;
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE brunch_collect_runs ADD COLUMN IF NOT EXISTS candidates_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE brunch_collect_runs ADD COLUMN IF NOT EXISTS picked_article_id INTEGER REFERENCES articles(id);
ALTER TABLE brunch_collect_runs ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE brunch_collect_runs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE community_comments ADD COLUMN IF NOT EXISTS member_id INTEGER REFERENCES members(id);
ALTER TABLE community_comments ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
ALTER TABLE community_post_likes ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL;
-- NOT NULL·DEFAULT 없음이라 자동 추가 불가(테이블 생성 시점부터 있던 컬럼). 7) 검증 쿼리로 확인:
--   card_benefit_collect_runs.status, card_benefits.source_id, card_benefits.card_company, card_benefits.title, card_benefits.event_period, card_benefits.detail_url, categories.slug, categories.name, courses.source_type, courses.source_id, courses.source_category_code, courses.source_category_name, courses.source_category_url, courses.title, courses.source_url, courses.badges, fastcampus_collect_runs.status, meetup_collect_runs.status, meetup_events.source_id, meetup_events.title, meetup_events.source_url, members.nickname, newsletter_collect_runs.status, writer_messages.telegram_user_id, writer_messages.role, writer_messages.content, articles.category_id, articles.article_type, articles.title, articles.source_type, articles.published_at, auth_sessions.member_id, auth_sessions.token_hash, auth_sessions.expires_at, community_posts.author_name, community_posts.tag, community_posts.title, community_posts.body, brunch_collect_runs.window_start, brunch_collect_runs.window_end, brunch_collect_runs.status, community_comments.post_id, community_comments.author_name, community_comments.body

-- 3) DEFAULT / NULL 허용 정합 (005 server_default, 001 meetup 가격 nullable)
ALTER TABLE card_benefit_collect_runs ALTER COLUMN candidates_count SET DEFAULT 0;
ALTER TABLE card_benefit_collect_runs ALTER COLUMN added_count SET DEFAULT 0;
ALTER TABLE card_benefit_collect_runs ALTER COLUMN error_message DROP NOT NULL;
ALTER TABLE card_benefit_collect_runs ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE card_benefits ALTER COLUMN event_start_date DROP NOT NULL;
ALTER TABLE card_benefits ALTER COLUMN event_end_date DROP NOT NULL;
ALTER TABLE card_benefits ALTER COLUMN target_cards DROP NOT NULL;
ALTER TABLE card_benefits ALTER COLUMN benefit_summary DROP NOT NULL;
ALTER TABLE card_benefits ALTER COLUMN countries DROP NOT NULL;
ALTER TABLE card_benefits ALTER COLUMN benefit_tags DROP NOT NULL;
ALTER TABLE card_benefits ALTER COLUMN image_url DROP NOT NULL;
ALTER TABLE card_benefits ALTER COLUMN status SET DEFAULT 'published';
ALTER TABLE card_benefits ALTER COLUMN collected_at SET DEFAULT now();
ALTER TABLE categories ALTER COLUMN description DROP NOT NULL;
ALTER TABLE categories ALTER COLUMN display_order SET DEFAULT 0;
ALTER TABLE categories ALTER COLUMN is_active SET DEFAULT true;
ALTER TABLE categories ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE courses ALTER COLUMN source_rank SET DEFAULT 0;
ALTER TABLE courses ALTER COLUMN summary DROP NOT NULL;
ALTER TABLE courses ALTER COLUMN thumbnail_url DROP NOT NULL;
ALTER TABLE courses ALTER COLUMN sub_category_name DROP NOT NULL;
ALTER TABLE courses ALTER COLUMN format_name DROP NOT NULL;
ALTER TABLE courses ALTER COLUMN qualification DROP NOT NULL;
ALTER TABLE courses ALTER COLUMN running_time_minutes DROP NOT NULL;
ALTER TABLE courses ALTER COLUMN sale_price DROP NOT NULL;
ALTER TABLE courses ALTER COLUMN list_price DROP NOT NULL;
ALTER TABLE courses ALTER COLUMN status SET DEFAULT 'published';
ALTER TABLE courses ALTER COLUMN collected_at SET DEFAULT now();
ALTER TABLE courses ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE fastcampus_collect_runs ALTER COLUMN candidates_count SET DEFAULT 0;
ALTER TABLE fastcampus_collect_runs ALTER COLUMN added_count SET DEFAULT 0;
ALTER TABLE fastcampus_collect_runs ALTER COLUMN updated_count SET DEFAULT 0;
ALTER TABLE fastcampus_collect_runs ALTER COLUMN hidden_count SET DEFAULT 0;
ALTER TABLE fastcampus_collect_runs ALTER COLUMN error_message DROP NOT NULL;
ALTER TABLE fastcampus_collect_runs ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE meetup_collect_runs ALTER COLUMN candidates_count SET DEFAULT 0;
ALTER TABLE meetup_collect_runs ALTER COLUMN added_count SET DEFAULT 0;
ALTER TABLE meetup_collect_runs ALTER COLUMN error_message DROP NOT NULL;
ALTER TABLE meetup_collect_runs ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE meetup_events ALTER COLUMN host_name DROP NOT NULL;
ALTER TABLE meetup_events ALTER COLUMN event_start DROP NOT NULL;
ALTER TABLE meetup_events ALTER COLUMN event_end DROP NOT NULL;
ALTER TABLE meetup_events ALTER COLUMN place DROP NOT NULL;
ALTER TABLE meetup_events ALTER COLUMN area DROP NOT NULL;
ALTER TABLE meetup_events ALTER COLUMN address DROP NOT NULL;
ALTER TABLE meetup_events ALTER COLUMN price_min DROP NOT NULL;
ALTER TABLE meetup_events ALTER COLUMN is_free DROP NOT NULL;
ALTER TABLE meetup_events ALTER COLUMN view_count SET DEFAULT 0;
ALTER TABLE meetup_events ALTER COLUMN event_system_type DROP NOT NULL;
ALTER TABLE meetup_events ALTER COLUMN category DROP NOT NULL;
ALTER TABLE meetup_events ALTER COLUMN cover_image_url DROP NOT NULL;
ALTER TABLE meetup_events ALTER COLUMN status SET DEFAULT 'published';
ALTER TABLE meetup_events ALTER COLUMN collected_at SET DEFAULT now();
ALTER TABLE members ALTER COLUMN password_hash DROP NOT NULL;
ALTER TABLE members ALTER COLUMN role DROP NOT NULL;
ALTER TABLE members ALTER COLUMN interests DROP NOT NULL;
ALTER TABLE members ALTER COLUMN access_role SET DEFAULT 'user';
ALTER TABLE members ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE newsletter_collect_runs ALTER COLUMN candidates_count SET DEFAULT 0;
ALTER TABLE newsletter_collect_runs ALTER COLUMN added_count SET DEFAULT 0;
ALTER TABLE newsletter_collect_runs ALTER COLUMN error_message DROP NOT NULL;
ALTER TABLE newsletter_collect_runs ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE writer_messages ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE writer_sessions ALTER COLUMN summary DROP NOT NULL;
ALTER TABLE writer_sessions ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE articles ALTER COLUMN summary DROP NOT NULL;
ALTER TABLE articles ALTER COLUMN body_html DROP NOT NULL;
ALTER TABLE articles ALTER COLUMN key_visual_html DROP NOT NULL;
ALTER TABLE articles ALTER COLUMN author_name DROP NOT NULL;
ALTER TABLE articles ALTER COLUMN author_member_id DROP NOT NULL;
ALTER TABLE articles ALTER COLUMN source_url DROP NOT NULL;
ALTER TABLE articles ALTER COLUMN thumbnail_url DROP NOT NULL;
ALTER TABLE articles ALTER COLUMN content_filename DROP NOT NULL;
ALTER TABLE articles ALTER COLUMN read_minutes SET DEFAULT 4;
ALTER TABLE articles ALTER COLUMN likes_count SET DEFAULT 0;
ALTER TABLE articles ALTER COLUMN comments_count SET DEFAULT 0;
ALTER TABLE articles ALTER COLUMN view_count SET DEFAULT 0;
ALTER TABLE articles ALTER COLUMN status SET DEFAULT 'published';
ALTER TABLE articles ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE articles ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE auth_sessions ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE community_posts ALTER COLUMN member_id DROP NOT NULL;
ALTER TABLE community_posts ALTER COLUMN likes_count SET DEFAULT 0;
ALTER TABLE community_posts ALTER COLUMN comments_count SET DEFAULT 0;
ALTER TABLE community_posts ALTER COLUMN status SET DEFAULT 'published';
ALTER TABLE community_posts ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE brunch_collect_runs ALTER COLUMN candidates_count SET DEFAULT 0;
ALTER TABLE brunch_collect_runs ALTER COLUMN picked_article_id DROP NOT NULL;
ALTER TABLE brunch_collect_runs ALTER COLUMN error_message DROP NOT NULL;
ALTER TABLE brunch_collect_runs ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE community_comments ALTER COLUMN member_id DROP NOT NULL;
ALTER TABLE community_comments ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE community_post_likes ALTER COLUMN created_at SET DEFAULT now();

-- 4) 인덱스 (마이그레이션 004/006/010/011/015 와 모델 정의, 이름은 dev RDS 와 동일하게)
CREATE UNIQUE INDEX IF NOT EXISTS ux_articles_source_url ON articles (source_url);
CREATE INDEX IF NOT EXISTS ix_articles_author_member ON articles (author_member_id);
CREATE INDEX IF NOT EXISTS ix_card_benefits_start ON card_benefits (event_start_date);
CREATE INDEX IF NOT EXISTS ix_courses_status_category_rank ON courses (status, source_category_code, source_rank);
CREATE INDEX IF NOT EXISTS ix_meetup_events_start ON meetup_events (event_start);
CREATE INDEX IF NOT EXISTS ix_writer_messages_user_created ON writer_messages (telegram_user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_articles_category_status_published ON articles (category_id, status, published_at);
CREATE INDEX IF NOT EXISTS ix_articles_type_published ON articles (article_type, published_at);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_member ON auth_sessions (member_id);
CREATE INDEX IF NOT EXISTS ix_community_posts_status_created ON community_posts (status, created_at);
CREATE INDEX IF NOT EXISTS ix_community_posts_member ON community_posts (member_id);
CREATE INDEX IF NOT EXISTS ix_community_comments_member ON community_comments (member_id);
CREATE INDEX IF NOT EXISTS ix_community_comments_post ON community_comments (post_id);

-- 5) 데이터 보정 — 015 작성자 백필 (author_member_id 가 비어 있는 직접 작성 글만, 멱등)
--    주의: 이 스크립트가 access_role 을 새로 추가한 DB 라면 모든 회원이 'user' 라 여기서 연결되는 글이 없다.
--    어드민 권한을 부여한 뒤 이 UPDATE 를 다시 실행하고, 8) 의 미연결 글 목록이 비었는지 확인한다.
UPDATE articles a SET author_member_id = m.id
  FROM members m
 WHERE a.source_type = 'authored' AND a.author_member_id IS NULL
   AND m.nickname = a.author_name
   AND m.access_role = 'admin'
   AND m.created_at <= a.created_at;

-- 6) 선택 항목 (기본 주석 처리 — 운영 데이터를 보고 판단 후 해제)
-- 007: dev 에는 members.email 이 없다. 운영에 남아 있으면 개인정보 컬럼이라 지우는 것이 정책이나 데이터 삭제다.
-- DROP INDEX IF EXISTS ux_members_email;
-- ALTER TABLE members DROP COLUMN IF EXISTS email;
-- 008: 브런치 글 article_type 'brunch' → 'column' 재분류
-- UPDATE articles SET article_type = 'column', updated_at = CURRENT_TIMESTAMP WHERE article_type = 'brunch';
-- 009: 폐지된 '질문' 태그 글 숨김
-- UPDATE community_posts SET status = 'hidden' WHERE tag = '질문' AND status = 'published';
-- 012: 중복 인제스트 글 삭제
-- DELETE FROM articles WHERE content_filename = '20260724_가이드_핫딜탐색AI에게맡기는법.html';

COMMIT;

-- 7) 검증 — 아래 3개 결과를 dev RDS 의 같은 쿼리 결과와 diff 한다.
--    data_type·character_maximum_length 차이는 이 스크립트가 고치지 않는다(ALTER TYPE 없음) — 수동 조치 대상.
SELECT table_name, column_name, data_type, character_maximum_length, is_nullable, column_default
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND table_name IN ('card_benefit_collect_runs', 'card_benefits', 'categories', 'courses', 'fastcampus_collect_runs', 'meetup_collect_runs', 'meetup_events', 'members', 'newsletter_collect_runs', 'writer_messages', 'writer_sessions', 'articles', 'auth_sessions', 'community_posts', 'brunch_collect_runs', 'community_comments', 'community_post_likes')
 ORDER BY table_name, column_name;

SELECT tablename, indexdef
  FROM pg_indexes
 WHERE schemaname = 'public'
   AND tablename IN ('card_benefit_collect_runs', 'card_benefits', 'categories', 'courses', 'fastcampus_collect_runs', 'meetup_collect_runs', 'meetup_events', 'members', 'newsletter_collect_runs', 'writer_messages', 'writer_sessions', 'articles', 'auth_sessions', 'community_posts', 'brunch_collect_runs', 'community_comments', 'community_post_likes')
 ORDER BY tablename, indexname;

SELECT conrelid::regclass AS table_name, contype, pg_get_constraintdef(oid) AS definition
  FROM pg_constraint
 WHERE connamespace = 'public'::regnamespace
   AND conrelid::regclass::text IN ('card_benefit_collect_runs', 'card_benefits', 'categories', 'courses', 'fastcampus_collect_runs', 'meetup_collect_runs', 'meetup_events', 'members', 'newsletter_collect_runs', 'writer_messages', 'writer_sessions', 'articles', 'auth_sessions', 'community_posts', 'brunch_collect_runs', 'community_comments', 'community_post_likes')
 ORDER BY 1, 3;

-- 8) 데이터 점검 — 0 건/빈 결과가 정상
SELECT id, author_name FROM articles WHERE source_type = 'authored' AND author_member_id IS NULL;  -- 수정 불가 상태의 직접 작성 글
SELECT count(*) AS brunch_typed_articles FROM articles WHERE article_type = 'brunch';             -- 0 아니면 6) 의 008 해제 검토
