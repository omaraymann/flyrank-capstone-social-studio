"""Try generation and judging on the project's published article/tweet sample."""

import argparse
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.llm.base import GenerationSettings, LLMError
from app.llm.openrouter import OpenRouterProvider
from app.services.prompts import EXAMPLES_VERSION, PROMPT_VERSION, generation_prompt, system_prompt
from app.services.variants import validate_variant
from evaluations.judge import evaluate_draft

SOURCE_URL = "https://arjungambhir.github.io/Domain_Specific_tweet_generation/"


def published_sample(html):
    soup = BeautifulSoup(html, "html.parser")
    values = {}
    for title in ("Sample Source Article", "Actual Tweet related to Article"):
        heading = soup.find(lambda tag: tag.name in ("h2", "h3", "h4") and tag.get_text(strip=True) == title)
        if heading is None:
            raise ValueError(f"Published sample section not found: {title}")
        chunks = []
        anchor = heading.parent if heading.parent.name == "header" else heading
        for element in anchor.next_siblings:
            if getattr(element, "name", None) in ("h2", "h3", "h4"):
                break
            if getattr(element, "name", None) == "blockquote":
                chunks.append(element.get_text(" ", strip=True))
        values[title] = " ".join(" ".join(chunks).split())
        if not values[title]:
            raise ValueError(f"Published sample is empty: {title}")
    return values["Sample Source Article"], values["Actual Tweet related to Article"]


async def main(output):
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "One published article excerpt/tweet pair; demonstration, not benchmark accuracy.",
        "source_url": SOURCE_URL,
        "limitations": [
            "The reported 70000-pair dataset is not included in the repository.",
            "Only the article text displayed on the project page is used, not a verified full original article.",
            "There are no independent factuality labels for these drafts.",
            "Generator and judge use the same model, so their errors may be correlated.",
        ],
        "evaluations": [],
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(SOURCE_URL)
        response.raise_for_status()
    source, reference = published_sample(response.text)
    report.update(source_text=source, source_sha256=hashlib.sha256(source.encode()).hexdigest(), reference_tweet=reference)
    output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    save()
    if not settings.openrouter_api_key:
        report["status"] = "blocked"
        report["error"] = "OpenRouter is not configured"
        save()
        print(report["error"])
        return

    provider = OpenRouterProvider(settings.openrouter_api_key, settings.openrouter_base_url, settings.llm_timeout_seconds)
    generation_settings = GenerationSettings(
        model=settings.llm_model, temperature=settings.llm_temperature,
        top_p=settings.llm_top_p, top_k=settings.llm_top_k,
        max_output_tokens=settings.llm_max_output_tokens,
    )
    cta = "Read the report"
    started = perf_counter()
    try:
        result = await provider.generate(
            system_prompt=system_prompt(["x", "linkedin"]),
            user_prompt=generation_prompt(
                title="US-Mexico border arrests continued to drop in September",
                content=source, source_url=None, audience="readers interested in news reporting",
                goal="traffic", tone="professional", call_to_action=cta, platforms=["x", "linkedin"],
            ),
            platforms=["x", "linkedin"], settings=generation_settings,
        )
        report["generation"] = {
            "status": "succeeded", "model": settings.llm_model,
            "prompt_version": PROMPT_VERSION, "examples_version": EXAMPLES_VERSION,
            "temperature": generation_settings.temperature, "top_p": generation_settings.top_p,
            "top_k": generation_settings.top_k, "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens, "reported_cost_usd": result.cost_usd,
            "latency_ms": round((perf_counter() - started) * 1000), "drafts": result.variants,
            "repair_policy": "No repair in this baseline trial; retain first-pass output.",
        }
    except (LLMError, httpx.RequestError):
        report["generation"] = {"status": "failed", "error": "Generation provider failed"}
        result = None
    save()

    drafts = [("published_reference", "x", reference)]
    if result is not None:
        drafts.extend(("generated", platform, draft) for platform, draft in result.variants.items())
    for origin, platform, draft in drafts:
        checks = {"characters": len(draft), "exact_cta_pass": cta in draft if origin == "generated" else None}
        try:
            validate_variant(platform, draft)
            checks["platform_rules_pass"] = True
        except ValueError as exc:
            checks.update(platform_rules_pass=False, platform_error=str(exc))
        try:
            judgement = await evaluate_draft(
                source=source, draft=draft, api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url, model=settings.llm_model,
                timeout=settings.llm_timeout_seconds,
            )
        except LLMError as exc:
            judgement = {"status": "failed", "error": str(exc)}
        report["evaluations"].append({"origin": origin, "platform": platform, "draft": draft, "checks": checks, "judge": judgement})
        save()
        print(origin, platform, "judge:", judgement["status"], "supported rate:", judgement.get("supported_claim_rate"))
    report["status"] = "completed" if result is not None and all(e["judge"]["status"] == "succeeded" for e in report["evaluations"]) else "partial"
    save()
    print(f"Trial saved to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evaluations/results/published_sample_trial.json"))
    args = parser.parse_args()
    asyncio.run(main(args.output))
