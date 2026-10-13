"""직접 작성 글 HTML 정화."""
import pytest
from app.services.html_sanitize import safe_href  # noqa: F401
from app.services.html_sanitize import sanitize_article_html


def test_strips_script_and_event_handlers():
    raw = '<p onclick="alert(1)">안녕</p><script>alert(1)</script>'
    clean = sanitize_article_html(raw)
    assert "안녕" in clean
    assert "script" not in clean.lower()
    assert "onclick" not in clean


def test_keeps_uploaded_image_and_drops_external_image():
    raw = (
        '<p>본문</p>'
        '<img src="/api/media/authored/a.png" alt="도표">'
        '<img src="https://evil.example/x.png" alt="외부">'
    )
    clean = sanitize_article_html(raw)
    assert 'src="/api/media/authored/a.png"' in clean
    assert "evil.example" not in clean


def test_drops_javascript_links():
    clean = sanitize_article_html('<a href="javascript:alert(1)">클릭</a>')
    assert "javascript" not in clean.lower()
    assert "클릭" in clean


def test_keeps_absolute_media_url_as_site_path():
    clean = sanitize_article_html(
        '<img src="https://edu.dev.bccard.ai/api/media/authored/a.png" alt="도표">'
    )
    assert 'src="/api/media/authored/a.png"' in clean
    assert "edu.dev.bccard.ai" not in clean


# --- 보안 점검(2026-10) 회귀: 새니타이저 우회 2종 ---

def _has_live_handler(html: str) -> bool:
    """이스케이프된 텍스트가 아니라 실제 태그/속성으로 살아 있는지 본다."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    if soup.find(["script", "img", "svg"]):
        return True
    return any(a.lower().startswith("on") for t in soup.find_all(True) for a in t.attrs)


def test_top_level_entities_stay_escaped():
    """출력 조립 시 최상위 텍스트의 이스케이프가 풀려 &lt;img onerror&gt; 가 살아났던 버그."""
    out = sanitize_article_html("&lt;img src=x onerror=alert(1)&gt;")
    assert not _has_live_handler(out)
    assert "&lt;img" in out


def test_text_inside_unwrapped_tag_stays_escaped():
    out = sanitize_article_html("<span>&lt;img src=x onerror=alert(1)&gt;</span>")
    assert not _has_live_handler(out)
    out = sanitize_article_html("<div><p>ok</p>&lt;svg onload=alert(1)&gt;</div>")
    assert "<p>ok</p>" in out and not _has_live_handler(out)


def test_cdata_sections_are_removed_top_level_and_nested():
    for raw in (
        "<![CDATA[><img src=x onerror=alert(1)>]]>",
        "<p><![CDATA[><img src=x onerror=alert(1)>]]></p>",
        "<p>a</p><![CDATA[ x ><svg onload=alert(1)>]]>",
    ):
        out = sanitize_article_html(raw)
        assert "CDATA" not in out and not _has_live_handler(out), out


@pytest.mark.filterwarnings("ignore::bs4.XMLParsedAsHTMLWarning")
def test_declarations_and_processing_instructions_are_removed():
    out = sanitize_article_html("<!DOCTYPE html><?xml version='1.0'?><!x><p>ok</p>")
    assert out == "<p>ok</p>"


# --- 보안 LOW: "//evil.com", "/\\evil.com" 은 같은 탭에서 외부로 빠져나간다 ---

def test_protocol_relative_and_backslash_links_are_dropped():
    for href in ("//evil.com/x", "/\\evil.com", "/\\\\evil.com"):
        assert safe_href(href) is None, href
    assert safe_href("/articles/1") == "/articles/1"


def test_links_with_embedded_tab_or_newline_are_dropped():
    """브라우저는 URL 안의 탭·개행을 지우므로 "/\t/evil.com" 은 "//evil.com" 이 된다."""
    for href in ("/\t/evil.com", "/\n\\evil.com", "/\r/evil.com", "ja\tvascript:alert(1)"):
        assert safe_href(href) is None, repr(href)
