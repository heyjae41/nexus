"""환경변수(.env) 기반 서비스 설정."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    db_name: str = "paybooc_ai"
    db_user: str = "postgres"
    db_password: str = ""
    db_host: str = "localhost"
    db_port: int = 5432

    # Redis / cache
    redis_url: str = "redis://localhost:6379/0"
    cache_prefix: str = "nexus:"
    cache_ttl_seconds: int = 300

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    # Ingest
    contents_dir: str = "./contents"
    ingest_interval_seconds: int = 60

    # Brunch collector
    brunch_collect_interval_hours: int = 12
    brunch_ref_query: str = "ref=nexus.bccard.ai"
    brunch_base_url: str = "https://brunch.co.kr"

    # 수집 체인 (브런치 → event-us → luma 순차 실행) 주기
    collect_chain_interval_hours: int = 12

    # Meetup collector (event-us.kr)
    meetup_query: str = "ai ax"
    meetup_categories: str = "IT/프로그래밍,경제/금융"
    meetup_window_days: int = 14

    # Meetup collector (luma.com) — "카테고리ID:표시라벨" 쉼표 구분
    luma_categories: str = "cat-ai:AI,cat-tech:TECH"

    @property
    def meetup_category_list(self) -> list[str]:
        return [c.strip() for c in self.meetup_categories.split(",") if c.strip()]

    @property
    def luma_category_pairs(self) -> list[tuple[str, str]]:
        pairs = []
        for token in self.luma_categories.split(","):
            if ":" in token:
                cid, label = token.split(":", 1)
                pairs.append((cid.strip(), label.strip()))
        return pairs

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
