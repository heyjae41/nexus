"""수집 체인 1회 실행 후 종료 — K8s CronJob 엔트리 (python -m app.collect_once).

in-process 스케줄러의 run_collect_chain_job 을 그대로 호출하므로 수집 로직·순서는 동일하다.
API pod 쪽은 ENABLE_CRAWL_SCHEDULER=false 로 수집 체인을 꺼서 중복 실행을 막는다.
REDIS_URL 미설정이면 이 프로세스의 캐시 무효화가 API pod 에 전파되지 않는다
(InMemory 폴백) — API 응답은 cache_ttl_seconds(기본 300초) 내에 자연 갱신된다.
"""
import logging
import sys

from app.cache import create_cache
from app.config import get_settings
from app.services.scheduler import run_collect_chain_job


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = get_settings()
    cache = create_cache(
        settings.redis_url, settings.cache_prefix, settings.cache_ttl_seconds
    )
    run_collect_chain_job(cache)
    return 0


if __name__ == "__main__":
    sys.exit(main())
