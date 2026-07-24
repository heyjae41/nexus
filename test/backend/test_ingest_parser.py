"""인제스트 파일명 파싱 테스트.

명명규칙: '날짜_글유형_제목.html'
- 날짜: yyyymmdd
- 글유형: 뉴스레터 | 컬럼 | 가이드
- 제목: 띄어쓰기 없이 붙여쓴 글 제목
"""
from datetime import date

import pytest

from app.services.ingest_parser import ParsedContentFile, parse_content_filename


def test_parse_valid_newsletter():
    p = parse_content_filename("20260707_뉴스레터_AI가바꾸는결제의미래.html")
    assert isinstance(p, ParsedContentFile)
    assert p.published_date == date(2026, 7, 7)
    assert p.article_type == "newsletter"
    assert p.title == "AI가바꾸는결제의미래"


@pytest.mark.parametrize(
    "korean,expected",
    [("뉴스레터", "newsletter"), ("컬럼", "column"), ("가이드", "guide")],
)
def test_parse_all_types(korean, expected):
    p = parse_content_filename(f"20260101_{korean}_제목.html")
    assert p.article_type == expected


@pytest.mark.parametrize(
    "bad",
    [
        "20260707_뉴스레터_제목.txt",          # 확장자 오류
        "2026-07-07_뉴스레터_제목.html",       # 날짜 형식 오류
        "20260707_기타_제목.html",             # 허용되지 않은 유형
        "20260707_뉴스레터.html",              # 제목 누락
        "20261399_뉴스레터_제목.html",         # 존재하지 않는 날짜
        "메모.html",
    ],
)
def test_parse_invalid_raises(bad):
    with pytest.raises(ValueError):
        parse_content_filename(bad)


def test_parse_nfd_decomposed_filename():
    """NFD(분해형) 파일명도 글유형을 인식하고 제목을 NFC 로 돌려준다."""
    import unicodedata

    nfd = unicodedata.normalize("NFD", "20260724_가이드_맛집탐색.html")
    parsed = parse_content_filename(nfd)
    assert parsed.article_type == "guide"
    assert parsed.title == "맛집탐색"  # NFC


def test_parse_title_keeps_underscores_in_title():
    # 제목에 _가 포함되어도 앞 두 조각(날짜, 유형) 이후 전체를 제목으로 취급
    p = parse_content_filename("20260707_가이드_프롬프트_엔지니어링_입문.html")
    assert p.title == "프롬프트_엔지니어링_입문"
