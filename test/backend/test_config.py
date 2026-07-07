"""설정(.env 환경변수) 로딩 테스트."""
from app.config import Settings


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DB_NAME", "paybooc_ai")
    monkeypatch.setenv("DB_USER", "postgres")
    monkeypatch.setenv("DB_PASSWORD", "pw")
    monkeypatch.setenv("DB_HOST", "dbhost")
    monkeypatch.setenv("DB_PORT", "5433")
    s = Settings(_env_file=None)
    assert s.db_name == "paybooc_ai"
    assert s.database_url == "postgresql+psycopg://postgres:pw@dbhost:5433/paybooc_ai"


def test_settings_defaults(monkeypatch):
    for k in ("REDIS_URL", "CACHE_PREFIX", "INGEST_INTERVAL_SECONDS"):
        monkeypatch.delenv(k, raising=False)
    s = Settings(_env_file=None)
    assert s.cache_prefix == "nexus:"
    assert s.cache_ttl_seconds == 300
    assert s.ingest_interval_seconds == 60
    assert s.brunch_collect_interval_hours == 12
    assert s.brunch_ref_query == "ref=nexus.bccard.ai"
