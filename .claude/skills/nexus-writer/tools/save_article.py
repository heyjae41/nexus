#!/usr/bin/env python3
"""글 저장 도구 — JSON 입력을 받아 /contents 에 명명규칙에 맞는 HTML 로 저장한다.

사용법:
  python save_article.py article.json --user <telegram_user_id>   # 파일 입력
  echo '{...}' | python save_article.py - --user <telegram_user_id>  # stdin 입력
  (NEXUS_TELEGRAM_USER_ID 환경변수가 있으면 --user 대신 그 값을 쓴다)

작가 화이트리스트(.writer_whitelist)에 없는 사용자는 DENIED 를 출력하고 아무것도 쓰지 않는다.
스킬 지시문이 0단계를 건너뛰어도 도구가 스스로 막는다 (불변식 4, fail-closed).

입력 JSON 필드:
  title(필수), article_type(newsletter|column|guide, 필수),
  summary(필수), author(필수), body_html(필수), key_visual_html(필수),
  published_date(yyyy-mm-dd, 생략 시 오늘), read_minutes(생략 시 본문 기준 자동)

출력: 저장된 파일 경로 (stdout)
"""
import json
import sys
from datetime import date
from pathlib import Path

from _bootstrap import PROJECT_ROOT  # noqa: E402,F401 — app.* import 경로 설정

from app.services.article_builder import (  # noqa: E402
    build_filename,
    estimate_read_minutes,
    render_article_html,
)
from app.services.ingest import ingest_now  # noqa: E402
from app.services.writer_identity import resolve_writer_id  # noqa: E402
from app.services.writer_whitelist import is_allowed_writer  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

REQUIRED = ("title", "article_type", "summary", "author", "body_html", "key_visual_html")


def _parse_args(argv: list[str]) -> tuple[str, str | None]:
    """(입력 경로, 사용자 id). id 출처 규칙은 writer_identity.resolve_writer_id (모든 작가 도구 공통)."""
    source, user = "-", None
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item == "--user" and rest:
            user = rest.pop(0)
        else:
            source = item
    return source, resolve_writer_id(user)


def main(
    argv: list[str] | None = None,
    *,
    telegram_user_id: str | None = None,
    whitelist_path: str | None = None,
    contents_dir: Path | None = None,
) -> int:
    source, arg_user = _parse_args(sys.argv[1:] if argv is None else argv)
    user_id = telegram_user_id if telegram_user_id is not None else arg_user
    whitelist = whitelist_path or str(PROJECT_ROOT / ".writer_whitelist")
    if not user_id or not is_allowed_writer(user_id, whitelist):
        print("DENIED: 화이트리스트에 등록되지 않은 사용자입니다 (저장하지 않음)")
        return 1

    raw = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"오류: JSON 파싱 실패 - {exc}", file=sys.stderr)
        return 1

    missing = [f for f in REQUIRED if not str(payload.get(f, "")).strip()]
    if missing:
        print(f"오류: 필수 필드 누락 - {', '.join(missing)}", file=sys.stderr)
        return 1

    published = (
        date.fromisoformat(payload["published_date"])
        if payload.get("published_date")
        else date.today()
    )
    body_text = BeautifulSoup(payload["body_html"], "html.parser").get_text(" ", strip=True)
    read_minutes = int(payload.get("read_minutes") or estimate_read_minutes(body_text))

    try:
        filename = build_filename(published, payload["article_type"], payload["title"])
        html = render_article_html(
            title=payload["title"],
            summary=payload["summary"],
            author=payload["author"],
            body_html=payload["body_html"],
            key_visual_html=payload["key_visual_html"],
            read_minutes=read_minutes,
        )
    except ValueError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    contents_dir = contents_dir or PROJECT_ROOT / "contents"
    contents_dir.mkdir(exist_ok=True)
    target = contents_dir / filename
    target.write_text(html, encoding="utf-8")
    print(str(target))

    # 저장 직후 즉시 반영 (best-effort) — 실패해도 1분 스케줄러가 안전망으로 처리
    result = ingest_now(str(contents_dir))
    if result is not None and result.ingested:
        print("즉시 반영 완료: 사이트에 바로 노출됩니다")
    else:
        print("즉시 반영 보류: 1분 내 스케줄러가 자동 반영합니다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
