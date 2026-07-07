"""텔레그램 글 생성 도구(article_builder) 테스트.

hermes agent 스킬이 사용하는 핵심 로직:
- 파일명 규칙 '날짜_글유형_제목.html' 생성 (제목 띄어쓰기 제거)
- 인제스트와 왕복 호환되는 완전한 HTML 렌더링 (키비주얼 필수)
- 4분 분량 읽기 시간 추정
"""
from datetime import date

import pytest

from app.services.article_builder import (
    build_filename,
    estimate_read_minutes,
    render_article_html,
)
from app.services.content_extract import extract_content
from app.services.ingest_parser import parse_content_filename


def test_build_filename_strips_spaces_and_maps_type():
    name = build_filename(date(2026, 7, 7), "newsletter", "AI가 바꾸는 결제의 미래")
    assert name == "20260707_뉴스레터_AI가바꾸는결제의미래.html"


@pytest.mark.parametrize(
    "code,korean", [("newsletter", "뉴스레터"), ("column", "컬럼"), ("guide", "가이드")]
)
def test_build_filename_all_types(code, korean):
    assert f"_{korean}_" in build_filename(date(2026, 1, 2), code, "제목")


def test_build_filename_removes_unsafe_chars():
    name = build_filename(date(2026, 7, 7), "guide", 'RAG vs 파인튜닝: 뭐가/맞을까?')
    parsed = parse_content_filename(name)
    assert parsed.title == "RAGvs파인튜닝뭐가맞을까"


def test_build_filename_rejects_unknown_type():
    with pytest.raises(ValueError):
        build_filename(date(2026, 7, 7), "essay", "제목")


def test_render_article_html_roundtrips_with_ingest():
    html = render_article_html(
        title="AI가 바꾸는 결제의 미래",
        summary="요약입니다",
        author="김넥서스",
        body_html="<p>첫 문단</p><p>둘째 문단</p>",
        key_visual_html='<svg viewBox="0 0 10 10"><circle r="4"/></svg>',
        read_minutes=4,
    )
    content = extract_content(html)
    assert content.title == "AI가 바꾸는 결제의 미래"
    assert content.author == "김넥서스"
    assert content.read_minutes == 4
    assert "svg" in content.key_visual_html
    assert "첫 문단" in content.body_html
    # 키비주얼은 본문에서 분리되어야 한다
    assert "circle" not in content.body_html


def test_render_article_html_requires_key_visual():
    with pytest.raises(ValueError):
        render_article_html(
            title="t", summary="s", author="a",
            body_html="<p>b</p>", key_visual_html="", read_minutes=4,
        )


def test_estimate_read_minutes_targets_4min_for_2000_chars():
    text = "가" * 2000
    assert estimate_read_minutes(text) == 4


def test_estimate_read_minutes_clamps():
    assert estimate_read_minutes("짧다") == 1
    assert estimate_read_minutes("가" * 100000) == 10
