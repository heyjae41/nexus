"""작가 화이트리스트 — 문서 루트 .writer_whitelist 의 텔레그램 userid 만 허용.

파일 형식: 한 줄당 숫자 userid 하나. '#' 주석과 빈 줄 허용.
파일이 없거나 비어 있으면 아무도 허용하지 않는다 (fail-closed).
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_WHITELIST_PATH = ".writer_whitelist"


def load_whitelist(path: str = DEFAULT_WHITELIST_PATH) -> set[int]:
    file = Path(path)
    if not file.is_file():
        logger.warning("화이트리스트 파일이 없습니다: %s (전원 차단)", path)
        return set()
    ids: set[int] = set()
    for line in file.read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if not entry:
            continue
        if entry.isdecimal():  # isdigit() 는 int() 변환 불가한 유니코드 숫자를 통과시킨다
            ids.add(int(entry))
        else:
            logger.warning("화이트리스트에 잘못된 항목 무시: %r", entry)
    return ids


def is_allowed_writer(telegram_user_id, path: str = DEFAULT_WHITELIST_PATH) -> bool:
    try:
        user_id = int(str(telegram_user_id).strip())
    except (TypeError, ValueError):
        return False
    return user_id in load_whitelist(path)
