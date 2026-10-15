"""글 요약 규칙 — 상세 화면 제목 아래 5줄(데스크톱 약 180자, 모바일 약 120자) 안에 들도록 자른다."""
import re

SUMMARY_MAX = 150

# 소수점("6.1")은 문장 끝이 아니다 — 마침표 뒤에 공백이나 끝이 와야 한다.
_SENTENCE = re.compile(r"\S.*?(?:[.!?。]+[\"'”’)\]]*(?=\s|$)|$)")


def summarize(text: str | None, limit: int = SUMMARY_MAX) -> str:
    """앞에서부터 온전한 문장을 limit 자까지 담는다. 첫 문장부터 넘치면 단어 경계에서 자른다."""
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    picked = ""
    for sentence in _SENTENCE.findall(clean):
        candidate = f"{picked} {sentence}".strip()
        if len(candidate) > limit:
            break
        picked = candidate
    return picked or _cut(clean, limit)


def _cut(text: str, limit: int) -> str:
    head = text[: limit - 1]
    space = head.rfind(" ")
    if space >= limit // 2:
        head = head[:space]
    return head.rstrip(" ,·") + "…"
