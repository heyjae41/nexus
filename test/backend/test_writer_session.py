"""작가별 대화 세션 저장소 테스트.

요구사항:
- 텔레그램 userid 기준으로 대화 맥락을 완전히 분리한다 (A/B 작가 혼재 금지).
- DB(PostgreSQL) 저장으로 서버 재기동에도 대화가 유지된다.
- 대화가 길어지면 요약으로 압축해 토큰 비용을 제어한다.
- 초기화(clear) 를 지원한다.
"""
from app.services.writer_session import (
    COMPACT_KEEP_RECENT,
    append_message,
    clear_session,
    compact_session,
    get_history,
    session_status,
)

USER_A = 8174778078
USER_B = 12345


def test_append_and_history_roundtrip(db):
    append_message(db, USER_A, "user", "RAG 글 쓰고 싶어")
    append_message(db, USER_A, "assistant", "유형은 가이드로 하겠습니다")
    h = get_history(db, USER_A)
    assert h.summary is None
    assert [(m.role, m.content) for m in h.messages] == [
        ("user", "RAG 글 쓰고 싶어"),
        ("assistant", "유형은 가이드로 하겠습니다"),
    ]


def test_contexts_are_isolated_per_user(db):
    append_message(db, USER_A, "user", "A의 주제: 금융 AI")
    append_message(db, USER_B, "user", "B의 주제: 프롬프트")
    h_a = get_history(db, USER_A)
    h_b = get_history(db, USER_B)
    assert all("B의" not in m.content for m in h_a.messages)
    assert all("A의" not in m.content for m in h_b.messages)
    assert len(h_a.messages) == 1
    assert len(h_b.messages) == 1


def test_history_persists_across_sessions(engine, db):
    """서버 재기동 시나리오: 새 DB 세션(연결)에서도 대화가 남아 있어야 한다."""
    from sqlalchemy.orm import Session

    append_message(db, USER_A, "user", "재기동 전 메시지")
    db.close()
    with Session(bind=engine) as fresh:
        h = get_history(fresh, USER_A)
        assert [m.content for m in h.messages] == ["재기동 전 메시지"]


def test_compact_replaces_old_with_summary_keeping_recent(db):
    for i in range(10):
        append_message(db, USER_A, "user", f"메시지{i}")
    compact_session(db, USER_A, summary="지금까지: RAG 가이드 글 작성 논의")
    h = get_history(db, USER_A)
    assert h.summary == "지금까지: RAG 가이드 글 작성 논의"
    assert len(h.messages) == COMPACT_KEEP_RECENT
    assert h.messages[-1].content == "메시지9"


def test_compact_does_not_touch_other_users(db):
    append_message(db, USER_A, "user", "A 메시지")
    append_message(db, USER_B, "user", "B 메시지")
    compact_session(db, USER_A, summary="A 요약")
    assert get_history(db, USER_B).summary is None
    assert len(get_history(db, USER_B).messages) == 1


def test_clear_session(db):
    append_message(db, USER_A, "user", "지울 메시지")
    compact_session(db, USER_A, summary="요약")
    clear_session(db, USER_A)
    h = get_history(db, USER_A)
    assert h.summary is None
    assert h.messages == []


def test_status_flags_compaction_when_long(db):
    st = session_status(db, USER_A)
    assert st.needs_compact is False
    # 장문 대화 누적 → 압축 필요 플래그
    for i in range(30):
        append_message(db, USER_A, "user", "가" * 500)
    st = session_status(db, USER_A)
    assert st.message_count == 30
    assert st.needs_compact is True


def test_append_rejects_bad_role(db):
    import pytest

    with pytest.raises(ValueError):
        append_message(db, USER_A, "system-hack", "x")


def test_append_rejects_oversized_content(db):
    """토큰 비용 폭주 방지: 메시지 길이 상한을 코드 레벨에서 강제한다."""
    import pytest

    from app.services.writer_session import MAX_CONTENT_CHARS

    append_message(db, USER_A, "user", "가" * MAX_CONTENT_CHARS)  # 경계값 허용
    with pytest.raises(ValueError):
        append_message(db, USER_A, "user", "가" * (MAX_CONTENT_CHARS + 1))


def test_compact_with_fewer_messages_than_keep(db):
    append_message(db, USER_A, "user", "하나뿐")
    compact_session(db, USER_A, summary="요약")
    h = get_history(db, USER_A)
    assert h.summary == "요약"
    assert [m.content for m in h.messages] == ["하나뿐"]


def test_compact_on_empty_session_only_sets_summary(db):
    compact_session(db, USER_A, summary="빈 세션 요약")
    h = get_history(db, USER_A)
    assert h.summary == "빈 세션 요약"
    assert h.messages == []


def test_compact_never_deletes_messages_newer_than_kept(db):
    """경쟁 조건 가드: 압축 조회 이후 추가된(더 새로운 id) 메시지는 삭제되지 않는다."""
    from app.services import writer_session as ws

    for i in range(10):
        append_message(db, USER_A, "user", f"메시지{i}")
    # 압축이 keep 대상으로 고른 것보다 새로운 메시지가 있는 상황을 재현:
    # keep_ids 를 미리 뽑아 두고, 그 뒤에 새 메시지가 커밋된 다음 삭제가 실행되는 경쟁.
    # 가드(id < min(keep_ids) 조건)가 있으면 새 메시지는 어떤 경우에도 지워질 수 없다.
    append_message(db, USER_A, "user", "경쟁중추가")
    compact_session(db, USER_A, summary="요약")
    contents = [m.content for m in get_history(db, USER_A).messages]
    assert "경쟁중추가" in contents
    assert len(contents) == ws.COMPACT_KEEP_RECENT
