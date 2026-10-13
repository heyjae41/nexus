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
  published_date(yyyy-mm-dd, 생략 시 오늘, 과거 30일~내일), read_minutes(1~10, 생략 시 본문 기준 자동)
같은 파일명이 이미 있으면 덮어쓰지 않고 오류로 끝난다.

출력: 저장된 파일 경로 (stdout)
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from _bootstrap import PROJECT_ROOT  # noqa: E402,F401 — app.* import 경로 설정

from app.services.article_builder import (  # noqa: E402
    MAX_MINUTES,
    build_filename,
    estimate_read_minutes,
    render_article_html,
)
from app.services.ingest import ingest_now  # noqa: E402
from app.services.writer_identity import resolve_writer_id  # noqa: E402
from app.services.writer_whitelist import is_allowed_writer  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

REQUIRED = ("title", "article_type", "summary", "author", "body_html", "key_visual_html")
# 발행일은 오늘 기준 과거 30일 ~ 내일까지만 — 임의 백데이트/미래 날짜로 정렬·상단 고정을 조작하지 못하게
PUBLISHED_PAST_DAYS = 30
PUBLISHED_FUTURE_DAYS = 1
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _clean_text(value) -> str:
    return _CONTROL_RE.sub("", str(value)).strip()


def _published_date(raw) -> date:
    if not raw:
        return date.today()
    try:
        published = date.fromisoformat(str(raw))
    except ValueError as exc:
        raise ValueError(f"published_date 는 yyyy-mm-dd 형식이어야 합니다: {raw}") from exc
    today = date.today()
    if not (today - timedelta(days=PUBLISHED_PAST_DAYS) <= published <= today + timedelta(days=PUBLISHED_FUTURE_DAYS)):
        raise ValueError(
            f"published_date 는 오늘 기준 {PUBLISHED_PAST_DAYS}일 전부터 {PUBLISHED_FUTURE_DAYS}일 후까지만 가능합니다: {raw}"
        )
    return published


def _read_minutes(raw, body_text: str) -> int:
    if raw in (None, ""):
        return estimate_read_minutes(body_text)
    try:
        minutes = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"read_minutes 는 정수여야 합니다: {raw}") from exc
    if minutes < 1:
        raise ValueError(f"read_minutes 는 1 이상이어야 합니다: {raw}")
    return min(minutes, MAX_MINUTES)


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
    user_id = resolve_writer_id(telegram_user_id) if telegram_user_id is not None else arg_user
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

    try:
        published = _published_date(payload.get("published_date"))
        body_text = BeautifulSoup(payload["body_html"], "html.parser").get_text(" ", strip=True)
        read_minutes = _read_minutes(payload.get("read_minutes"), body_text)
        filename = build_filename(published, payload["article_type"], _clean_text(payload["title"]))
        html = render_article_html(
            title=_clean_text(payload["title"]),
            summary=_clean_text(payload["summary"]),
            author=_clean_text(payload["author"]),
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
    try:
        # 같은 이름을 덮어쓰면 인제스트(파일명 dedup)가 갱신하지 않아 파일과 DB 가 어긋난다
        with target.open("x", encoding="utf-8") as fh:
            fh.write(html)
    except FileExistsError:
        print(f"오류: 이미 같은 이름의 글이 있습니다 - {target.name} (제목이나 날짜를 바꾸세요)", file=sys.stderr)
        return 1
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
