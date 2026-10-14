# Judge tuning report: v1 to v2

The experimental judge now distinguishes missing evidence from direct contradiction. Contradicted requires an incompatible source assertion about the same subject, time, and scope. Unsupported covers claims lacking evidence, including unproven benefits or guarantees. Two development-source examples clarify this distinction. Compound claims get explicit decision rules.

Only judge instructions changed. Production generation prompts, model settings, benchmark articles, and reference labels stayed unchanged. Original v1 remains available through `--prompt-version v1`.

| Measure | Baseline v1 | Tuned v2 retry |
|---|---:|---:|
| Completed drafts | 35/35 | 34/35 |
| Development claim agreement | 12/14 | 14/14 |
| Agreement on completed claims | 60/66 (90.9%) | 64/64 (100%) |
| Correct / all attempted claims | 60/66 | 64/66 (97.0%) |
| Unsupported recall | 9/15 | 15/15 |
| Flawed drafts flagged | 25/25 | 24/24 completed; 1 failed |
| Accurate drafts falsely flagged | 0/10 | 0/10 |

On the same 34 completed drafts, baseline agreement was 58/64 and v2 agreement was 64/64. All six baseline disagreements were corrected; no scored claim regressed.

## Run history and failures

The separate development run completed 9/9 drafts, with 14/14 matching claims. The v2 prompt was frozen before the full comparison. The first full attempt completed only 3/35 drafts, with 32 provider request failures. It is preserved. An explicit retry with concurrency 1 completed 34/35, with one provider request failure. Failed evaluations are not passes and are excluded from scored-only agreement while remaining in all-attempt metrics. No failed result was silently replaced.

## Settings and cost

Model: `google/gemini-2.5-flash`. Both versions use temperature 0, max_tokens 3000, and strict structured output. Baseline concurrency was 3; retry concurrency was 1, so latency is not a controlled comparison.

Dataset SHA-256: `5731ea2307e31ba68af8507b7ceeedfde4524ae714d85df1bcfee60877e17948`.
Sources SHA-256: `2670a1e9be25233145d013c350a4e825f88e4e27a68fc5c05441afa26f5255ab`.

Reported cost: baseline $0.018552; development $0.004909; retry $0.021254, with cost available for 34 completed calls. Failed-call cost is unknown, not zero. The failed first attempt preserves its available usage separately.

## Interpretation and verification

This is agreement with provisional assistant-authored labels on short synthetic drafts from ten sources, with repeated claims. It is not independent production accuracy. Original holdout results were inspected during baseline review, so this comparison is not untouched validation. The test classifies supplied claim spans; it does not measure automatic claim extraction. Next validation needs fresh, independently reviewed examples.

All 48 software tests passed, including hidden labels and version metadata for both prompts, evidence validation, candidate-claim coverage, and failure-aware metrics. One dependency deprecation warning remains.

## Evidence

- [Baseline](batch_baseline_2026-10-09/REPORT.md)
- [Development](judge_v2_development/REPORT.md)
- [Failed first comparison](judge_v2_comparison/REPORT.md)
- [Comparison retry](judge_v2_comparison_retry/REPORT.md)

Reproduce into a new directory:

```sh
python -m evaluations.run_batch --prompt-version v2 --split all --concurrency 1 --output /tmp/judge_v2_new_run
```
