"""작가별 대화 세션 저장소 (PostgreSQL 영속 — 서버 재기동에도 유지).

- 텔레그램 userid 기준으로 대화를 완전히 분리해 작가 간 맥락 혼재를 막는다.
- 대화가 길어지면(needs_compact) 오래된 메시지를 요약 한 줄로 압축해
  토큰 비용 증가를 차단한다. 최근 COMPACT_KEEP_RECENT 개는 원문 유지.
"""
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import WriterMessage, WriterSession

ALLOWED_ROLES = ("user", "assistant")

# 메시지 1건의 최대 길이 — 토큰 비용 폭주 방지 (SKILL.md 는 300자 요약을 권고)
MAX_CONTENT_CHARS = 2000

# 압축 정책: 메시지 수 또는 총 글자수가 임계치를 넘으면 압축을 권고한다.
COMPACT_AFTER_MESSAGES = 20
COMPACT_AFTER_CHARS = 8000
COMPACT_KEEP_RECENT = 4

# 안전 상한: 압축을 건너뛰어도 이 개수를 넘는 오래된 메시지는 조회에서 제외
HARD_MESSAGE_LIMIT = 200


@dataclass(frozen=True)
class SessionHistory:
    summary: str | None
    messages: list[WriterMessage]


@dataclass(frozen=True)
class SessionStatus:
    message_count: int
    total_chars: int
    has_summary: bool
    needs_compact: bool


def append_message(db: Session, telegram_user_id: int, role: str, content: str) -> None:
    if role not in ALLOWED_ROLES:
        allowed = ", ".join(ALLOWED_ROLES)
        raise ValueError(f"role 은 [{allowed}] 중 하나여야 합니다: {role}")
    if len(content) > MAX_CONTENT_CHARS:
        raise ValueError(
            f"메시지가 너무 깁니다 ({len(content)}자 > {MAX_CONTENT_CHARS}자) — 요약해서 저장하세요"
        )
    db.add(WriterMessage(telegram_user_id=telegram_user_id, role=role, content=content))
    db.commit()


def _get_session(db: Session, telegram_user_id: int) -> WriterSession | None:
    return db.get(WriterSession, telegram_user_id)


def get_history(db: Session, telegram_user_id: int) -> SessionHistory:
    session = _get_session(db, telegram_user_id)
    messages = list(
        db.scalars(
            select(WriterMessage)
            .where(WriterMessage.telegram_user_id == telegram_user_id)
            .order_by(WriterMessage.created_at.desc(), WriterMessage.id.desc())
            .limit(HARD_MESSAGE_LIMIT)
        )
    )[::-1]
    return SessionHistory(
        summary=session.summary if session else None,
        messages=messages,
    )


def session_status(db: Session, telegram_user_id: int) -> SessionStatus:
    count, chars = db.execute(
        select(
            func.count(WriterMessage.id),
            func.coalesce(func.sum(func.length(WriterMessage.content)), 0),
        ).where(WriterMessage.telegram_user_id == telegram_user_id)
    ).one()
    session = _get_session(db, telegram_user_id)
    return SessionStatus(
        message_count=count,
        total_chars=chars,
        has_summary=bool(session and session.summary),
        needs_compact=count > COMPACT_AFTER_MESSAGES or chars > COMPACT_AFTER_CHARS,
    )


def compact_session(db: Session, telegram_user_id: int, summary: str) -> None:
    """오래된 메시지를 요약으로 대체한다 (최근 COMPACT_KEEP_RECENT 개 유지)."""
    keep_ids = list(
        db.scalars(
            select(WriterMessage.id)
            .where(WriterMessage.telegram_user_id == telegram_user_id)
            .order_by(WriterMessage.created_at.desc(), WriterMessage.id.desc())
            .limit(COMPACT_KEEP_RECENT)
        )
    )
    # 경쟁 조건 가드: keep_ids 조회 이후 커밋된 새 메시지(id 가 더 큼)는
    # id < min(keep_ids) 조건 덕분에 어떤 경우에도 삭제되지 않는다.
    min_keep = min(keep_ids) if keep_ids else 0
    db.execute(
        delete(WriterMessage).where(
            WriterMessage.telegram_user_id == telegram_user_id,
            WriterMessage.id.not_in(keep_ids),
            WriterMessage.id < min_keep,
        )
    )
    session = _get_session(db, telegram_user_id)
    if session is None:
        session = WriterSession(telegram_user_id=telegram_user_id)
        db.add(session)
    session.summary = summary
    db.commit()


def clear_session(db: Session, telegram_user_id: int) -> None:
    db.execute(
        delete(WriterMessage).where(WriterMessage.telegram_user_id == telegram_user_id)
    )
    db.execute(
        delete(WriterSession).where(WriterSession.telegram_user_id == telegram_user_id)
    )
    db.commit()
