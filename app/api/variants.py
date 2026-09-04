from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import current_user
from app.database import get_db
from app.models import PlatformVariant, ScheduleSlot, SourcePost, User
from app.schemas import ScheduleCreate, ScheduleOut, VariantEdit, VariantOut, VariantReject
from app.services.review import (
    InvalidStatusTransition,
    VariantStatus,
    approve_variant,
    change_status,
    edit_variant,
    reject_variant,
)

router = APIRouter(tags=["variant review"])


def owned_variant(variant_id: int, user: User, db: Session) -> PlatformVariant:
    variant = db.scalar(
        select(PlatformVariant)
        .join(SourcePost, PlatformVariant.source_post_id == SourcePost.id)
        .where(PlatformVariant.id == variant_id, SourcePost.owner_id == user.id)
    )
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    return variant


def review_error(exc: ValueError) -> HTTPException:
    code = status.HTTP_409_CONFLICT if isinstance(exc, InvalidStatusTransition) else status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(status_code=code, detail=str(exc))


@router.get("/posts/{post_id}/variants", response_model=list[VariantOut])
def list_variants(post_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owns_post = db.scalar(select(SourcePost.id).where(SourcePost.id == post_id, SourcePost.owner_id == user.id))
    if not owns_post:
        raise HTTPException(status_code=404, detail="Source post not found")
    return db.scalars(
        select(PlatformVariant).where(PlatformVariant.source_post_id == post_id).order_by(PlatformVariant.id)
    ).all()


@router.get("/variants/{variant_id}", response_model=VariantOut)
def get_variant(variant_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return owned_variant(variant_id, user, db)


@router.patch("/variants/{variant_id}", response_model=VariantOut)
def update_variant(payload: VariantEdit, variant_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    variant = owned_variant(variant_id, user, db)
    try:
        edit_variant(variant, payload.content)
    except ValueError as exc:
        raise review_error(exc)
    db.commit()
    db.refresh(variant)
    return variant


@router.post("/variants/{variant_id}/approve", response_model=VariantOut)
def approve(variant_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    variant = owned_variant(variant_id, user, db)
    try:
        approve_variant(variant)
    except ValueError as exc:
        raise review_error(exc)
    db.commit()
    db.refresh(variant)
    return variant


@router.post("/variants/{variant_id}/reject", response_model=VariantOut)
def reject(payload: VariantReject, variant_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    variant = owned_variant(variant_id, user, db)
    try:
        reject_variant(variant, payload.reason)
    except ValueError as exc:
        raise review_error(exc)
    db.commit()
    db.refresh(variant)
    return variant


@router.post("/variants/{variant_id}/schedule", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def schedule(payload: ScheduleCreate, variant_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    variant = owned_variant(variant_id, user, db)
    if payload.publish_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Publishing time must be in the future")
    try:
        change_status(variant, VariantStatus.SCHEDULED)
    except ValueError as exc:
        raise review_error(exc)
    slot = ScheduleSlot(variant_id=variant.id, publish_at=payload.publish_at)
    db.add(slot)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Variant is already scheduled")
    db.refresh(slot)
    return slot
