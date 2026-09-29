"""직접 작성 글 HTML 정화."""
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
