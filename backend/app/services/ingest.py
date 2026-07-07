"""/contents 폴더 인제스트 서비스.

텔레그램(hermes agent)이 생성한 '날짜_글유형_제목.html' 파일을 읽어 DB 에 입력한다.
스케줄러가 1분 주기로 scan_contents_dir 를 호출한다.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.models import Article
from app.repositories.categories import get_category_by_slug
from app.services.content_extract import extract_content
from app.services.ingest_parser import parse_content_filename

logger = logging.getLogger(__name__)

INGEST_CATEGORY_SLUG = "curation"


@dataclass(frozen=True)
class IngestResult:
    ingested: int = 0
    already: int = 0
    skipped: int = 0


def _existing_filenames(db: Session, names: list[str]) -> set[str]:
    if not names:
        return set()
    stmt = select(Article.content_filename).where(Article.content_filename.in_(names))
    return set(db.scalars(stmt))


def scan_contents_dir(db: Session, cache: VersionedCache, contents_dir: str) -> IngestResult:
    """폴더의 신규 html 을 DB 에 입력하고, 입력이 있었으면 캐시를 무효화한다."""
    directory = Path(contents_dir)
    if not directory.is_dir():
        logger.warning("컨텐츠 폴더가 없습니다: %s", contents_dir)
        return IngestResult()

    files = sorted(p.name for p in directory.glob("*.html"))
    existing = _existing_filenames(db, files)
    ingested = already = skipped = 0

    for name in files:
        if name in existing:
            already += 1
            continue
        try:
            _ingest_file(db, directory / name)
            ingested += 1
        except ValueError as exc:
            skipped += 1
            logger.warning("인제스트 건너뜀 (%s): %s", name, exc)

    if ingested:
        cache.bump_version()
        logger.info("인제스트 %d건 완료 → 캐시 무효화", ingested)
    return IngestResult(ingested=ingested, already=already, skipped=skipped)


def _ingest_file(db: Session, path: Path) -> None:
    parsed = parse_content_filename(path.name)
    category = get_category_by_slug(db, INGEST_CATEGORY_SLUG)
    if category is None:
        raise ValueError(f"기본 카테고리({INGEST_CATEGORY_SLUG})가 없습니다")

    html = path.read_text(encoding="utf-8")
    content = extract_content(html)
    article = Article(
        category_id=category.id,
        article_type=parsed.article_type,
        title=content.title or parsed.title,
        summary=content.summary,
        body_html=content.body_html,
        key_visual_html=content.key_visual_html,
        author_name=content.author or "BC카드 AI사업팀",
        source_type="internal",
        content_filename=path.name,
        read_minutes=content.read_minutes or 4,
        published_at=datetime.combine(
            parsed.published_date, time(0, 0), tzinfo=timezone.utc
        ),
    )
    db.add(article)
    db.commit()
