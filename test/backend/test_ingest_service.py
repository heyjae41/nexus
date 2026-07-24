"""/contents 폴더 인제스트 서비스 테스트.

- 1분 주기(스케줄러)로 폴더를 스캔하여 신규 html 을 DB 에 입력한다.
- 파일명 규칙 위반 파일은 건너뛰고 나머지는 처리한다.
- 이미 입력된 파일(content_filename 중복)은 재입력하지 않는다.
- 입력 성공 시 캐시가 무효화되어 메인/목록에 즉시 반영된다.
"""
from app.repositories.articles import list_articles
from app.services.ingest import scan_contents_dir

HTML = """<!doctype html><html><head><title>t</title></head>
<body>
<article>
  <div class="key-visual"><svg><circle r="5"/></svg></div>
  <p>직장인을 위한 AI 활용 팁 본문입니다.</p>
</article>
</body></html>"""


from shared import make_cache, seed_curation  # noqa: E402 — 수집 테스트 공용 헬퍼


def write_file(tmp_path, name, content=HTML):
    (tmp_path / name).write_text(content, encoding="utf-8")


def test_ingest_new_files(db, tmp_path):
    seed_curation(db)
    cache = make_cache()
    write_file(tmp_path, "20260707_뉴스레터_AI팁모음.html")
    write_file(tmp_path, "20260707_가이드_프롬프트입문.html")

    result = scan_contents_dir(db, cache, str(tmp_path))

    assert result.ingested == 2
    assert result.skipped == 0
    arts = list_articles(db).items
    assert {a.title for a in arts} == {"AI팁모음", "프롬프트입문"}
    types = {a.article_type for a in arts}
    assert types == {"newsletter", "guide"}
    assert all(a.source_type == "internal" for a in arts)
    assert all(a.body_html for a in arts)


def test_ingest_is_idempotent(db, tmp_path):
    seed_curation(db)
    cache = make_cache()
    write_file(tmp_path, "20260707_뉴스레터_AI팁모음.html")

    first = scan_contents_dir(db, cache, str(tmp_path))
    second = scan_contents_dir(db, cache, str(tmp_path))

    assert first.ingested == 1
    assert second.ingested == 0
    assert second.already == 1
    assert list_articles(db).total == 1


def test_ingest_accepts_nfd_decomposed_filenames(db, tmp_path):
    """macOS 에서 저장된 NFD(분해형) 파일명도 인제스트한다.

    글유형 판정·중복 판정·DB 저장은 NFC 정규화본 기준, 파일 IO 는 원본 이름 그대로."""
    import unicodedata

    from app.models import Article

    seed_curation(db)
    cache = make_cache()
    nfd_name = unicodedata.normalize("NFD", "20260724_가이드_맛집탐색결제데이터에맡기는법.html")
    assert not unicodedata.is_normalized("NFC", nfd_name)  # 전제 확인
    write_file(tmp_path, nfd_name)

    first = scan_contents_dir(db, cache, str(tmp_path))
    assert first.ingested == 1
    assert first.skipped == 0

    saved = db.query(Article).one()
    assert saved.article_type == "guide"
    # DB 에는 정준(NFC) 파일명으로 저장한다 — 중복 판정 키의 정규화 통일
    assert unicodedata.is_normalized("NFC", saved.content_filename)

    # 디스크 파일명은 NFD 그대로여도 재스캔 시 재인제스트하지 않는다
    second = scan_contents_dir(db, cache, str(tmp_path))
    assert second.ingested == 0
    assert second.already == 1


def test_ingest_skips_invalid_names_but_continues(db, tmp_path):
    seed_curation(db)
    cache = make_cache()
    write_file(tmp_path, "잘못된이름.html")
    write_file(tmp_path, "20260707_컬럼_정상글.html")

    result = scan_contents_dir(db, cache, str(tmp_path))

    assert result.ingested == 1
    assert result.skipped == 1
    assert list_articles(db).items[0].title == "정상글"


def test_ingest_bumps_cache_version(db, tmp_path):
    seed_curation(db)
    cache = make_cache()
    cache.set("home", "stale")
    write_file(tmp_path, "20260707_뉴스레터_새글.html")

    scan_contents_dir(db, cache, str(tmp_path))

    assert cache.get("home") is None, "신규 글 인제스트 후 캐시는 무효화되어야 한다"


def test_ingest_no_bump_when_nothing_new(db, tmp_path):
    seed_curation(db)
    cache = make_cache()
    write_file(tmp_path, "20260707_뉴스레터_새글.html")
    scan_contents_dir(db, cache, str(tmp_path))

    cache.set("home", "warm")
    scan_contents_dir(db, cache, str(tmp_path))  # 변화 없음
    assert cache.get("home") == "warm", "변화가 없으면 캐시를 유지한다"


def test_ingest_now_runs_scan_with_injected_engine(engine, tmp_path):
    """글 저장 직후 즉시 반영: ingest_now 는 스케줄러와 동일 코드 경로를 1회 실행한다."""
    from sqlalchemy.orm import Session

    from app.services.ingest import ingest_now

    with Session(bind=engine) as db:
        seed_curation(db)
    cache = make_cache()
    write_file(tmp_path, "20260708_뉴스레터_즉시반영.html")

    result = ingest_now(str(tmp_path), engine=engine, cache=cache)

    assert result is not None
    assert result.ingested == 1
    with Session(bind=engine) as db:
        assert list_articles(db).items[0].title == "즉시반영"


def test_ingest_now_swallows_failures(tmp_path, monkeypatch):
    """DB 미가용 등 실패 시 예외를 전파하지 않고 None — 1분 스케줄러가 안전망."""
    from app.services import ingest as ingest_module

    def boom(*args, **kwargs):
        raise RuntimeError("DB down")

    monkeypatch.setattr(ingest_module, "scan_contents_dir", boom)
    cache = make_cache()

    class FakeEngine:  # Session 생성 시점엔 접속하지 않으므로 형태만 충족
        pass

    result = ingest_module.ingest_now(str(tmp_path), engine=FakeEngine(), cache=cache)
    assert result is None


def test_ingest_survives_concurrent_duplicate(db, tmp_path, monkeypatch):
    """즉시 인제스트와 스케줄러가 경합해 UNIQUE 위반이 나도
    해당 파일만 already 처리하고 나머지 파일은 계속 진행해야 한다."""
    from sqlalchemy.exc import IntegrityError

    from app.services import ingest as ingest_module

    seed_curation(db)
    cache = make_cache()
    write_file(tmp_path, "20260708_뉴스레터_경합파일.html")
    write_file(tmp_path, "20260708_컬럼_정상파일.html")

    real_ingest_file = ingest_module._ingest_file

    def racy_ingest_file(session, path, canonical_name=None):
        if "경합파일" in path.name:
            raise IntegrityError("INSERT", {}, Exception("duplicate key"))
        return real_ingest_file(session, path, canonical_name=canonical_name)

    monkeypatch.setattr(ingest_module, "_ingest_file", racy_ingest_file)

    result = scan_contents_dir(db, cache, str(tmp_path))

    assert result.already == 1     # 경합 파일은 이미 처리된 것으로 집계
    assert result.ingested == 1    # 뒤 파일은 중단 없이 인제스트
    assert list_articles(db).items[0].title == "정상파일"


def test_ingest_extracts_key_visual(db, tmp_path):
    seed_curation(db)
    cache = make_cache()
    write_file(tmp_path, "20260707_뉴스레터_비주얼.html")
    scan_contents_dir(db, cache, str(tmp_path))
    art = list_articles(db).items[0]
    assert "svg" in (art.key_visual_html or "")
