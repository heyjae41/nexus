--
-- PostgreSQL database dump
--

\restrict B5SAPCtBGUP3l3ypvq6DYxhHRxLN0h9AAaLP65bcdpSXNcfrZ2dbEUNh6cBY1tQ

-- Dumped from database version 14.22 (Homebrew)
-- Dumped by pg_dump version 14.22 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: articles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.articles (
    id integer NOT NULL,
    category_id integer NOT NULL,
    article_type character varying(20) NOT NULL,
    title character varying(300) NOT NULL,
    summary character varying(500),
    body_html text,
    key_visual_html text,
    author_name character varying(100),
    source_type character varying(20) NOT NULL,
    source_url character varying(1000),
    content_filename character varying(300),
    read_minutes integer NOT NULL,
    likes_count integer NOT NULL,
    comments_count integer NOT NULL,
    view_count integer NOT NULL,
    status character varying(20) NOT NULL,
    published_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    thumbnail_url character varying(1000)
);


--
-- Name: articles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.articles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: articles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.articles_id_seq OWNED BY public.articles.id;


--
-- Name: brunch_collect_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.brunch_collect_runs (
    id integer NOT NULL,
    window_start timestamp with time zone NOT NULL,
    window_end timestamp with time zone NOT NULL,
    status character varying(20) NOT NULL,
    candidates_count integer NOT NULL,
    picked_article_id integer,
    error_message text,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: brunch_collect_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.brunch_collect_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: brunch_collect_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.brunch_collect_runs_id_seq OWNED BY public.brunch_collect_runs.id;


--
-- Name: categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.categories (
    id integer NOT NULL,
    slug character varying(50) NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(300),
    display_order integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: categories_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.categories_id_seq OWNED BY public.categories.id;


--
-- Name: community_comments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.community_comments (
    id integer NOT NULL,
    post_id integer NOT NULL,
    member_id integer,
    author_name character varying(50) NOT NULL,
    body text NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: community_comments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.community_comments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: community_comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.community_comments_id_seq OWNED BY public.community_comments.id;


--
-- Name: community_post_likes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.community_post_likes (
    post_id integer NOT NULL,
    member_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: community_posts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.community_posts (
    id integer NOT NULL,
    member_id integer,
    author_name character varying(50) NOT NULL,
    tag character varying(20) NOT NULL,
    title character varying(300) NOT NULL,
    body text NOT NULL,
    likes_count integer NOT NULL,
    comments_count integer NOT NULL,
    status character varying(20) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: community_posts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.community_posts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: community_posts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.community_posts_id_seq OWNED BY public.community_posts.id;


--
-- Name: meetup_collect_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.meetup_collect_runs (
    id integer NOT NULL,
    status character varying(20) NOT NULL,
    candidates_count integer NOT NULL,
    added_count integer NOT NULL,
    error_message text,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: meetup_collect_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.meetup_collect_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: meetup_collect_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.meetup_collect_runs_id_seq OWNED BY public.meetup_collect_runs.id;


--
-- Name: meetup_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.meetup_events (
    id integer NOT NULL,
    source_id character varying(50) NOT NULL,
    title character varying(300) NOT NULL,
    host_name character varying(100),
    source_url character varying(1000) NOT NULL,
    event_start timestamp with time zone,
    event_end timestamp with time zone,
    place character varying(300),
    area character varying(100),
    address character varying(300),
    price_min integer,
    is_free boolean,
    view_count integer NOT NULL,
    event_system_type character varying(20),
    category character varying(100),
    cover_image_url character varying(1000),
    status character varying(20) NOT NULL,
    collected_at timestamp with time zone NOT NULL
);


--
-- Name: meetup_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.meetup_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: meetup_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.meetup_events_id_seq OWNED BY public.meetup_events.id;


--
-- Name: members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.members (
    id integer NOT NULL,
    nickname character varying(50) NOT NULL,
    role character varying(20),
    interests character varying(300),
    created_at timestamp with time zone NOT NULL,
    email character varying(200)
);


--
-- Name: members_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.members_id_seq OWNED BY public.members.id;


--
-- Name: writer_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.writer_messages (
    id integer NOT NULL,
    telegram_user_id bigint NOT NULL,
    role character varying(12) NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: writer_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.writer_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: writer_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.writer_messages_id_seq OWNED BY public.writer_messages.id;


--
-- Name: writer_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.writer_sessions (
    telegram_user_id bigint NOT NULL,
    summary text,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: writer_sessions_telegram_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.writer_sessions_telegram_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: writer_sessions_telegram_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.writer_sessions_telegram_user_id_seq OWNED BY public.writer_sessions.telegram_user_id;


--
-- Name: articles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.articles ALTER COLUMN id SET DEFAULT nextval('public.articles_id_seq'::regclass);


--
-- Name: brunch_collect_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.brunch_collect_runs ALTER COLUMN id SET DEFAULT nextval('public.brunch_collect_runs_id_seq'::regclass);


--
-- Name: categories id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories ALTER COLUMN id SET DEFAULT nextval('public.categories_id_seq'::regclass);


--
-- Name: community_comments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.community_comments ALTER COLUMN id SET DEFAULT nextval('public.community_comments_id_seq'::regclass);


--
-- Name: community_posts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.community_posts ALTER COLUMN id SET DEFAULT nextval('public.community_posts_id_seq'::regclass);


--
-- Name: meetup_collect_runs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.meetup_collect_runs ALTER COLUMN id SET DEFAULT nextval('public.meetup_collect_runs_id_seq'::regclass);


--
-- Name: meetup_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.meetup_events ALTER COLUMN id SET DEFAULT nextval('public.meetup_events_id_seq'::regclass);


--
-- Name: members id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.members ALTER COLUMN id SET DEFAULT nextval('public.members_id_seq'::regclass);


--
-- Name: writer_messages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.writer_messages ALTER COLUMN id SET DEFAULT nextval('public.writer_messages_id_seq'::regclass);


--
-- Name: writer_sessions telegram_user_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.writer_sessions ALTER COLUMN telegram_user_id SET DEFAULT nextval('public.writer_sessions_telegram_user_id_seq'::regclass);


--
-- Name: articles articles_content_filename_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_content_filename_key UNIQUE (content_filename);


--
-- Name: articles articles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_pkey PRIMARY KEY (id);


--
-- Name: brunch_collect_runs brunch_collect_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.brunch_collect_runs
    ADD CONSTRAINT brunch_collect_runs_pkey PRIMARY KEY (id);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: categories categories_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_slug_key UNIQUE (slug);


--
-- Name: community_comments community_comments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.community_comments
    ADD CONSTRAINT community_comments_pkey PRIMARY KEY (id);


--
-- Name: community_post_likes community_post_likes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.community_post_likes
    ADD CONSTRAINT community_post_likes_pkey PRIMARY KEY (post_id, member_id);


--
-- Name: community_posts community_posts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.community_posts
    ADD CONSTRAINT community_posts_pkey PRIMARY KEY (id);


--
-- Name: meetup_collect_runs meetup_collect_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.meetup_collect_runs
    ADD CONSTRAINT meetup_collect_runs_pkey PRIMARY KEY (id);


--
-- Name: meetup_events meetup_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.meetup_events
    ADD CONSTRAINT meetup_events_pkey PRIMARY KEY (id);


--
-- Name: meetup_events meetup_events_source_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.meetup_events
    ADD CONSTRAINT meetup_events_source_id_key UNIQUE (source_id);


--
-- Name: meetup_events meetup_events_source_url_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.meetup_events
    ADD CONSTRAINT meetup_events_source_url_key UNIQUE (source_url);


--
-- Name: members members_nickname_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.members
    ADD CONSTRAINT members_nickname_key UNIQUE (nickname);


--
-- Name: members members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.members
    ADD CONSTRAINT members_pkey PRIMARY KEY (id);


--
-- Name: writer_messages writer_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.writer_messages
    ADD CONSTRAINT writer_messages_pkey PRIMARY KEY (id);


--
-- Name: writer_sessions writer_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.writer_sessions
    ADD CONSTRAINT writer_sessions_pkey PRIMARY KEY (telegram_user_id);


--
-- Name: ix_articles_category_status_published; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_articles_category_status_published ON public.articles USING btree (category_id, status, published_at);


--
-- Name: ix_articles_type_published; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_articles_type_published ON public.articles USING btree (article_type, published_at);


--
-- Name: ix_community_posts_status_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_community_posts_status_created ON public.community_posts USING btree (status, created_at);


--
-- Name: ix_meetup_events_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_meetup_events_start ON public.meetup_events USING btree (event_start);


--
-- Name: ix_writer_messages_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_writer_messages_user_created ON public.writer_messages USING btree (telegram_user_id, created_at);


--
-- Name: ux_members_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_members_email ON public.members USING btree (email);


--
-- Name: articles articles_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id);


--
-- Name: brunch_collect_runs brunch_collect_runs_picked_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.brunch_collect_runs
    ADD CONSTRAINT brunch_collect_runs_picked_article_id_fkey FOREIGN KEY (picked_article_id) REFERENCES public.articles(id);


--
-- Name: community_comments community_comments_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.community_comments
    ADD CONSTRAINT community_comments_member_id_fkey FOREIGN KEY (member_id) REFERENCES public.members(id);


--
-- Name: community_comments community_comments_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.community_comments
    ADD CONSTRAINT community_comments_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.community_posts(id);


--
-- Name: community_post_likes community_post_likes_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.community_post_likes
    ADD CONSTRAINT community_post_likes_member_id_fkey FOREIGN KEY (member_id) REFERENCES public.members(id);


--
-- Name: community_post_likes community_post_likes_post_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.community_post_likes
    ADD CONSTRAINT community_post_likes_post_id_fkey FOREIGN KEY (post_id) REFERENCES public.community_posts(id);


--
-- Name: community_posts community_posts_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.community_posts
    ADD CONSTRAINT community_posts_member_id_fkey FOREIGN KEY (member_id) REFERENCES public.members(id);


--
-- PostgreSQL database dump complete
--

\unrestrict B5SAPCtBGUP3l3ypvq6DYxhHRxLN0h9AAaLP65bcdpSXNcfrZ2dbEUNh6cBY1tQ

