"""텔레그램 발행 글 빌더 — hermes agent 스킬(.claude/skills/nexus-writer)의 핵심 로직.

인제스트 파이프라인(ingest_parser / content_extract)과 왕복 호환되는
파일명과 HTML 을 생성한다.
"""
import html as html_escape
import re
from datetime import date

KOREAN_TYPE = {"newsletter": "뉴스레터", "column": "컬럼", "guide": "가이드"}
KOREAN_TO_CODE = {v: k for k, v in KOREAN_TYPE.items()}

# 파일명에서 제거할 문자: 공백 + 파일시스템/규칙상 위험 문자
UNSAFE_CHARS_RE = re.compile(r'[\s_/\\:*?"<>|.]+')

READ_CHARS_PER_MINUTE = 500
MIN_MINUTES, MAX_MINUTES = 1, 10


def build_filename(published: date, article_type: str, title: str) -> str:
    """'yyyymmdd_글유형_제목.html' — 제목은 띄어쓰기 없이 붙여쓴다."""
    korean = KOREAN_TYPE.get(KOREAN_TO_CODE.get(article_type, article_type))
    if korean is None:
        allowed = ", ".join(KOREAN_TYPE)
        raise ValueError(f"글유형은 [{allowed}] 중 하나여야 합니다: {article_type}")
    compact_title = UNSAFE_CHARS_RE.sub("", title)
    if not compact_title:
        raise ValueError("제목이 비어 있습니다")
    return f"{published.strftime('%Y%m%d')}_{korean}_{compact_title}.html"


def estimate_read_minutes(text: str) -> int:
    minutes = round(len(text) / READ_CHARS_PER_MINUTE)
    return max(MIN_MINUTES, min(MAX_MINUTES, minutes))


def render_article_html(
    *,
    title: str,
    summary: str,
    author: str,
    body_html: str,
    key_visual_html: str,
    read_minutes: int,
) -> str:
    """인제스트가 그대로 읽을 수 있는 완전한 글 HTML 을 렌더링한다."""
    if not key_visual_html.strip():
        raise ValueError("키비주얼(key_visual_html)은 필수입니다 — 개념 애니메이션을 포함하세요")
    if not body_html.strip():
        raise ValueError("본문(body_html)이 비어 있습니다")
    escaped_title = html_escape.escape(title)
    escaped_author = html_escape.escape(author)
    escaped_summary = html_escape.escape(summary)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="author" content="{escaped_author}">
<meta name="read-minutes" content="{read_minutes}">
<meta name="description" content="{escaped_summary}">
<title>{escaped_title}</title>
</head>
<body>
<article>
  <div class="key-visual">{key_visual_html}</div>
  <h1>{escaped_title}</h1>
  {body_html}
</article>
</body>
</html>
"""
