"""SQLAlchemy 모델 — docs/ARCHITECTURE.md 의 스키마 정의를 따른다."""
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# 반복되는 컬럼 레시피 — 모델마다 동일 파라미터를 재선언하지 않는다
def _ts_now_col() -> Mapped[datetime]:
    """생성/수집 시각 컬럼 (기본값 now)."""
    return mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())


def _ts_now_onupdate_col() -> Mapped[datetime]:
    """수정 시각 컬럼 (갱신 시 자동 반영)."""
    return mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )


def _int_zero_col() -> Mapped[int]:
    """0 에서 시작하는 정수 컬럼 (카운트·정렬순서)."""
    return mapped_column(Integer, nullable=False, default=0, server_default=text("0"))


def _published_status_col() -> Mapped[str]:
    """published 기본 상태 컬럼."""
    return mapped_column(
        String(20), nullable=False, default="published", server_default=text("'published'")
    )


class Base(DeclarativeBase):
    pass


class Category(Base):
    """메인화면 섹션/메뉴."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    display_order: Mapped[int] = _int_zero_col()
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = _ts_now_col()

    articles: Mapped[list["Article"]] = relationship(back_populates="category")


class Article(Base):
    """글: 포맷(newsletter/column/guide)과 수집 출처(source_type)를 분리한다."""

    __tablename__ = "articles"
    __table_args__ = (
        Index("ix_articles_category_status_published", "category_id", "status", "published_at"),
        Index("ix_articles_type_published", "article_type", "published_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )
    article_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500))
    body_html: Mapped[str | None] = mapped_column(Text)
    key_visual_html: Mapped[str | None] = mapped_column(Text)
    author_name: Mapped[str | None] = mapped_column(String(100))
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000), unique=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1000))  # 목록 카드 대표 이미지
    content_filename: Mapped[str | None] = mapped_column(String(300), unique=True)
    read_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=4, server_default=text("4"))
    likes_count: Mapped[int] = _int_zero_col()
    comments_count: Mapped[int] = _int_zero_col()
    view_count: Mapped[int] = _int_zero_col()
    status: Mapped[str] = _published_status_col()
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = _ts_now_col()
    updated_at: Mapped[datetime] = _ts_now_onupdate_col()

    category: Mapped[Category] = relationship(back_populates="articles")


class Member(Base):
    """회원 — 닉네임 식별 + 비밀번호(PBKDF2 해시) 인증."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nickname: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # NULL = 비밀번호 정책 도입 이전 레거시 계정 (로그인 시 인증 실패로 처리)
    password_hash: Mapped[str | None] = mapped_column(String(300))
    role: Mapped[str | None] = mapped_column(String(20))
    interests: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = _ts_now_col()


class AuthSession(Base):
    """로그인 세션 — 쿠키 원문 대신 SHA-256 해시만 저장한다."""

    __tablename__ = "auth_sessions"
    __table_args__ = (Index("ix_auth_sessions_member", "member_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _ts_now_col()


class CommunityPost(Base):
    """커뮤니티 글."""

    __tablename__ = "community_posts"
    __table_args__ = (
        Index("ix_community_posts_status_created", "status", "created_at"),
        Index("ix_community_posts_member", "member_id"),  # PG 는 FK 자동 인덱스 없음
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id"))
    author_name: Mapped[str] = mapped_column(String(50), nullable=False)
    tag: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    likes_count: Mapped[int] = _int_zero_col()
    comments_count: Mapped[int] = _int_zero_col()
    status: Mapped[str] = _published_status_col()
    created_at: Mapped[datetime] = _ts_now_col()


class CommunityPostLike(Base):
    """커뮤니티 글 좋아요 — 회원당 글 1개 (토글, 어뷰징 방지)."""

    __tablename__ = "community_post_likes"

    post_id: Mapped[int] = mapped_column(
        ForeignKey("community_posts.id"), primary_key=True
    )
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id"), primary_key=True
    )
    created_at: Mapped[datetime] = _ts_now_col()


class CommunityComment(Base):
    """커뮤니티 댓글."""

    __tablename__ = "community_comments"
    __table_args__ = (
        # 게시글별 댓글 조회·회원 연결 해제(탈회) 경로 — PG 는 FK 자동 인덱스 없음
        Index("ix_community_comments_post", "post_id"),
        Index("ix_community_comments_member", "member_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("community_posts.id"), nullable=False
    )
    member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id"))
    author_name: Mapped[str] = mapped_column(String(50), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _ts_now_col()


class Course(Base):
    """외부 학습 과정 — 현재 패스트캠퍼스 공개 카테고리 API 수집."""

    __tablename__ = "courses"
    __table_args__ = (
        Index("ix_courses_status_category_rank", "status", "source_category_code", "source_rank"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    source_category_code: Mapped[str] = mapped_column(String(50), nullable=False)
    source_category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_category_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_rank: Mapped[int] = _int_zero_col()
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1000))
    sub_category_name: Mapped[str | None] = mapped_column(String(100))
    format_name: Mapped[str | None] = mapped_column(String(100))
    qualification: Mapped[str | None] = mapped_column(String(100))
    running_time_minutes: Mapped[int | None] = mapped_column(Integer)
    sale_price: Mapped[int | None] = mapped_column(Integer)
    list_price: Mapped[int | None] = mapped_column(Integer)
    badges: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = _published_status_col()
    collected_at: Mapped[datetime] = _ts_now_col()
    updated_at: Mapped[datetime] = _ts_now_onupdate_col()


class FastCampusCollectRun(Base):
    """패스트캠퍼스 클래스 수집 이력."""

    __tablename__ = "fastcampus_collect_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    candidates_count: Mapped[int] = _int_zero_col()
    added_count: Mapped[int] = _int_zero_col()
    updated_count: Mapped[int] = _int_zero_col()
    hidden_count: Mapped[int] = _int_zero_col()
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts_now_col()


class MeetupEvent(Base):
    """meet.pl 밋업 이벤트 (event-us.kr 수집)."""

    __tablename__ = "meetup_events"
    __table_args__ = (Index("ix_meetup_events_start", "event_start"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    host_name: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    event_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    place: Mapped[str | None] = mapped_column(String(300))
    area: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(300))
    # NULL = 가격 미상 (luma 등 가격 정보를 제공하지 않는 소스)
    price_min: Mapped[int | None] = mapped_column(Integer)
    is_free: Mapped[bool | None] = mapped_column(Boolean)
    view_count: Mapped[int] = _int_zero_col()
    event_system_type: Mapped[str | None] = mapped_column(String(20))
    category: Mapped[str | None] = mapped_column(String(100))
    cover_image_url: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = _published_status_col()
    collected_at: Mapped[datetime] = _ts_now_col()


class MeetupCollectRun(Base):
    """밋업 수집 이력."""

    __tablename__ = "meetup_collect_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    candidates_count: Mapped[int] = _int_zero_col()
    added_count: Mapped[int] = _int_zero_col()
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts_now_col()


class WriterSession(Base):
    """작가(텔레그램 userid)별 대화 세션 — 압축 요약 보관."""

    __tablename__ = "writer_sessions"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    summary: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = _ts_now_onupdate_col()


class WriterMessage(Base):
    """작가별 대화 메시지 (userid 기준 완전 분리)."""

    __tablename__ = "writer_messages"
    __table_args__ = (
        Index("ix_writer_messages_user_created", "telegram_user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role: Mapped[str] = mapped_column(String(12), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _ts_now_col()


class BrunchCollectRun(Base):
    """브런치 수집 이력 (12시간 주기)."""

    __tablename__ = "brunch_collect_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    candidates_count: Mapped[int] = _int_zero_col()
    picked_article_id: Mapped[int | None] = mapped_column(ForeignKey("articles.id"))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts_now_col()
