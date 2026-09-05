from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SourcePost(Base):
    __tablename__ = "source_posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    variants: Mapped[list["PlatformVariant"]] = relationship(cascade="all, delete-orphan")


class PlatformVariant(Base):
    __tablename__ = "platform_variants"
    __table_args__ = (
        UniqueConstraint("source_post_id", "platform", name="uq_source_platform"),
        CheckConstraint(
            "status IN ('draft', 'approved', 'rejected', 'scheduled', 'published')",
            name="ck_platform_variants_status",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    source_post_id: Mapped[int] = mapped_column(ForeignKey("source_posts.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GenerationRun(Base):
    __tablename__ = "generation_runs"
    __table_args__ = (
        CheckConstraint("status IN ('processing', 'succeeded', 'failed')", name="ck_generation_runs_status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    source_post_id: Mapped[int] = mapped_column(ForeignKey("source_posts.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(150))
    prompt_version: Mapped[str] = mapped_column(String(50))
    examples_version: Mapped[str] = mapped_column(String(50))
    platforms: Mapped[str] = mapped_column(String(100))
    audience: Mapped[str] = mapped_column(String(300))
    goal: Mapped[str] = mapped_column(String(50))
    tone: Mapped[str] = mapped_column(String(50))
    call_to_action: Mapped[str] = mapped_column(String(500))
    temperature: Mapped[float] = mapped_column(Float)
    top_p: Mapped[float] = mapped_column(Float)
    top_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_output_tokens: Mapped[int] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repair_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="processing")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"
    __table_args__ = (
        UniqueConstraint("variant_id", name="uq_schedule_slots_variant_id"),
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="ck_schedule_slots_status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("platform_variants.id", ondelete="CASCADE"), index=True)
    publish_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PublishDelivery(Base):
    __tablename__ = "publish_deliveries"
    __table_args__ = (
        UniqueConstraint("schedule_slot_id", name="uq_publish_deliveries_schedule_slot_id"),
        UniqueConstraint("idempotency_key", name="uq_publish_deliveries_idempotency_key"),
        CheckConstraint("status IN ('processing', 'succeeded', 'failed')", name="ck_publish_deliveries_status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_slot_id: Mapped[int] = mapped_column(ForeignKey("schedule_slots.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(30))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    content_snapshot: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="processing")
    attempt_count: Mapped[int] = mapped_column(default=1)
    external_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PublishAttempt(Base):
    __tablename__ = "publish_attempts"
    __table_args__ = (
        UniqueConstraint("delivery_id", "attempt_number", name="uq_publish_attempt_number"),
        CheckConstraint(
            "status IN ('processing', 'succeeded', 'failed', 'uncertain')",
            name="ck_publish_attempts_status",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[int] = mapped_column(ForeignKey("publish_deliveries.id", ondelete="CASCADE"), index=True)
    attempt_number: Mapped[int]
    status: Mapped[str] = mapped_column(String(30), default="processing")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
