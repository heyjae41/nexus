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
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Category(Base):
    """메인화면 섹션/메뉴."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    articles: Mapped[list["Article"]] = relationship(back_populates="category")


class Article(Base):
    """글: 뉴스레터/컬럼/가이드(internal) + 브런치 수집글(brunch)."""

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
    source_url: Mapped[str | None] = mapped_column(String(1000))
    thumbnail_url: Mapped[str | None] = mapped_column(String(1000))  # 목록 카드 대표 이미지
    content_filename: Mapped[str | None] = mapped_column(String(300), unique=True)
    read_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    likes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published")
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    category: Mapped[Category] = relationship(back_populates="articles")


class Member(Base):
    """경량 회원 — 닉네임 기반 식별 (비밀번호 없는 프로토타입 정책)."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nickname: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), unique=True)  # 최초 1회만 등록, 수정 불가
    role: Mapped[str | None] = mapped_column(String(20))
    interests: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class CommunityPost(Base):
    """커뮤니티 글."""

    __tablename__ = "community_posts"
    __table_args__ = (
        Index("ix_community_posts_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id"))
    author_name: Mapped[str] = mapped_column(String(50), nullable=False)
    tag: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    likes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class CommunityPostLike(Base):
    """커뮤니티 글 좋아요 — 회원당 글 1개 (토글, 어뷰징 방지)."""

    __tablename__ = "community_post_likes"

    post_id: Mapped[int] = mapped_column(
        ForeignKey("community_posts.id"), primary_key=True
    )
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class CommunityComment(Base):
    """커뮤니티 댓글."""

    __tablename__ = "community_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("community_posts.id"), nullable=False
    )
    member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id"))
    author_name: Mapped[str] = mapped_column(String(50), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


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
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_system_type: Mapped[str | None] = mapped_column(String(20))
    category: Mapped[str | None] = mapped_column(String(100))
    cover_image_url: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published")
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class MeetupCollectRun(Base):
    """밋업 수집 이력."""

    __tablename__ = "meetup_collect_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    candidates_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class WriterSession(Base):
    """작가(텔레그램 userid)별 대화 세션 — 압축 요약 보관."""

    __tablename__ = "writer_sessions"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    summary: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class BrunchCollectRun(Base):
    """브런치 수집 이력 (12시간 주기)."""

    __tablename__ = "brunch_collect_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    candidates_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    picked_article_id: Mapped[int | None] = mapped_column(ForeignKey("articles.id"))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
