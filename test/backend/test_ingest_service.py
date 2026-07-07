"""/contents 폴더 인제스트 서비스 테스트.

- 1분 주기(스케줄러)로 폴더를 스캔하여 신규 html 을 DB 에 입력한다.
- 파일명 규칙 위반 파일은 건너뛰고 나머지는 처리한다.
- 이미 입력된 파일(content_filename 중복)은 재입력하지 않는다.
- 입력 성공 시 캐시가 무효화되어 메인/목록에 즉시 반영된다.
"""
from app.cache import InMemoryCacheBackend, VersionedCache
from app.models import Category
from app.repositories.articles import list_articles
from app.services.ingest import scan_contents_dir

HTML = """<!doctype html><html><head><title>t</title></head>
<body>
<article>
  <div class="key-visual"><svg><circle r="5"/></svg></div>
  <p>직장인을 위한 AI 활용 팁 본문입니다.</p>
</article>
</body></html>"""


def make_cache():
    return VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)


def seed_curation(db):
    db.add(Category(slug="curation", name="큐레이션", display_order=1))
    db.commit()


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


def test_ingest_extracts_key_visual(db, tmp_path):
    seed_curation(db)
    cache = make_cache()
    write_file(tmp_path, "20260707_뉴스레터_비주얼.html")
    scan_contents_dir(db, cache, str(tmp_path))
    art = list_articles(db).items[0]
    assert "svg" in (art.key_visual_html or "")
