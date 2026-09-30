"""환경변수(.env) 기반 서비스 설정."""
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_pairs(raw: str) -> list[tuple[str, str]]:
    """"키:라벨" 쉼표 구분 문자열 → (키, 라벨) 목록 (형식 밖 항목은 무시)."""
    pairs = []
    for token in raw.split(","):
        if ":" in token:
            key, label = token.split(":", 1)
            pairs.append((key.strip(), label.strip()))
    return pairs


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

    # Media — 영구 보관 파일(에디터 본문 이미지, 인제스트 썸네일)의 루트.
    # 배포 파드에서는 /app/media 에 S3 가 마운트되어 재기동 후에도 남는다
    # (docker/backend.Dockerfile 이 MEDIA_DIR=/app/media 로 고정).
    media_dir: str = "./media"
    # true 면 media_dir 이 마운트 포인트가 아닐 때 기동을 거부한다 (배포 이미지 기본값)
    media_require_mount: bool = False

    # Brunch collector
    brunch_collect_interval_hours: int = 12
    brunch_ref_query: str = "ref=nexus.bccard.ai"
    brunch_base_url: str = "https://brunch.co.kr"

    # 수집 체인 (브런치 → event-us → luma 순차 실행) 주기
    collect_chain_interval_hours: int = 12
    # false 면 in-process 스케줄러에서 수집 체인을 빼고 인제스트만 돌린다
    # (K8s 배포에서 수집을 CronJob(app.collect_once)으로 분리할 때 사용)
    enable_crawl_scheduler: bool = True

    # Meetup collector (event-us.kr)
    meetup_query: str = "ai ax"
    meetup_categories: str = "IT/프로그래밍,경제/금융"
    meetup_window_days: int = 14

    # Meetup collector (luma.com) — "카테고리ID:표시라벨" 쉼표 구분
    luma_categories: str = "cat-ai:AI,cat-tech:TECH"

    # Newsletter collector — 스티비 아카이브 "listId:뉴스레터이름" 쉼표 구분 + KMA 인사이트
    newsletter_stibee_lists: str = "297134:테크잇슈,212479:셀렉트 다이제스트,181723:모두레터"
    stibee_page_base_url: str = "https://page.stibee.com"
    newsletter_kma_base_url: str = "https://www.kma.or.kr"
    aitimes_base_url: str = "https://www.aitimes.com"
    newsletter_window_days: int = 7

    # 권한관리 화면을 열 닉네임. 쉼표로 구분. 글쓰기 권한은 members.access_role 이다.
    super_admin: str = ""

    @field_validator("media_dir")
    @classmethod
    def _absolute_media_dir(cls, value: str) -> str:
        """기동 시점의 cwd 기준으로 절대경로를 고정한다 — 이후 chdir 에 흔들리지 않는다.

        빈 값은 cwd 전체(/app: 소스·.env·.writer_whitelist)를 /api/media 로 노출하므로 거부한다."""
        if not value.strip():
            raise ValueError("MEDIA_DIR 은 비워 둘 수 없습니다")
        return str(Path(value.strip()).expanduser().resolve())

    @property
    def meetup_category_list(self) -> list[str]:
        return [c.strip() for c in self.meetup_categories.split(",") if c.strip()]

    @property
    def luma_category_pairs(self) -> list[tuple[str, str]]:
        return _split_pairs(self.luma_categories)

    @property
    def newsletter_stibee_pairs(self) -> list[tuple[str, str]]:
        return _split_pairs(self.newsletter_stibee_lists)

    @property
    def super_admin_set(self) -> set[str]:
        return {name.strip() for name in self.super_admin.split(",") if name.strip()}

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
