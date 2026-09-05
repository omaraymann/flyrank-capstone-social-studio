import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import PlatformVariant, PublishAttempt, PublishDelivery, ScheduleSlot
from app.publishers.registry import PublisherRegistry, publisher_registry
from app.services.publishing import PublishFailed, publish_scheduled_variant

logger = logging.getLogger("social_studio.worker")


def recover_expired_leases(db: Session, now: datetime):
    stale = db.scalars(
        select(ScheduleSlot).where(
            ScheduleSlot.status == "processing",
            ScheduleSlot.lease_expires_at.is_not(None),
            ScheduleSlot.lease_expires_at <= now,
        )
    ).all()
    for schedule in stale:
        delivery = db.scalar(select(PublishDelivery).where(PublishDelivery.schedule_slot_id == schedule.id))
        if delivery and delivery.status == "processing":
            attempt = db.scalar(
                select(PublishAttempt)
                .where(PublishAttempt.delivery_id == delivery.id, PublishAttempt.status == "processing")
                .order_by(PublishAttempt.attempt_number.desc())
            )
            if delivery.platform == "discord":
                message = "Outcome uncertain after worker lease expired; manual reconciliation required"
                delivery.status = "failed"
                delivery.error_message = message
                schedule.status = "failed"
                schedule.last_error = message
                if attempt:
                    attempt.status = "uncertain"
                    attempt.error_message = message
                    attempt.completed_at = now
            else:
                message = "Worker lease expired before completion; safe mock retry scheduled"
                delivery.status = "failed"
                delivery.error_message = message
                schedule.status = "pending"
                schedule.next_attempt_at = now
                schedule.last_error = message
                if attempt:
                    attempt.status = "failed"
                    attempt.error_message = message
                    attempt.completed_at = now
        else:
            schedule.status = "pending"
            schedule.next_attempt_at = now
            schedule.last_error = "Worker lease expired before delivery started"
        schedule.worker_id = None
        schedule.claimed_at = None
        schedule.lease_expires_at = None
    db.commit()


def claim_due_schedule(db: Session, worker_id: str, now: datetime) -> int | None:
    schedule = db.scalar(
        select(ScheduleSlot)
        .where(
            ScheduleSlot.status == "pending",
            ScheduleSlot.publish_at <= now,
            or_(ScheduleSlot.next_attempt_at.is_(None), ScheduleSlot.next_attempt_at <= now),
        )
        .order_by(ScheduleSlot.publish_at, ScheduleSlot.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not schedule:
        return None
    schedule.status = "processing"
    schedule.worker_id = worker_id
    schedule.claimed_at = now
    schedule.lease_expires_at = now + timedelta(seconds=settings.worker_lease_seconds)
    db.commit()
    return schedule.id


async def process_claimed_schedule(db: Session, schedule_id: int, registry: PublisherRegistry):
    row = db.execute(
        select(ScheduleSlot, PlatformVariant)
        .join(PlatformVariant, ScheduleSlot.variant_id == PlatformVariant.id)
        .where(ScheduleSlot.id == schedule_id)
    ).first()
    if not row:
        return
    schedule, variant = row
    try:
        await publish_scheduled_variant(db, schedule, variant, registry)
    except PublishFailed as exc:
        db.refresh(schedule)
        delivery = db.scalar(select(PublishDelivery).where(PublishDelivery.schedule_slot_id == schedule.id))
        attempts = delivery.attempt_count if delivery else 1
        schedule.last_error = str(exc)
        schedule.worker_id = None
        schedule.claimed_at = None
        schedule.lease_expires_at = None
        if attempts < settings.max_publish_attempts:
            delay = settings.retry_base_seconds * (2 ** (attempts - 1))
            schedule.status = "pending"
            schedule.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        else:
            schedule.status = "failed"
            schedule.next_attempt_at = None
        db.commit()


async def run_once(registry: PublisherRegistry = publisher_registry, worker_id: str | None = None) -> bool:
    worker_id = worker_id or f"worker-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        recover_expired_leases(db, now)
        schedule_id = claim_due_schedule(db, worker_id, now)
    if schedule_id is None:
        return False
    with SessionLocal() as db:
        await process_claimed_schedule(db, schedule_id, registry)
    return True
