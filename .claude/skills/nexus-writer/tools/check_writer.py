#!/usr/bin/env python3
"""작가 권한 확인 도구 — 화이트리스트에 등록된 텔레그램 userid 인지 검사한다.

사용법: python check_writer.py [<telegram_user_id>]
출력: ALLOWED 또는 DENIED (exit code 0 / 1)

호스트(hermes)가 넣는 NEXUS_TELEGRAM_USER_ID 가 있으면 그 값만 믿는다 — 인자는 같을 때만
허용하고, 환경변수가 비어 있으면 거부한다. 환경변수가 없을 때만 인자를 쓴다.
"""
import sys

from _bootstrap import PROJECT_ROOT  # noqa: E402,F401 — app.* import 경로 설정

from app.services.writer_identity import resolve_writer_id  # noqa: E402
from app.services.writer_whitelist import is_allowed_writer  # noqa: E402


def main(argv: list[str] | None = None, *, whitelist_path: str | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) > 1:
        print("사용법: python check_writer.py [<telegram_user_id>]", file=sys.stderr)
        return 2
    user_id = resolve_writer_id(argv[0] if argv else None)
    whitelist = whitelist_path or str(PROJECT_ROOT / ".writer_whitelist")
    if user_id and is_allowed_writer(user_id, whitelist):
        print("ALLOWED")
        return 0
    print("DENIED: 화이트리스트에 등록되지 않은 사용자입니다")
    return 1


if __name__ == "__main__":
    sys.exit(main())
