"""인제스트(텔레그램 발행) HTML 정화 — LLM 이 만든 본문·키비주얼도 저장 전에 거른다.

보안 점검(2026-10) HIGH 3: 프롬프트 인젝션으로 <svg onload> 같은 핸들러가 심긴 글이
사람 검토 없이 1분 안에 게시될 수 있었다."""
from pathlib import Path

from app.services.content_sanitize import sanitize_ingest_html, sanitize_key_visual_html
from app.services.ingest import scan_contents_dir
from shared import make_cache, seed_curation

DATA_IMG = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD"


def _no_handlers(html: str) -> bool:
    """실제 태그/속성 기준: on* 속성, script 태그, javascript: 값이 하나도 없어야 한다."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    if soup.find("script"):
        return False
    for tag in soup.find_all(True):
        for name, value in tag.attrs.items():
            text = " ".join(value) if isinstance(value, list) else str(value)
            if name.lower().startswith("on") or "javascript:" in text.replace(" ", "").lower():
                return False
    return True


def test_ingest_body_keeps_article_markup_but_strips_scripts():
    raw = (
        '<h1>제목</h1><h2>소제목</h2><p class="note">본문 <strong>강조</strong></p>'
        '<figure><img src="%s" alt="그림" loading="lazy" width="600"/><figcaption>캡션</figcaption></figure>'
        '<table><thead><tr><th>a</th></tr></thead><tbody><tr><td>b</td></tr></tbody></table>'
        '<ul><li>항목</li></ul><div><span>span</span></div>'
        '<script>alert(1)</script><img src="x" onerror="alert(1)">'
        '<a href="javascript:alert(1)">링크</a><p onclick="x">클릭</p>'
    ) % DATA_IMG
    out = sanitize_ingest_html(raw)
    assert _no_handlers(out)
    for keep in ("<h1>", "<h2>", 'class="note"', "<figure>", "<figcaption>", "<table>", "<th>", "<td>", "<ul>", "<li>", "<div>", "<span>"):
        assert keep in out, keep
    assert DATA_IMG in out and 'alt="그림"' in out and 'width="600"' in out
    assert ">링크</a>" in out and 'href="javascript' not in out


def test_ingest_body_blocks_entity_and_cdata_bypasses():
    from bs4 import BeautifulSoup

    for raw in ("&lt;img src=x onerror=alert(1)&gt;", "<p><![CDATA[><img src=x onerror=alert(1)>]]></p>"):
        out = sanitize_ingest_html(raw)
        assert _no_handlers(out) and BeautifulSoup(out, "html.parser").find("img") is None, out


def test_key_visual_keeps_animated_svg():
    raw = (
        '<div class="key-visual"><svg viewBox="0 0 720 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="x">'
        '<defs><linearGradient id="g"><stop offset="0" stop-color="#fff"/></linearGradient></defs>'
        '<g><circle cx="10" cy="10" r="5" fill="url(#g)"><animate attributeName="r" values="5;8;5" dur="2s" repeatCount="indefinite"/></circle>'
        '<rect x="1" y="1" width="2" height="2" rx="1"/><path d="M0 0L1 1" stroke="#000" stroke-width="2"/>'
        '<text x="1" y="1" font-family="Pretendard" font-size="12">라벨</text><use href="#g"/></g></svg></div>'
    )
    out = sanitize_key_visual_html(raw)
    for keep in ("<svg", "<animate", 'attributename="r"', "<circle", "<lineargradient", 'fill="url(#g)"', "<text", 'href="#g"', 'viewbox="0 0 720 300"'):
        assert keep in out.lower(), keep


def test_key_visual_strips_script_vectors():
    raw = (
        '<div class="key-visual"><svg onload="alert(1)"><script>alert(1)</script>'
        '<a href="javascript:alert(1)"><text>x</text></a>'
        '<animate attributeName="href" values="javascript:alert(1)"/>'
        '<set attributeName="xlink:href" to="javascript:alert(1)"/>'
        '<use href="https://evil/x.svg#a"/><use xlink:href="javascript:alert(1)"/>'
        '<foreignObject><body onload="alert(1)"/></foreignObject>'
        '<style>@import url(https://evil); rect{fill:red}</style>'
        '<rect style="background:url(javascript:alert(1))"/>'
        '<image href="https://evil/a.png" onerror="alert(1)"/></svg></div>'
    )
    out = sanitize_key_visual_html(raw)
    low = out.lower()
    assert _no_handlers(out)
    assert "<foreignobject" not in low and "@import" not in low and "evil" not in low
    assert "<svg" in low and "<rect" in low


def test_key_visual_keeps_plain_image_variant():
    out = sanitize_key_visual_html('<div class="key-visual"><img src="%s" alt="k"/></div>' % DATA_IMG)
    assert DATA_IMG in out and _no_handlers(out)


def test_ingest_stores_sanitized_body_and_key_visual(db, tmp_path):
    seed_curation(db)
    (tmp_path / "20260707_가이드_주입.html").write_text(
        '<html><body><div class="key-visual"><svg onload="alert(1)"><circle r="1"/></svg></div>'
        '<article><h1>주입</h1><p>본문</p><img src="x" onerror="alert(1)"></article></body></html>',
        encoding="utf-8",
    )
    scan_contents_dir(db, make_cache(), str(tmp_path), media_dir=str(tmp_path / "media"))
    from app.models import Article

    article = db.query(Article).one()
    assert _no_handlers(article.body_html) and "<p>본문</p>" in article.body_html
    assert _no_handlers(article.key_visual_html) and "<circle" in article.key_visual_html


def test_migration_015_backfill_only_links_admins_older_than_the_article():
    sql = (Path(__file__).resolve().parents[2] / "backend/migrations/015_articles_author_member_id.sql").read_text(encoding="utf-8")
    assert "author_member_id" in sql and "ADD COLUMN IF NOT EXISTS" in sql
    assert "UPDATE articles" in sql  # 기존 authored 글 백필
    # 옛 닉네임을 선점한 계정에게 소유권이 넘어가지 않도록: 어드민이고 글보다 먼저 가입한 회원만
    assert "m.access_role = 'admin'" in sql and "m.created_at <= a.created_at" in sql


# --- 2차 리뷰: 키비주얼 CSS 주입(페이지 전체 디페이스·피싱 오버레이·비콘) 차단 ---

def test_key_visual_style_only_inside_svg_and_no_css_escapes():
    from bs4 import BeautifulSoup

    gone = (
        "<div><style>body{display:none}</style></div>",
        "<svg><style>body{background:\\75 rl(https://evil.example/x)}</style></svg>",
        '<svg><style>@\\69mport "https://evil.example/x.css";</style></svg>',
        '<svg><style>body{background-image:image-set("https://evil.example/x.png" 1x)}</style></svg>',
        '<svg><style>@font-face{src:url(https://evil)}</style></svg>',
    )
    for raw in gone:
        out = sanitize_key_visual_html(raw) or ""
        assert "<style" not in out.lower(), raw
    out = sanitize_key_visual_html("<svg><style>rect{fill:#f00} .a{animation:spin 2s}</style><rect/></svg>")
    assert "<style" in out.lower()  # svg 안의 평범한 CSS 는 유지

    out = sanitize_key_visual_html('<div style="position:fixed;inset:0;z-index:99999;background:white">x</div>'
                                   '<div style="background:u\\rl(https://evil.example/t)">y</div>'
                                   '<div style="color:red">z</div>')
    soup = BeautifulSoup(out, "html.parser")
    styles = [d.get("style") for d in soup.find_all("div")]
    assert styles == [None, None, "color:red"]


def test_key_visual_blocks_style_animation_and_external_url_refs():
    from bs4 import BeautifulSoup

    out = sanitize_key_visual_html(
        '<svg><animate attributeName="style" to="background:url(https://evil)"/>'
        '<set attributeName="x" to="java&#9;script:alert(1)"/>'
        '<animate attributeName="x:href" values="javascript:alert(1)"/>'
        '<rect fill="url(https://evil.example/x.svg#a)" filter="url(https://evil.example/f.svg#f)" stroke="url(#g)"/></svg>'
    )
    soup = BeautifulSoup(out, "html.parser")
    assert not [t for t in soup.find_all(["animate", "set"]) if (t.get("attributename") or "").endswith(("style", "href"))]
    assert all("javascript" not in str(t.attrs).replace(" ", "").lower() for t in soup.find_all(True))
    rect = soup.find("rect")
    assert rect.get("fill") is None and rect.get("filter") is None and rect.get("stroke") == "url(#g)"
    assert "evil" not in out


def test_resanitize_existing_articles(db, _isolated_media):
    """이번 수정 이전에 저장된 글(인제스트는 파일명 중복으로 재처리되지 않음)을 제자리에서 정화한다."""
    from datetime import datetime, timezone

    from app.models import Category
    from app.repositories.articles import create_article
    from app.services.content_sanitize import resanitize_stored_articles

    cat = Category(slug="curation", name="큐레이션", display_order=1)
    db.add(cat)
    db.commit()
    bad = create_article(
        db, category_id=cat.id, article_type="guide", title="old", source_type="internal",
        body_html='<p>본문</p><img src="x" onerror="alert(1)">',
        key_visual_html='<svg onload="alert(1)"><circle r="1"/></svg>',
        published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    authored = create_article(
        db, category_id=cat.id, article_type="column", title="a", source_type="authored",
        body_html="<p>&lt;img src=x onerror=alert(1)&gt;</p><span>&lt;svg onload=alert(1)&gt;</span>",
        published_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
    )
    cache = make_cache()
    before = cache._version()
    result = resanitize_stored_articles(db, cache)
    assert result.checked == 2 and result.changed == 2
    db.refresh(bad)
    db.refresh(authored)
    assert _no_handlers(bad.body_html) and _no_handlers(bad.key_visual_html) and "<circle" in bad.key_visual_html
    assert _no_handlers(authored.body_html)
    assert cache._version() > before
    assert resanitize_stored_articles(db, cache).changed == 0
