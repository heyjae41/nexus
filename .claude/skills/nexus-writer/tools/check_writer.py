#!/usr/bin/env python3
"""작가 권한 확인 도구 — 화이트리스트에 등록된 텔레그램 userid 인지 검사한다.

사용법: python check_writer.py <telegram_user_id>
출력: ALLOWED 또는 DENIED (exit code 0 / 1)
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.writer_whitelist import is_allowed_writer  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("사용법: python check_writer.py <telegram_user_id>", file=sys.stderr)
        return 2
    whitelist_path = str(PROJECT_ROOT / ".writer_whitelist")
    if is_allowed_writer(sys.argv[1], whitelist_path):
        print("ALLOWED")
        return 0
    print("DENIED: 화이트리스트에 등록되지 않은 사용자입니다")
    return 1


if __name__ == "__main__":
    sys.exit(main())
