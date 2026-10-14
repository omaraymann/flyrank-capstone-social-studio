"""Generate a proposal separately from the user's decision to apply it."""
from datetime import timedelta
from time import perf_counter
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.fact_checks import digest
from app.api.variants import owned_variant
from app.config import settings
from app.core.security import current_user
from app.database import get_db
from app.llm.base import LLMError, LLMProvider
from app.llm.registry import get_llm_provider
from app.models import FactCheck, GenerationRun, PlatformVariant, RevisionSuggestion, SourcePost, User, utcnow
from app.schemas import FixSuggestionOut, FixSuggestionRequest, VariantOut
from app.services.fix_suggestions import FIX_PROMPT_VERSION, propose_fix
from app.services.variants import validate_variant

router = APIRouter(tags=["fix suggestions"])


def latest_check(db, variant_id):
    return db.scalar(select(FactCheck).where(FactCheck.variant_id == variant_id).order_by(FactCheck.id.desc()))


def view(row, variant, source, current_check):
    status, error = row.status, row.error_message
    created = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=utcnow().tzinfo)
    if status == 'processing' and created < utcnow() - timedelta(seconds=max(300, 3 * settings.llm_timeout_seconds)):
        status, error = 'failed', 'Suggestion was interrupted. Request a new one.'
    return FixSuggestionOut(id=row.id, variant_id=row.variant_id, fact_check_id=row.fact_check_id,
        status=status, stale=row.draft_hash != digest(variant.content) or row.source_hash != digest(source.content)
            or current_check is None or current_check.id != row.fact_check_id,
        draft_snapshot=row.draft_snapshot, suggested_content=row.suggested_content,
        model=row.model, prompt_version=row.prompt_version, reported_cost_usd=row.reported_cost_usd,
        error_message=error, created_at=row.created_at, completed_at=row.completed_at, applied_at=row.applied_at)


@router.get('/variants/{variant_id}/fix-suggestions/latest', response_model=FixSuggestionOut | None)
def latest(variant_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    variant = owned_variant(variant_id, user, db)
    source = db.get(SourcePost, variant.source_post_id)
    row = db.scalar(select(RevisionSuggestion).where(RevisionSuggestion.variant_id == variant_id).order_by(RevisionSuggestion.id.desc()))
    return view(row, variant, source, latest_check(db, variant_id)) if row else None


@router.post('/variants/{variant_id}/fix-suggestions', response_model=FixSuggestionOut, status_code=201)
async def suggest(payload: FixSuggestionRequest, variant_id: int, user: User = Depends(current_user),
                  db: Session = Depends(get_db), provider: LLMProvider = Depends(get_llm_provider)):
    variant = owned_variant(variant_id, user, db)
    source = db.get(SourcePost, variant.source_post_id)
    check = latest_check(db, variant_id)
    if variant.status != 'draft':
        raise HTTPException(409, 'Suggestions are available for editable drafts only')
    if not check or check.id != payload.fact_check_id or check.status != 'succeeded':
        raise HTTPException(409, 'Run a successful fact check before requesting a fix')
    if check.draft_hash != digest(variant.content) or check.source_hash != digest(source.content):
        raise HTTPException(409, 'The fact check is outdated. Recheck facts first')
    flagged = [claim for claim in (check.result or {}).get('claims', []) if claim['verdict'] in {'unsupported', 'contradicted'}]
    if not flagged:
        raise HTTPException(409, 'There are no flagged factual claims to fix')
    if len(source.content) > settings.llm_max_input_characters:
        raise HTTPException(413, 'Source is too long for a fix suggestion')
    cutoff = utcnow() - timedelta(seconds=max(300, 3 * settings.llm_timeout_seconds))
    db.execute(update(RevisionSuggestion).where(RevisionSuggestion.variant_id == variant_id,
        RevisionSuggestion.status == 'processing', RevisionSuggestion.created_at < cutoff).values(
            status='failed', error_message='Suggestion was interrupted. Request a new one.', completed_at=utcnow()))
    if db.scalar(select(RevisionSuggestion.id).where(RevisionSuggestion.variant_id == variant_id, RevisionSuggestion.status == 'processing')):
        db.rollback()
        raise HTTPException(409, 'A fix suggestion is already running')
    generation = next((run for run in db.scalars(select(GenerationRun).where(
        GenerationRun.source_post_id == source.id, GenerationRun.status == 'succeeded').order_by(GenerationRun.id.desc()))
        if variant.platform in run.platforms.split(',')), None)
    cta = generation.call_to_action if generation and generation.call_to_action in variant.content else None
    row = RevisionSuggestion(variant_id=variant_id, fact_check_id=check.id, draft_snapshot=variant.content,
        draft_hash=digest(variant.content), source_hash=digest(source.content), call_to_action=cta,
        model=settings.llm_model, prompt_version=FIX_PROMPT_VERSION, status='processing')
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'A fix suggestion is already running')
    started = perf_counter()
    try:
        result = await propose_fix(provider, source=check.source_snapshot, draft=row.draft_snapshot,
            platform=variant.platform, claims=flagged, call_to_action=cta,
            audience=generation.audience if generation else 'the existing audience',
            tone=generation.tone if generation else 'preserve the draft tone')
        row.input_tokens, row.output_tokens, row.reported_cost_usd = result.input_tokens, result.output_tokens, result.cost_usd
        proposed = result.variants[variant.platform]
        validate_variant(variant.platform, proposed)
        if cta and cta not in proposed:
            raise ValueError('The suggestion omitted or changed the requested call to action')
        if proposed == row.draft_snapshot:
            raise ValueError('The model returned an unchanged draft. Edit manually or request another suggestion')
        row.suggested_content, row.status = proposed, 'succeeded'
    except (LLMError, ValueError) as exc:
        row.status, row.error_message = 'failed', str(exc)
    except Exception:
        row.status, row.error_message = 'failed', 'Could not generate a fix suggestion. Try again.'
    row.latency_ms = round((perf_counter() - started) * 1000)
    row.completed_at = utcnow()
    db.commit()
    db.refresh(row); db.refresh(variant); db.refresh(source)
    return view(row, variant, source, latest_check(db, variant_id))


@router.post('/variants/{variant_id}/fix-suggestions/{suggestion_id}/apply', response_model=VariantOut)
def apply(variant_id: int, suggestion_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    variant = owned_variant(variant_id, user, db)
    row = db.scalar(select(RevisionSuggestion).where(RevisionSuggestion.id == suggestion_id, RevisionSuggestion.variant_id == variant_id))
    if not row:
        raise HTTPException(404, 'Suggestion not found')
    check = latest_check(db, variant_id)
    source = db.get(SourcePost, variant.source_post_id)
    if row.status != 'succeeded' or row.applied_at is not None or not row.suggested_content:
        raise HTTPException(409, 'This suggestion is not available to apply')
    if view(row, variant, source, check).stale or variant.status != 'draft':
        raise HTTPException(409, 'Draft, source, or fact check changed. Request a fresh suggestion')
    validate_variant(variant.platform, row.suggested_content)
    if row.call_to_action and row.call_to_action not in row.suggested_content:
        raise HTTPException(409, 'Suggestion no longer preserves the requested call to action')
    # Compare and update atomically so another edit or approval cannot be overwritten.
    updated = db.execute(update(PlatformVariant).where(PlatformVariant.id == variant_id,
        PlatformVariant.content == row.draft_snapshot, PlatformVariant.status == 'draft',
        ~exists(select(FactCheck.id).where(FactCheck.variant_id == variant_id, FactCheck.id > row.fact_check_id)),
        exists(select(SourcePost.id).where(SourcePost.id == variant.source_post_id, SourcePost.content == check.source_snapshot)))
        .values(content=row.suggested_content, fact_recheck_required=True, updated_at=utcnow(),
            reviewed_at=None, rejection_reason=None))
    applied = db.execute(update(RevisionSuggestion).where(RevisionSuggestion.id == suggestion_id,
        RevisionSuggestion.applied_at.is_(None)).values(applied_at=utcnow()))
    if updated.rowcount != 1 or applied.rowcount != 1:
        db.rollback()
        raise HTTPException(409, 'Draft or suggestion changed. Refresh before applying')
    db.commit(); db.refresh(variant)
    return variant
