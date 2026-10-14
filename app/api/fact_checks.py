"""Owner-scoped, on-demand factuality checks of saved variant snapshots."""
import hashlib
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.variants import owned_variant
from app.config import settings
from app.core.security import current_user
from app.database import get_db
from app.llm.base import LLMError
from app.models import FactCheck, PlatformVariant, SourcePost, User, utcnow
from app.services.factuality import JUDGE_PROMPT_VERSION, evaluate_draft
from app.schemas import FactCheckOut

router = APIRouter(tags=["fact checks"])

def digest(content):
    return hashlib.sha256(content.encode()).hexdigest()

async def configured_judge(*, source, draft):
    return await evaluate_draft(source=source, draft=draft,
        api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url,
        model=settings.llm_model, timeout=settings.llm_timeout_seconds)

def get_fact_judge():
    return configured_judge

def output(check, variant, source):
    result = check.result or {}
    outcome = check.status
    if check.status == "succeeded":
        if result.get("requires_review") is None:
            outcome = "unknown"
        else:
            outcome = "needs_review" if result["requires_review"] else "no_issues"
    error_message = check.error_message
    if check.status == "processing":
        created_at = check.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=utcnow().tzinfo)
        if created_at < utcnow() - timedelta(seconds=max(300, 3 * settings.llm_timeout_seconds)):
            outcome = "failed"
            error_message = "Fact check was interrupted. Run it again."
    return FactCheckOut(id=check.id, variant_id=check.variant_id, status=check.status,
        outcome=outcome, stale=check.draft_hash != digest(variant.content) or check.source_hash != digest(source.content),
        draft_snapshot=check.draft_snapshot, claims=result.get("claims", []),
        error_message=error_message, prompt_version=check.prompt_version,
        extraction_model=check.extraction_model, audit_model=check.audit_model,
        reported_cost_usd=result.get("reported_cost_usd"), latency_ms=result.get("latency_ms"),
        created_at=check.created_at, completed_at=check.completed_at)

@router.get("/variants/{variant_id}/fact-check", response_model=FactCheckOut | None)
def latest(variant_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    variant = owned_variant(variant_id, user, db)
    source = db.get(SourcePost, variant.source_post_id)
    check = db.scalar(select(FactCheck).where(FactCheck.variant_id == variant_id).order_by(FactCheck.id.desc()))
    return output(check, variant, source) if check else None

@router.post("/variants/{variant_id}/fact-check", response_model=FactCheckOut, status_code=201)
async def run_check(variant_id: int, user: User = Depends(current_user),
                    db: Session = Depends(get_db), judge=Depends(get_fact_judge)):
    variant = owned_variant(variant_id, user, db)
    source = db.get(SourcePost, variant.source_post_id)
    if len(source.content) > settings.llm_max_input_characters:
        raise HTTPException(status_code=413, detail="Source is too long for a fact check")
    # Allow recovery after an interrupted API process; ordinary checks finish within two provider timeouts.
    cutoff = utcnow() - timedelta(seconds=max(300, 3 * settings.llm_timeout_seconds))
    db.execute(update(FactCheck).where(FactCheck.variant_id == variant_id,
        FactCheck.status == "processing", FactCheck.created_at < cutoff).values(
            status="failed", error_message="Fact check was interrupted. Run it again.", completed_at=utcnow()))
    if db.scalar(select(FactCheck.id).where(FactCheck.variant_id == variant_id, FactCheck.status == "processing")):
        db.rollback()
        raise HTTPException(status_code=409, detail="A fact check is already running for this draft")
    check = FactCheck(variant_id=variant_id, draft_snapshot=variant.content, source_snapshot=source.content,
        draft_hash=digest(variant.content), source_hash=digest(source.content),
        prompt_version=JUDGE_PROMPT_VERSION, extraction_model=settings.llm_model,
        audit_model=settings.judge_audit_model, status="processing")
    db.add(check)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A fact check is already running for this draft")
    try:
        result = await judge(source=check.source_snapshot, draft=check.draft_snapshot)
        check.result = result
        check.status = "succeeded"
    except LLMError as exc:
        check.status = "failed"
        check.error_message = str(exc)
    except Exception:
        check.status = "failed"
        check.error_message = "Fact check could not complete. Try again."
    check.completed_at = utcnow()
    db.commit()
    db.refresh(check)
    db.refresh(variant)
    db.refresh(source)
    if check.status == "succeeded" and check.draft_hash == digest(variant.content) and check.source_hash == digest(source.content):
        db.execute(update(PlatformVariant).where(PlatformVariant.id == variant_id,
            PlatformVariant.content == check.draft_snapshot,
            exists(select(SourcePost.id).where(SourcePost.id == source.id, SourcePost.content == check.source_snapshot)))
            .values(fact_recheck_required=False))
        db.commit()
    return output(check, variant, source)
