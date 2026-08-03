"""테스트 격리 가드 — 테스트가 실제 PostgreSQL 에 접속하는 것을 차단한다.

과거 스케줄러 체인 테스트가 card.Pick 단계를 mock 하지 않아 pytest 실행마다
실 DB 로 실제 수집이 나간 사고의 재발 방지 장치다 (conftest autouse 픽스처).
"""
import pytest


def test_real_db_access_is_blocked_in_tests():
    import app.db as app_db

    with pytest.raises(RuntimeError, match="실 DB"):
        app_db.get_engine()


def test_scheduler_module_reference_is_also_blocked():
    """scheduler 는 모듈 상단에서 get_engine 을 import 하므로 그 참조도 차단."""
    from app.services import scheduler as scheduler_module

    with pytest.raises(RuntimeError, match="실 DB"):
        scheduler_module.get_engine()
