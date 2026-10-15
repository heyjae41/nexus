"""요약 규칙 — 상세 화면 제목 아래 5줄(약 150자) 안에 들어가도록 앞 문장을 고른다.

LLM 없이 규칙으로 만든다: 문장 단위로 150자까지 담고, 첫 문장부터 넘치면 단어 경계에서 자른다."""
from datetime import datetime, timezone

from app.models import Category
from app.repositories.articles import create_article
from app.services.article_builder import render_article_html
from app.services.content_extract import extract_content
from app.services.summary import SUMMARY_MAX, summarize
from app.services.summary_backfill import resummarize_stored_articles
from shared import make_cache

SENTENCE = "오픈AI가 차세대 모델을 공개하며 에이전트 기능을 대폭 강화했다."  # 35자


def test_short_text_is_kept_with_whitespace_normalized():
    assert summarize("  첫 문장입니다.\n\n 둘째   문장. ") == "첫 문장입니다. 둘째 문장."
    assert summarize("") == "" and summarize(None) == ""


def test_keeps_whole_sentences_within_limit():
    text = " ".join([SENTENCE] * 10)
    out = summarize(text)
    assert len(out) <= SUMMARY_MAX
    assert out.endswith("강화했다.")
    assert out == " ".join([SENTENCE] * 4)


def test_decimal_point_is_not_a_sentence_end():
    text = "GPT-6.1 모델이 공개됐다. " + "가" * 200
    assert summarize(text) == "GPT-6.1 모델이 공개됐다."


def test_overlong_first_sentence_is_cut_at_word_boundary():
    text = " ".join(["단어열"] * 80) + "."
    out = summarize(text)
    assert len(out) <= SUMMARY_MAX
    assert out.endswith("단어열…")


def test_ingest_uses_meta_description_as_summary():
    html = render_article_html(
        title="제목", summary="작가가 쓴 요약입니다.", author="김넥서스",
        body_html="<p>" + SENTENCE * 20 + "</p>",
        key_visual_html='<svg viewBox="0 0 10 10"><circle r="4"/></svg>', read_minutes=4,
    )
    assert extract_content(html).summary == "작가가 쓴 요약입니다."


def test_ingest_without_description_summarizes_body_without_title():
    html = (
        "<html><head><title>t</title></head><body><article><h1>긴 제목입니다</h1>"
        f"<p>{SENTENCE}</p><p>{SENTENCE}</p></article></body></html>"
    )
    summary = extract_content(html).summary
    assert not summary.startswith("긴 제목") and summary.startswith("오픈AI가")
    assert len(summary) <= SUMMARY_MAX


def _article(db, cat, **kwargs):
    return create_article(
        db, category_id=cat.id, article_type="guide",
        published_at=datetime(2026, 9, 1, tzinfo=timezone.utc), **kwargs,
    )


def test_resummarize_shortens_own_articles_only(db, tmp_path):
    cat = Category(slug="curation", name="큐레이션", display_order=1)
    db.add(cat)
    db.commit()
    long_summary = " ".join([SENTENCE] * 12)
    authored = _article(db, cat, title="a", source_type="authored", summary=long_summary,
                        body_html=f"<p>{long_summary}</p>")
    (tmp_path / "20260901_가이드_글.html").write_text(render_article_html(
        title="글", summary="파일의 작가 요약.", author="a", body_html=f"<p>{long_summary}</p>",
        key_visual_html='<svg viewBox="0 0 1 1"></svg>', read_minutes=4,
    ), encoding="utf-8")
    from_file = _article(db, cat, title="글", source_type="internal", summary=long_summary,
                         body_html=f"<h1>글</h1><p>{long_summary}</p>",
                         content_filename="20260901_가이드_글.html")
    no_file = _article(db, cat, title="옛글", source_type="internal", summary=long_summary,
                       body_html=f"<h1>옛글</h1><p>{long_summary}</p>",
                       content_filename="20250101_가이드_없음.html")
    collected = _article(db, cat, title="b", source_type="brunch", summary=long_summary)
    cache = make_cache()
    before = cache._version()

    result = resummarize_stored_articles(db, cache, tmp_path)

    assert (result.checked, result.changed) == (3, 3)
    for row in (authored, from_file, no_file, collected):
        db.refresh(row)
    assert authored.summary == " ".join([SENTENCE] * 4)
    assert from_file.summary == "파일의 작가 요약."
    assert no_file.summary == " ".join([SENTENCE] * 4)
    assert collected.summary == long_summary
    assert cache._version() > before
    assert resummarize_stored_articles(db, cache, tmp_path).changed == 0
