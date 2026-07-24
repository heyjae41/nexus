"""key-visual 대표 이미지 → 목록 카드 썸네일 파일 추출.

인제스트 글의 대표 이미지는 key_visual_html 안에 base64 data-URI(<img>) 또는
인라인 <svg> 로만 존재해, 목록/홈 카드(thumbnail_url)에는 노출되지 않는다.
save_key_visual_thumbnail 이 그 이미지를 media_dir 아래 정적 파일로 저장하고
공개 URL(/api/media/...)을 돌려준다.
"""
import base64

from app.services.thumbnails import save_key_visual_thumbnail

# 1x1 투명 PNG
_PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


def test_extracts_base64_img_to_file(tmp_path):
    kv = f'<div class="key-visual"><img alt="x" src="data:image/png;base64,{_PNG}"></div>'

    url = save_key_visual_thumbnail(kv, str(tmp_path))

    assert url is not None
    assert url.startswith("/api/media/thumbnails/")
    assert url.endswith(".png")
    saved = tmp_path / url.removeprefix("/api/media/")
    assert saved.is_file()
    assert saved.read_bytes() == base64.b64decode(_PNG)


def test_extracts_inline_svg_to_file(tmp_path):
    kv = '<div class="key-visual"><svg viewBox="0 0 10 10"><circle r="5"/></svg></div>'

    url = save_key_visual_thumbnail(kv, str(tmp_path))

    assert url is not None
    assert url.endswith(".svg")
    saved = tmp_path / url.removeprefix("/api/media/")
    content = saved.read_text(encoding="utf-8")
    # 독립 파일로 렌더되려면 xmlns 가 있어야 한다
    assert "<svg" in content and "xmlns" in content


def test_none_when_no_image(tmp_path):
    assert save_key_visual_thumbnail('<div class="key-visual"></div>', str(tmp_path)) is None
    assert save_key_visual_thumbnail(None, str(tmp_path)) is None
    assert save_key_visual_thumbnail("", str(tmp_path)) is None


def test_external_url_img_is_used_as_is(tmp_path):
    # data-URI 가 아닌 외부 URL 이미지는 저장하지 않고 URL 을 그대로 쓴다
    kv = '<div class="key-visual"><img src="https://ex.com/a.jpg"></div>'
    assert save_key_visual_thumbnail(kv, str(tmp_path)) == "https://ex.com/a.jpg"


def test_same_image_is_deduplicated(tmp_path):
    kv = f'<div class="key-visual"><img src="data:image/png;base64,{_PNG}"></div>'

    u1 = save_key_visual_thumbnail(kv, str(tmp_path))
    u2 = save_key_visual_thumbnail(kv, str(tmp_path))

    assert u1 == u2
    files = list((tmp_path / "thumbnails").iterdir())
    assert len(files) == 1  # 동일 내용은 한 파일로만 저장(내용 해시 파일명)


def test_corrupt_base64_returns_none(tmp_path):
    kv = '<div class="key-visual"><img src="data:image/png;base64,@@@not-base64@@@"></div>'
    assert save_key_visual_thumbnail(kv, str(tmp_path)) is None


def test_blank_img_src_returns_none(tmp_path):
    # 공백뿐인 src 는 빈 문자열 URL 을 저장하면 안 된다 (카드가 <img src=""> 재요청)
    kv = '<div class="key-visual"><img src="   "></div>'
    assert save_key_visual_thumbnail(kv, str(tmp_path)) is None


def test_svg_script_and_handlers_are_stripped(tmp_path):
    kv = (
        '<div class="key-visual"><svg viewBox="0 0 10 10" onload="alert(1)">'
        '<script>alert(2)</script><rect onclick="evil()"/>'
        '<a xlink:href="javascript:evil()">x</a></svg></div>'
    )
    url = save_key_visual_thumbnail(kv, str(tmp_path))
    assert url is not None and url.endswith(".svg")
    content = (tmp_path / url.removeprefix("/api/media/")).read_text(encoding="utf-8")
    assert "<script" not in content.lower()
    assert "onload" not in content.lower()
    assert "onclick" not in content.lower()
    assert "javascript:" not in content.lower()


def test_oversized_image_returns_none(tmp_path, monkeypatch):
    import app.services.thumbnails as th

    monkeypatch.setattr(th, "MAX_THUMBNAIL_BYTES", 8)
    kv = f'<div class="key-visual"><img src="data:image/png;base64,{_PNG}"></div>'
    assert save_key_visual_thumbnail(kv, str(tmp_path)) is None
