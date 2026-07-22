CREATE TABLE IF NOT EXISTS courses (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(30) NOT NULL,
    source_id VARCHAR(50) NOT NULL UNIQUE,
    source_category_code VARCHAR(50) NOT NULL,
    source_category_name VARCHAR(100) NOT NULL,
    source_category_url VARCHAR(1000) NOT NULL,
    source_rank INTEGER NOT NULL DEFAULT 0,
    title VARCHAR(300) NOT NULL,
    summary TEXT,
    source_url VARCHAR(1000) NOT NULL UNIQUE,
    thumbnail_url VARCHAR(1000),
    sub_category_name VARCHAR(100),
    format_name VARCHAR(100),
    qualification VARCHAR(100),
    running_time_minutes INTEGER,
    sale_price INTEGER,
    list_price INTEGER,
    badges VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'published',
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_courses_status_category_rank
    ON courses (status, source_category_code, source_rank);

CREATE TABLE IF NOT EXISTS fastcampus_collect_runs (
    id SERIAL PRIMARY KEY,
    status VARCHAR(20) NOT NULL,
    candidates_count INTEGER NOT NULL DEFAULT 0,
    added_count INTEGER NOT NULL DEFAULT 0,
    updated_count INTEGER NOT NULL DEFAULT 0,
    hidden_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
