"""DB 엔진/세션 관리 테스트."""


def test_get_engine_caches_and_get_db_yields_session(monkeypatch, tmp_path):
    """get_engine 은 최초 1회만 생성해 재사용하고, get_db 는 요청 단위 세션을 준다."""
    from app import db as db_mod

    monkeypatch.setattr(db_mod, "_engine", None)
    monkeypatch.setattr(db_mod, "_session_factory", None)

    class FakeSettings:
        database_url = f"sqlite:///{tmp_path}/t.db"

    monkeypatch.setattr(db_mod, "get_settings", lambda: FakeSettings())

    engine = db_mod.get_engine()
    assert engine is db_mod.get_engine()  # 캐시 재사용 (재생성 없음)

    gen = db_mod.get_db()
    session = next(gen)
    assert session.get_bind() is engine
    gen.close()  # finally 경로 — 세션 close


def test_is_unique_violation_distinguishes_error_kinds():
    """UNIQUE 위반(레이스)과 NOT NULL 등 실제 결함을 구분한다."""
    from sqlalchemy.exc import IntegrityError

    from app.db import is_unique_violation

    def make(msg):
        return IntegrityError("stmt", {}, Exception(msg))

    assert is_unique_violation(make("UNIQUE constraint failed: articles.source_url"))
    assert is_unique_violation(make('duplicate key value violates unique constraint "ux"'))
    assert not is_unique_violation(make("NOT NULL constraint failed: articles.title"))
    assert not is_unique_violation(make("FOREIGN KEY constraint failed"))
