# Prompt evaluation: first baseline

This is a small, human-reviewed quality evaluation, separate from the fake-provider software tests in `tests/test_phase_six.py`. Those tests prove code behavior; they do not measure real model writing quality.

All articles in `cases.json` are synthetic test content, not claims about actual businesses or research. No model calls occur when these files are read.

## Automatic judge benchmark

`judge_examples.json` contains a randomized pool linked to the 10 source articles. The current seed produces 35 shuffled drafts with 66 labeled claim occurrences. There is no fixed accurate/flawed pairing: each article gets 2–5 drafts, each containing 1–3 randomly sampled claims. Drafts can be entirely supported, entirely flawed, or mixtures of supported, contradicted, and unsupported claims. Neutral example IDs do not reveal their expected outcome. Labels are an initial reference to review, not model-generated judgments or independently reviewed ground truth.

`claim_pool.json` stores the curated candidate claims and their reference labels. `randomize_pool.py` samples their combinations and shuffles the result. Randomization changes which claims appear together; it does not randomly assign truth labels or invent new facts. The assembled drafts are synthetic benchmark samples, not live model outputs or an estimate of production error rates.

Rebuild the same pool with:

```sh
python3 evaluations/randomize_pool.py --seed 42
```

To create a different pool without replacing the comparison benchmark:

```sh
python3 evaluations/randomize_pool.py --seed 123 --output /tmp/judge_examples_123.json
```

Keep the same pool and seed when comparing judge versions, so a changed sample does not distort the comparison.

The examples cover correct paraphrases, a valid percentage calculation, wrong numbers, invented benefits, exaggerated certainty, missing evidence, reversed limitations, and instructions embedded in source text. All drafts fit the app's X character limit and include their requested CTA so simple formatting failures do not obscure the factuality benchmark.

Each example stores:

- `source_case_id`: the article to retrieve from `cases.json`.
- `draft`: the candidate social post.
- `gold_claims`: expected supported, contradicted, or unsupported verdicts, with exact source excerpts where applicable.
- `expected_requires_review`: whether any claim is unsupported or contradicted.
- `expected_supported_claim_rate`: the supported fraction of the curated claims, between 0 and 1. This is source agreement, not real-world truth or a universal accuracy score.

First implement a classification benchmark: give the judge the article, draft, and candidate claim strings, while hiding all expected verdicts, excerpts, review decisions, rates, and split metadata. The candidate claims make the classification comparison deterministic. A later end-to-end benchmark should let the judge extract claims itself; that needs semantic alignment and separate measurement of missed or invented claims. Do not compare claim counts alone or reward a judge for skipping difficult claims.

Measure:

1. Per-verdict precision and recall: can the judge detect unsupported/contradicted claims without falsely accusing supported claims?
2. Draft review decisions: how often does it correctly flag flawed drafts, and how often does it incorrectly flag accurate drafts?
3. Quote validity and response schema: are excerpts present in the source and are the verdicts valid? Quote presence alone does not prove the interpretation is correct.
4. Evaluation failures, judge cost, and latency: count invalid or failed responses explicitly; never treat them as passing evaluations.

Keep all drafts from the same article in the same split. The current seed produces nine development examples and twenty-six held-out examples. Use development cases to tune the judge instructions; reserve held-out cases for a comparison after tuning. The original held-out results have already been inspected during baseline review, so this tuning comparison is not an untouched validation set. Do not put held-out examples into either generation or judge prompts. Expand this small synthetic benchmark with reviewed, representative articles before relying on the judge in production.

The synthetic pool is ready. `judge.py` implements an experimental LLM judge, `run_trial.py` runs a small live demonstration on the article excerpt/tweet pair, and `run_batch.py` runs a blind classification benchmark against the randomized pool.

## Batch baseline and report

```sh
python -m evaluations.run_batch --prompt-version v2 --concurrency 3 --output /tmp/judge_batch_run
```

This makes one provider request per draft, with no automatic retries. The judge receives only source text, draft, and candidate claim strings; reference labels and metadata remain local. Its response must classify each supplied claim exactly once. This mode measures classification, not claim extraction. Costs may be incurred through the configured OpenRouter account.

Each run saves `raw_results.json` with predictions and reference labels, and `REPORT.md` with split-level agreement, per-verdict precision/recall, confusion matrix, draft review decisions, disagreements, failures, tokens, available cost, and latency. Failed calls remain in the report and are excluded from scored-only metrics, with an all-attempts denominator reported separately.

The completed October 9 baseline is in [results/batch_baseline_2026-10-09/REPORT.md](results/batch_baseline_2026-10-09/REPORT.md). All 35 calls completed, 60/66 claim verdicts agreed with the reference labels, and all 25 flawed drafts were flagged without flagging the ten accurate drafts. The six disagreements were unsupported-versus-contradicted distinctions. This is agreement with provisional synthetic labels, not independently measured real-world judge accuracy.

## Published-sample live trial

Using a Python 3.11+ environment with the project's dependencies and configured OpenRouter key:

```sh
python -m evaluations.run_trial --output /tmp/published_sample_trial.json
```

This performs one generation request for X/LinkedIn, followed by three judge requests (the published reference tweet and both generated drafts). It fetches the public sample from `https://arjungambhir.github.io/Domain_Specific_tweet_generation/`. It does not have access to the reported 70,000-pair collection or a verified full original article. The report preserves the displayed source, its hash, drafts, prompt/model settings, first-pass rule/CTA results, judgments, available usage and cost, and latency. It does not publish posts or change production prompts.

`judge.py` sends only source and draft to the model. Python validates the schema, checks extracted claim spans against the draft, rejects duplicate claim strings, and verifies evidence excerpts occur in the supplied source. Unsupported claims can lack evidence. A draft with no extracted factual claims gets an unknown rate, not a perfect score. These structural checks do not establish that the judge correctly interpreted the article or extracted all claims.

The October 9 trial is saved in `results/published_sample_trial.json`. It uses the same Gemini model for generation and judging, so agreement may reflect correlated errors. A locally injected numeric error is recorded as a separate control, clearly distinguished from the published data. The trial demonstrates execution and error detection, not benchmark accuracy or independent factual correctness.

## Run the baseline in the dashboard

1. Start with case `01`. Copy its title and article into the composer.
2. Select X and LinkedIn, select LLM generation, and copy the case's audience, goal, tone, and call to action.
3. Generate once. Record any failure; do not silently discard it or retry until a nicer result appears.
4. Save the final draft text and the generation audit: model, prompt version, example version, repairs, tokens, available cost, and latency.
5. Score each platform draft with the rubric below and note any unsupported claims. The listed facts are a reference for review; not every short draft must contain every fact.
6. Repeat for the other cases. Model calls require a configured provider key and may incur cost.

Use one record per case/platform/run, including failed runs. Suggested fields:

```text
case_id, platform, run_number, model, prompt_version, examples_version,
temperature, top_p, top_k, outcome, content, rules_pass, cta_pass,
fidelity_score, audience_score, tone_score, usefulness_score,
unsupported_claims, repairs, input_tokens, output_tokens,
reported_cost_usd, latency_ms, notes
```

## What to score

| Check | Scoring |
|---|---|
| Platform rules | Pass/fail using the application's character, hashtag, empty-text, and tone rules. These are the app's rules, not a complete platform specification. |
| CTA | Pass/fail: the exact requested CTA appears, including case. The existing backend check is case-insensitive even though the system prompt requests verbatim inclusion. |
| Source fidelity | 0 = invented or contradictory claims; 1 = misleading omission or exaggeration; 2 = accurate representation of the source. |
| Audience fit | 0 = unsuitable; 1 = generic; 2 = clearly appropriate for the specified audience. |
| Requested tone | 0 = wrong tone; 1 = mixed; 2 = consistently appropriate. |
| Usefulness | 0 = confusing or unusable; 1 = needs meaningful edits; 2 = clear and ready for human approval. |

Check unsupported claims manually. Simple keyword matching cannot establish factual accuracy. Evaluate whether X and LinkedIn use meaningfully different structures, rather than merely different wording. Record delivery failures and generation failures separately from quality scores.

Compare first-pass success and repair counts as well as final output: the service may have repaired a draft before it reaches the dashboard. Current audit data does not preserve the original invalid text, so first-pass quality cannot be fully inspected from the dashboard.

## Improve and compare

- Cases `01`–`03` are development cases. Use their failures to decide what instructions and examples to improve.
- Cases `04`–`10` are held-out cases. Do not copy their articles or expected drafts into prompt examples or tune repeatedly against them.
- Create separate source/instruction/output examples covering the missing patterns. Keep the prompt's platform and CTA rules consistent with the examples.
- Increment `PROMPT_VERSION` and/or `EXAMPLES_VERSION` when changing the prompt or examples.
- Keep model, temperature, top-p, top-k, and token limits fixed while comparing prompt versions. Change one factor at a time.
- Run both versions on the same held-out cases. Repeat runs if the initial comparison looks promising: a single output per case is a noisy baseline.
- Report all runs, failures, unsupported claims, quality scores, repair counts, available cost, and latency. Distinguish missing cost from zero.

Ten source cases provide an initial debugging benchmark, not proof of general quality. The judge batch baseline and one published-sample generation trial have been collected. Production generation prompts and sampling settings have not been changed.

## Judge tuning v2

Judge v2 explicitly separates missing evidence from direct contradiction, with two development-source examples. Generation prompts and sampling settings are unchanged. Original v1 remains selectable with `--prompt-version v1`; use a separate output directory for every run. See [results/JUDGE_TUNING_REPORT.md](results/JUDGE_TUNING_REPORT.md) for development results, comparison attempts, and limitations.

## Extraction and evidence audit (v7)

The default extraction-mode judge now uses two stages: Flash identifies factual spans and explicitly labels non-factual text; Python excludes those items from scores while preserving them for audit. A focused Gemini Pro call checks each retained span's precise scope and qualifiers. It cites numbered source passages, which Python resolves into exact source text. Citation validity does not establish that the passage supports the interpretation. Configure its model with `JUDGE_AUDIT_MODEL`; the generator model remains unchanged. Costs, tokens and latency are aggregated across successful stages, and both responses are retained. If the audit fails, the initial extraction verdict is not returned as a passing evaluation. Missing usage stays unknown.

Prepared-claim classification mode makes a single call using its supplied model; it does not measure this extraction pipeline. Old versions remain selectable. These experimental scripts do not add judge results to the dashboard.

```sh
python -m evaluations.run_small_review --prompt-version v7 --output /tmp/new_small_review
```

The original six-draft baseline and each tuning attempt are preserved in separate result directories. See [the comparison report](results/small_user_drafts_v7_2026-10-11/REPORT.md). This set has been used for tuning and cannot serve as independent validation.
