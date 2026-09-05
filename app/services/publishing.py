from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import PlatformVariant, PublishAttempt, PublishDelivery, ScheduleSlot, utcnow
from app.publishers.base import PublisherError, PublishRequest
from app.publishers.registry import PublisherRegistry


class DeliveryInProgress(RuntimeError):
    pass


class PublishFailed(RuntimeError):
    pass


def make_idempotency_key(variant_id: int, schedule_slot_id: int) -> str:
    operation = f"variant:{variant_id}:schedule:{schedule_slot_id}"
    return sha256(operation.encode()).hexdigest()


def delivery_payload(delivery: PublishDelivery, already_published: bool = False) -> dict:
    return {
        "id": delivery.id,
        "schedule_slot_id": delivery.schedule_slot_id,
        "platform": delivery.platform,
        "idempotency_key": delivery.idempotency_key,
        "status": delivery.status,
        "attempt_count": delivery.attempt_count,
        "external_post_id": delivery.external_post_id,
        "external_url": delivery.external_url,
        "error_message": delivery.error_message,
        "created_at": delivery.created_at,
        "completed_at": delivery.completed_at,
        "already_published": already_published,
    }


async def publish_scheduled_variant(
    db: Session,
    schedule: ScheduleSlot,
    variant: PlatformVariant,
    registry: PublisherRegistry,
) -> dict:
    key = make_idempotency_key(variant.id, schedule.id)
    delivery = db.scalar(select(PublishDelivery).where(PublishDelivery.idempotency_key == key))
    if delivery and delivery.status == "succeeded":
        return delivery_payload(delivery, already_published=True)
    if delivery and delivery.status == "processing":
        raise DeliveryInProgress("This publishing operation is already in progress")

    if delivery:
        delivery.status = "processing"
        delivery.attempt_count += 1
        delivery.error_message = None
    else:
        delivery = PublishDelivery(
            schedule_slot_id=schedule.id,
            platform=variant.platform,
            idempotency_key=key,
            content_snapshot=variant.content,
        )
        db.add(delivery)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(PublishDelivery).where(PublishDelivery.idempotency_key == key))
        if existing and existing.status == "succeeded":
            return delivery_payload(existing, already_published=True)
        raise DeliveryInProgress("This publishing operation is already in progress")
    db.refresh(delivery)
    attempt = PublishAttempt(delivery_id=delivery.id, attempt_number=delivery.attempt_count)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    try:
        result = await registry.get(variant.platform).publish(
            PublishRequest(content=variant.content, idempotency_key=key)
        )
    except PublisherError as exc:
        safe_error = str(exc)
        delivery.status = "failed"
        delivery.error_message = safe_error[:500]
        delivery.completed_at = utcnow()
        attempt.status = "failed"
        attempt.error_message = safe_error[:500]
        attempt.completed_at = utcnow()
        db.commit()
        raise PublishFailed(safe_error) from exc
    except Exception as exc:
        safe_error = "Publisher failed unexpectedly"
        delivery.status = "failed"
        delivery.error_message = safe_error
        delivery.completed_at = utcnow()
        attempt.status = "failed"
        attempt.error_message = safe_error
        attempt.completed_at = utcnow()
        db.commit()
        raise PublishFailed(safe_error) from exc

    delivery.status = "succeeded"
    delivery.external_post_id = result.external_post_id
    delivery.external_url = result.external_url
    delivery.completed_at = utcnow()
    attempt.status = "succeeded"
    attempt.completed_at = utcnow()
    schedule.status = "completed"
    schedule.next_attempt_at = None
    schedule.lease_expires_at = None
    schedule.last_error = None
    variant.status = "published"
    variant.updated_at = utcnow()
    db.commit()
    db.refresh(delivery)
    return delivery_payload(delivery)
