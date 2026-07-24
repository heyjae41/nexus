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


def test_settings_newsletter_sources():
    s = Settings(_env_file=None)
    assert s.newsletter_window_days == 7
    assert s.newsletter_kma_base_url == "https://www.kma.or.kr"
    assert s.stibee_page_base_url == "https://page.stibee.com"
    assert s.aitimes_base_url == "https://www.aitimes.com"
    assert s.newsletter_stibee_pairs == [
        ("297134", "테크잇슈"),
        ("212479", "셀렉트 다이제스트"),
        ("181723", "모두레터"),
    ]


def test_settings_stibee_pairs_from_env(monkeypatch):
    monkeypatch.setenv("NEWSLETTER_STIBEE_LISTS", "111:레터A, 222:레터B ,깨진항목")
    s = Settings(_env_file=None)
    assert s.newsletter_stibee_pairs == [("111", "레터A"), ("222", "레터B")]
