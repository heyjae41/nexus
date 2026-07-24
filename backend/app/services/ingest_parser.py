"""인제스트 파일명 파서.

명명규칙: '날짜_글유형_제목.html' (예: 20260707_뉴스레터_AI가바꾸는결제의미래.html)
- 날짜: yyyymmdd
- 글유형: 뉴스레터 | 컬럼 | 가이드
- 제목: 붙여쓴 글 제목 (제목 내 '_' 허용)
"""
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime

TYPE_MAP = {"뉴스레터": "newsletter", "컬럼": "column", "가이드": "guide"}


@dataclass(frozen=True)
class ParsedContentFile:
    published_date: date
    article_type: str
    title: str


def parse_content_filename(filename: str) -> ParsedContentFile:
    # macOS 저장 파일은 NFD(분해형) 한글일 수 있다 — 글유형 비교 전에 NFC 로 정규화
    filename = unicodedata.normalize("NFC", filename)
    if not filename.endswith(".html"):
        raise ValueError(f"확장자는 .html 이어야 합니다: {filename}")
    stem = filename[: -len(".html")]
    parts = stem.split("_", 2)
    if len(parts) != 3:
        raise ValueError(f"'날짜_글유형_제목.html' 형식이 아닙니다: {filename}")
    date_part, type_part, title = parts
    try:
        published = datetime.strptime(date_part, "%Y%m%d").date()
    except ValueError as exc:
        raise ValueError(f"날짜는 yyyymmdd 형식이어야 합니다: {date_part}") from exc
    if type_part not in TYPE_MAP:
        allowed = ", ".join(TYPE_MAP)
        raise ValueError(f"글유형은 [{allowed}] 중 하나여야 합니다: {type_part}")
    if not title:
        raise ValueError(f"제목이 비어 있습니다: {filename}")
    return ParsedContentFile(
        published_date=published,
        article_type=TYPE_MAP[type_part],
        title=title,
    )
