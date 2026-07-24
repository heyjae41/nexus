"""공용 테스트 픽스처: SQLite in-memory DB 세션."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base


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
