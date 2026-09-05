from time import perf_counter

from sqlalchemy.orm import Session

from app.config import settings
from app.llm.base import GenerationSettings, LLMError, LLMProvider, LLMResult
from app.models import GenerationRun, PlatformVariant, SourcePost, utcnow
from app.schemas import GenerateVariants
from app.services.prompts import (
    EXAMPLES_VERSION,
    PROMPT_VERSION,
    generation_prompt,
    repair_prompt,
    system_prompt,
)
from app.services.variants import validate_variant


def _settings(temperature: float | None = None) -> GenerationSettings:
    return GenerationSettings(
        model=settings.llm_model,
        temperature=settings.llm_temperature if temperature is None else temperature,
        top_p=settings.llm_top_p,
        top_k=settings.llm_top_k,
        max_output_tokens=settings.llm_max_output_tokens,
    )


def _add_usage(run: GenerationRun, result: LLMResult) -> None:
    if result.input_tokens is not None:
        run.input_tokens = (run.input_tokens or 0) + result.input_tokens
    if result.output_tokens is not None:
        run.output_tokens = (run.output_tokens or 0) + result.output_tokens
    if result.cost_usd is not None:
        run.estimated_cost_usd = (run.estimated_cost_usd or 0) + result.cost_usd


def _validate_generated(platform: str, content: str, call_to_action: str) -> None:
    validate_variant(platform, content)
    if call_to_action.lower() not in content.lower():
        raise ValueError(f'content must include the call to action: "{call_to_action}"')


async def generate_llm_variants(
    db: Session,
    post: SourcePost,
    payload: GenerateVariants,
    provider: LLMProvider,
) -> list[PlatformVariant]:
    requested = list(dict.fromkeys(payload.platforms))
    generation_settings = _settings()
    run = GenerationRun(
        source_post_id=post.id,
        provider=provider.name,
        model=generation_settings.model,
        prompt_version=PROMPT_VERSION,
        examples_version=EXAMPLES_VERSION,
        platforms=",".join(requested),
        audience=payload.audience,
        goal=payload.goal,
        tone=payload.tone,
        call_to_action=payload.call_to_action,
        temperature=generation_settings.temperature,
        top_p=generation_settings.top_p,
        top_k=generation_settings.top_k,
        max_output_tokens=generation_settings.max_output_tokens,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    started = perf_counter()
    try:
        result = await provider.generate(
            system_prompt=system_prompt(requested),
            user_prompt=generation_prompt(
                title=post.title,
                content=post.content[: settings.llm_max_input_characters],
                source_url=post.source_url,
                audience=payload.audience,
                goal=payload.goal,
                tone=payload.tone,
                call_to_action=payload.call_to_action,
                platforms=requested,
            ),
            platforms=requested,
            settings=generation_settings,
        )
        _add_usage(run, result)
        final_content = dict(result.variants)
        for platform in requested:
            try:
                _validate_generated(platform, final_content[platform], payload.call_to_action)
            except ValueError as validation_error:
                repaired = await provider.generate(
                    system_prompt=system_prompt([platform]),
                    user_prompt=repair_prompt(
                        platform=platform,
                        content=final_content[platform],
                        errors=str(validation_error),
                    ),
                    platforms=[platform],
                    settings=_settings(temperature=0.1),
                )
                run.repair_count += 1
                _add_usage(run, repaired)
                final_content[platform] = repaired.variants[platform]
                _validate_generated(platform, final_content[platform], payload.call_to_action)

        variants = [
            PlatformVariant(source_post_id=post.id, platform=platform, content=final_content[platform])
            for platform in requested
        ]
        db.add_all(variants)
        run.status = "succeeded"
        run.completed_at = utcnow()
        run.latency_ms = round((perf_counter() - started) * 1000)
        db.commit()
        for variant in variants:
            db.refresh(variant)
        return variants
    except (LLMError, ValueError, KeyError) as exc:
        run.status = "failed"
        run.error_message = str(exc)[:500]
        run.completed_at = utcnow()
        run.latency_ms = round((perf_counter() - started) * 1000)
        db.commit()
        if isinstance(exc, LLMError):
            raise
        raise LLMError(f"Generated content failed validation: {exc}") from exc
