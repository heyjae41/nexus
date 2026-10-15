"""이미 저장된 직접 작성(authored)·텔레그램(internal) 글의 요약을 현재 규칙으로 다시 만든다 (1회성 운영)."""
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.models import Article
from app.services.content_extract import body_summary, extract_content
from app.services.html_sanitize import plain_text
from app.services.summary import summarize


@dataclass(frozen=True)
class ResummarizeResult:
    checked: int
    changed: int


def _source_file_summary(contents_dir: Path, filename: str | None) -> str | None:
    if not filename:
        return None
    path = contents_dir / Path(filename).name
    if not path.is_file():
        return None
    return extract_content(path.read_text(encoding="utf-8")).summary


def _new_summary(article: Article, contents_dir: Path) -> str:
    if article.source_type == "internal":
        return (
            _source_file_summary(contents_dir, article.content_filename)
            or body_summary(article.body_html)
            or summarize(article.summary)
        )
    return summarize(article.summary or plain_text(article.body_html or "") or article.title)


def resummarize_stored_articles(
    db: Session, cache: VersionedCache, contents_dir: str | Path
) -> ResummarizeResult:
    """텔레그램 글은 원본 파일의 작가 요약(meta description)을 우선 쓰고, 없으면 본문 앞 문장으로 만든다."""
    folder = Path(contents_dir)
    stmt = select(Article).where(Article.source_type.in_(("internal", "authored")))
    checked = changed = 0
    for article in db.scalars(stmt):
        checked += 1
        summary = _new_summary(article, folder) or None
        if summary == article.summary:
            continue
        article.summary = summary
        changed += 1
    if changed:
        db.commit()
        cache.bump_version()
    return ResummarizeResult(checked=checked, changed=changed)
