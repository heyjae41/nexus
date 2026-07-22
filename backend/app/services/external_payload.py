"""외부 JSON 응답의 선택 필드 변환."""


def optional_text(item: dict, key: str) -> str | None:
    value = str(item.get(key) or "").strip()
    return value or None


def optional_integer(value, *, multiplier: int = 1) -> int | None:
    try:
        return int(value) * multiplier if value is not None else None
    except (TypeError, ValueError):
        return None
