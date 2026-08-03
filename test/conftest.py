"""공용 테스트 픽스처: SQLite in-memory DB 세션."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base


@pytest.fixture(autouse=True)
def _block_real_db(monkeypatch):
    """테스트가 실제 PostgreSQL 에 접속하는 것을 차단한다.

    스케줄러 체인 테스트가 card.Pick 단계를 mock 하지 않아 pytest 실행마다
    실 DB 로 실제 수집이 나갔던 사고의 재발 방지 장치 — get_engine 이 실 DB
    URL(postgresql)로 엔진을 만들려는 순간 실패시킨다. SQLite 는 허용된다."""
    from app import db as app_db

    real_create_engine = app_db.create_engine

    def guarded_create_engine(url, *args, **kwargs):
        if str(url).startswith("postgresql"):
            raise RuntimeError(
                "테스트에서 실 DB(PostgreSQL) 접속이 차단되었습니다 — "
                "conftest 의 SQLite 픽스처를 쓰거나 해당 의존성을 mock 하세요."
            )
        return real_create_engine(url, *args, **kwargs)

    monkeypatch.setattr(app_db, "create_engine", guarded_create_engine)
    # 테스트 간 엔진 캐시 공유 금지 — 이전 테스트의 엔진이 새어 들지 않게
    monkeypatch.setattr(app_db, "_engine", None)
    monkeypatch.setattr(app_db, "_session_factory", None)


@pytest.fixture(autouse=True)
def _isolated_media(tmp_path_factory, monkeypatch):
    """썸네일 미디어 디렉토리를 테스트별 임시 경로로 격리한다.

    인제스트가 media_dir 미지정 시 settings.media_dir 로 폴백하므로,
    격리하지 않으면 테스트가 실제 ./media 에 파일을 쓴다."""
    from app.config import get_settings

    media = tmp_path_factory.mktemp("media")
    monkeypatch.setattr(get_settings(), "media_dir", str(media))
    return str(media)


@pytest.fixture()
def engine():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db(engine) -> Session:
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    session = factory()
    yield session
    session.close()
