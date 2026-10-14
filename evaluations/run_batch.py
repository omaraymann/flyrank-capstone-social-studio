"""Run a blind claim-classification benchmark and write raw data plus a report."""

import argparse
import asyncio
from datetime import datetime
import hashlib
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from zoneinfo import ZoneInfo

from app.config import settings
from app.llm.base import LLMError
from evaluations.judge import evaluate_draft

ROOT = Path(__file__).resolve().parent
VERDICTS = ("supported", "contradicted", "unsupported")


def metrics(rows):
    successful = [r for r in rows if r["judge"]["status"] == "succeeded"]
    matrix = {gold: dict.fromkeys(VERDICTS, 0) for gold in VERDICTS}
    correct = total = 0
    disagreements = []
    for row in successful:
        predictions = {c["claim"]: c for c in row["judge"]["claims"]}
        for gold in row["gold_claims"]:
            predicted = predictions[gold["claim"]]
            matrix[gold["verdict"]][predicted["verdict"]] += 1
            total += 1
            correct += gold["verdict"] == predicted["verdict"]
            if gold["verdict"] != predicted["verdict"]:
                disagreements.append({"example_id": row["id"], "source_case_id": row["source_case_id"],
                    "claim": gold["claim"], "expected": gold["verdict"], "predicted": predicted["verdict"],
                    "reason": predicted["reason"]})
    per_verdict = {}
    for verdict in VERDICTS:
        tp = matrix[verdict][verdict]
        predicted_count = sum(matrix[g][verdict] for g in VERDICTS)
        gold_count = sum(matrix[verdict].values())
        per_verdict[verdict] = {"precision": tp / predicted_count if predicted_count else None,
            "recall": tp / gold_count if gold_count else None, "gold_count": gold_count}
    flawed = [r for r in successful if r["expected_requires_review"]]
    accurate = [r for r in successful if not r["expected_requires_review"]]
    caught = sum(r["judge"]["requires_review"] is True for r in flawed)
    false_alarms = sum(r["judge"]["requires_review"] is True for r in accurate)
    all_claims = sum(len(r["gold_claims"]) for r in rows)
    return {"examples": len(rows), "succeeded": len(successful), "failed": len(rows)-len(successful),
        "scored_claims": total, "total_claims": all_claims, "correct_claims": correct,
        "claim_accuracy_on_successes": correct / total if total else None,
        "correct_claim_fraction_all_attempts": correct / all_claims if all_claims else None,
        "confusion_matrix": matrix, "per_verdict": per_verdict,
        "flawed_drafts_caught": caught, "flawed_drafts_scored": len(flawed),
        "flawed_drafts_missed": len(flawed)-caught, "accurate_drafts_scored": len(accurate),
        "accurate_drafts_flagged": false_alarms, "disagreements": disagreements}


def write_report(data, path):
    def pct(value):
        return "unknown" if value is None else f"{value:.1%}"
    lines = ["# Judge batch evaluation", "", f"Run: {data['started_at']} (Africa/Cairo).",
        f"Model: `{data['model']}`; prompt: `{data['prompt_version']}`; temperature: 0; maximum output tokens: 3000.",
        "", "This is a blind classification test of synthetic X drafts. Only the source, draft, and unlabeled candidate claim strings were sent to the judge. Expected labels were withheld. Claim extraction was not tested.",
        "", f"Dataset SHA-256: `{data['dataset_sha256']}`; sources SHA-256: `{data['sources_sha256']}`.",
        "", "| Split | Examples | Completed | Failed | Correct claims / scored | Claim agreement | Correct / all attempted claims |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for split, summary in data["metrics"].items():
        lines.append(f"| {split} | {summary['examples']} | {summary['succeeded']} | {summary['failed']} | {summary['correct_claims']}/{summary['scored_claims']} | {pct(summary['claim_accuracy_on_successes'])} | {pct(summary['correct_claim_fraction_all_attempts'])} |")
    overall = data["metrics"]["all"]
    lines += ["", "## Error detection", "",
        f"Among completed evaluations: caught {overall['flawed_drafts_caught']}/{overall['flawed_drafts_scored']} flawed drafts; missed {overall['flawed_drafts_missed']}; falsely flagged {overall['accurate_drafts_flagged']}/{overall['accurate_drafts_scored']} accurate drafts.",
        "", "| Verdict | Precision | Recall | Reference claims scored |", "|---|---:|---:|---:|"]
    for verdict, values in overall["per_verdict"].items():
        lines.append(f"| {verdict} | {pct(values['precision'])} | {pct(values['recall'])} | {values['gold_count']} |")
    lines += ["", "## Confusion matrix", "", "Rows are reference verdicts; columns are judge predictions.", "",
        "| Reference | Supported | Contradicted | Unsupported |", "|---|---:|---:|---:|"]
    for verdict, counts in overall["confusion_matrix"].items():
        lines.append(f"| {verdict} | {counts['supported']} | {counts['contradicted']} | {counts['unsupported']} |")
    lines += ["", "## Execution", "", f"Elapsed wall time: {data['elapsed_seconds']:.2f} seconds; concurrency: {data['concurrency']}; no automatic retries.",
        f"Reported cost: ${data['reported_cost_usd']:.6f}, available for {data['runs_with_reported_cost']}/{len(data['results'])} calls. Missing cost is not zero, and failed-response usage may be unavailable.",
        f"Recorded tokens: {data['input_tokens']} input, {data['output_tokens']} output. Average successful-call latency: {data['average_latency_ms']} ms.",
        "", "## Disagreements", ""]
    for item in overall["disagreements"]:
        lines += [f"- `{item['example_id']}` (source {item['source_case_id']}): {item['claim']}",
            f"  Reference: **{item['expected']}**; judge: **{item['predicted']}**. Reason: {item['reason']}"]
    if not overall["disagreements"]:
        lines.append("No verdict disagreements among completed evaluations.")
    lines += ["", "## Failures", ""]
    failures = [r for r in data["results"] if r["judge"]["status"] != "succeeded"]
    lines.extend(f"- `{r['id']}`: {r['judge']['error']}" for r in failures)
    if not failures:
        lines.append("No evaluation failures.")
    lines += ["", "## Interpretation and limits", "",
        "This measures agreement with provisional, assistant-authored reference labels, not independently established accuracy. Review disagreements before changing either labels or prompts. Contradicted versus unsupported can be ambiguous.",
        f"These {len(data['results'])} drafts reuse claims from only {len({r['source_case_id'] for r in data['results']})} synthetic articles; observations are correlated. They are short X-format samples, not a representative benchmark of long LinkedIn posts or live user campaigns. One run per draft does not establish stability. Evidence substring checks verify quote presence, not semantic correctness.",
        "Development and held-out results are reported separately. The held-out set was inspected in the baseline review, so subsequent comparisons are not untouched confirmatory tests. New independently reviewed cases are required for that. No reference labels are sent to the judge.",
        "Next: review disagreements, add longer article/LinkedIn examples with independent labels, and test claim extraction separately. Passing software tests does not establish judge quality.", ""]
    path.write_text("\n".join(lines))


async def run(args):
    if not settings.openrouter_api_key:
        raise ValueError("OpenRouter is not configured")
    dataset_bytes = (ROOT / "judge_examples.json").read_bytes()
    source_bytes = (ROOT / "cases.json").read_bytes()
    examples = json.loads(dataset_bytes)
    if args.split != "all":
        examples = [example for example in examples if example["split"] == args.split]
    sources = {s["id"]: s for s in json.loads(source_bytes)}
    if not 1 <= args.concurrency <= 5:
        raise ValueError("Concurrency must be between 1 and 5")
    args.output.mkdir(parents=True, exist_ok=True)
    data = {"started_at": datetime.now(ZoneInfo("Africa/Cairo")).isoformat(),
        "model": settings.llm_model, "prompt_version": f"factuality-classification-{args.prompt_version}",
        "selected_split": args.split,
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "sources_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "concurrency": args.concurrency, "results": []}
    semaphore = asyncio.Semaphore(args.concurrency)
    start = perf_counter()

    async def evaluate(example):
        async with semaphore:
            try:
                judgement = await evaluate_draft(
                    source=sources[example['source_case_id']]['markdown'], draft=example['draft'],
                    candidate_claims=[claim['claim'] for claim in example['gold_claims']],
                    api_key=settings.openrouter_api_key, base_url=settings.openrouter_base_url,
                    model=settings.llm_model, timeout=settings.llm_timeout_seconds,
                    prompt_version=args.prompt_version,
                )
            except LLMError as exc:
                judgement = {"status": "failed", "error": str(exc)}
            row = {**example, "judge": judgement}
            data["results"].append(row)
            (args.output / "raw_results.json").write_text(json.dumps(data, indent=2) + "\n")
            print(f"{len(data['results'])}/{len(examples)} {example['id']}: {judgement['status']}", flush=True)
    await asyncio.gather(*(evaluate(example) for example in examples))
    data["elapsed_seconds"] = round(perf_counter()-start, 2)
    data["metrics"] = {split: metrics([r for r in data["results"] if split == "all" or r["split"] == split]) for split in ("all", "development", "holdout")}
    successes = [r['judge'] for r in data['results'] if r['judge']['status'] == 'succeeded']
    costs = [r['reported_cost_usd'] for r in successes if r.get('reported_cost_usd') is not None]
    data.update(reported_cost_usd=sum(costs), runs_with_reported_cost=len(costs),
        input_tokens=sum(r.get('input_tokens') or 0 for r in successes),
        output_tokens=sum(r.get('output_tokens') or 0 for r in successes),
        average_latency_ms=round(mean(r['latency_ms'] for r in successes)) if successes else None)
    (args.output / "raw_results.json").write_text(json.dumps(data, indent=2) + "\n")
    write_report(data, args.output / "REPORT.md")
    print(json.dumps(data["metrics"]["all"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--prompt-version", choices=("v1", "v2", "v3", "v4", "v5", "v6", "v7"), default="v2")
    parser.add_argument("--split", choices=("all", "development", "holdout"), default="all")
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))
