from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import current_user
from app.database import get_db
from app.models import GenerationRun, PlatformVariant, PublishDelivery, ScheduleSlot, SourcePost, User

router = APIRouter(prefix="/analytics", tags=["workspace analytics"])


class AIUsageOut(BaseModel):
    runs: int
    succeeded: int
    failed: int
    processing: int
    input_tokens: int
    output_tokens: int
    repair_count: int
    reported_cost_usd: float | None
    runs_with_reported_cost: int
    average_latency_ms: float | None


class WorkspaceAnalyticsOut(BaseModel):
    campaigns: int
    variants_by_status: dict[str, int]
    schedules_by_status: dict[str, int]
    deliveries_by_status: dict[str, int]
    delivery_success_rate: float | None
    ai_usage: AIUsageOut


@router.get("/summary", response_model=WorkspaceAnalyticsOut)
def workspace_summary(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Lifetime operational metrics for the authenticated owner's workspace."""
    owned_posts = select(SourcePost.id).where(SourcePost.owner_id == user.id)
    owned_variants = select(PlatformVariant.id).where(PlatformVariant.source_post_id.in_(owned_posts))
    owned_schedules = select(ScheduleSlot.id).where(ScheduleSlot.variant_id.in_(owned_variants))

    def status_counts(model, ownership, statuses):
        rows = db.execute(
            select(model.status, func.count()).where(ownership).group_by(model.status)
        ).all()
        return {**dict.fromkeys(statuses, 0), **dict(rows)}

    variants = status_counts(
        PlatformVariant, PlatformVariant.source_post_id.in_(owned_posts),
        ("draft", "approved", "rejected", "scheduled", "published"),
    )
    schedules = status_counts(
        ScheduleSlot, ScheduleSlot.variant_id.in_(owned_variants),
        ("pending", "processing", "completed", "failed"),
    )
    deliveries = status_counts(
        PublishDelivery, PublishDelivery.schedule_slot_id.in_(owned_schedules),
        ("processing", "succeeded", "failed"),
    )
    generation_statuses = status_counts(
        GenerationRun, GenerationRun.source_post_id.in_(owned_posts),
        ("processing", "succeeded", "failed"),
    )
    usage = db.execute(
        select(
            func.coalesce(func.sum(GenerationRun.input_tokens), 0),
            func.coalesce(func.sum(GenerationRun.output_tokens), 0),
            func.coalesce(func.sum(GenerationRun.repair_count), 0),
            func.sum(GenerationRun.estimated_cost_usd),
            func.count(GenerationRun.estimated_cost_usd),
            func.avg(GenerationRun.latency_ms),
        ).where(GenerationRun.source_post_id.in_(owned_posts))
    ).one()
    completed_deliveries = deliveries["succeeded"] + deliveries["failed"]
    return WorkspaceAnalyticsOut(
        campaigns=db.scalar(select(func.count()).select_from(SourcePost).where(SourcePost.owner_id == user.id)),
        variants_by_status=variants,
        schedules_by_status=schedules,
        deliveries_by_status=deliveries,
        delivery_success_rate=(deliveries["succeeded"] / completed_deliveries if completed_deliveries else None),
        ai_usage=AIUsageOut(
            runs=sum(generation_statuses.values()),
            **generation_statuses,
            input_tokens=usage[0], output_tokens=usage[1], repair_count=usage[2],
            reported_cost_usd=usage[3], runs_with_reported_cost=usage[4], average_latency_ms=usage[5],
        ),
    )
