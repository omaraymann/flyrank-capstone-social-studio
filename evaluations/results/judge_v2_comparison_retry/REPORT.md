# Judge batch evaluation

Run: 2026-10-10T05:59:20.779901+03:00 (Africa/Cairo).
Model: `google/gemini-2.5-flash`; prompt: `factuality-classification-v2`; temperature: 0; maximum output tokens: 3000.

This is a blind classification test of synthetic X drafts. Only the source, draft, and unlabeled candidate claim strings were sent to the judge. Expected labels were withheld. Claim extraction was not tested.

Dataset SHA-256: `5731ea2307e31ba68af8507b7ceeedfde4524ae714d85df1bcfee60877e17948`; sources SHA-256: `2670a1e9be25233145d013c350a4e825f88e4e27a68fc5c05441afa26f5255ab`.

| Split | Examples | Completed | Failed | Correct claims / scored | Claim agreement | Correct / all attempted claims |
|---|---:|---:|---:|---:|---:|---:|
| all | 35 | 34 | 1 | 64/64 | 100.0% | 97.0% |
| development | 9 | 9 | 0 | 14/14 | 100.0% | 100.0% |
| holdout | 26 | 25 | 1 | 50/50 | 100.0% | 96.2% |

## Error detection

Among completed evaluations: caught 24/24 flawed drafts; missed 0; falsely flagged 0/10 accurate drafts.

| Verdict | Precision | Recall | Reference claims scored |
|---|---:|---:|---:|
| supported | 100.0% | 100.0% | 33 |
| contradicted | 100.0% | 100.0% | 16 |
| unsupported | 100.0% | 100.0% | 15 |

## Confusion matrix

Rows are reference verdicts; columns are judge predictions.

| Reference | Supported | Contradicted | Unsupported |
|---|---:|---:|---:|
| supported | 33 | 0 | 0 |
| contradicted | 0 | 16 | 0 |
| unsupported | 0 | 0 | 15 |

## Execution

Elapsed wall time: 107.98 seconds; concurrency: 1; no automatic retries.
Reported cost: $0.021254, available for 34/35 calls. Missing cost is not zero, and failed-response usage may be unavailable.
Recorded tokens: 25570 input, 5433 output. Average successful-call latency: 2255 ms.

## Disagreements

No verdict disagreements among completed evaluations.

## Failures

- `example-d7c524a55304317f`: Judge provider request failed

## Interpretation and limits

This measures agreement with provisional, assistant-authored reference labels, not independently established accuracy. Review disagreements before changing either labels or prompts. Contradicted versus unsupported can be ambiguous.
These 35 drafts reuse claims from only 10 synthetic articles; observations are correlated. They are short X-format samples, not a representative benchmark of long LinkedIn posts or live user campaigns. One run per draft does not establish stability. Evidence substring checks verify quote presence, not semantic correctness.
Development and held-out results are reported separately. The held-out set was inspected in the baseline review, so subsequent comparisons are not untouched confirmatory tests. New independently reviewed cases are required for that. No reference labels are sent to the judge.
Next: review disagreements, add longer article/LinkedIn examples with independent labels, and test claim extraction separately. Passing software tests does not establish judge quality.
