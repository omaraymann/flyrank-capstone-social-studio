# Judge batch evaluation

Run: 2026-10-09T23:46:03.482238+03:00 (Africa/Cairo).
Model: `google/gemini-2.5-flash`; prompt: `factuality-classification-v2`; temperature: 0; maximum output tokens: 3000.

This is a blind classification test of synthetic X drafts. Only the source, draft, and unlabeled candidate claim strings were sent to the judge. Expected labels were withheld. Claim extraction was not tested.

Dataset SHA-256: `5731ea2307e31ba68af8507b7ceeedfde4524ae714d85df1bcfee60877e17948`; sources SHA-256: `2670a1e9be25233145d013c350a4e825f88e4e27a68fc5c05441afa26f5255ab`.

| Split | Examples | Completed | Failed | Correct claims / scored | Claim agreement | Correct / all attempted claims |
|---|---:|---:|---:|---:|---:|---:|
| all | 9 | 9 | 0 | 14/14 | 100.0% | 100.0% |
| development | 9 | 9 | 0 | 14/14 | 100.0% | 100.0% |
| holdout | 0 | 0 | 0 | 0/0 | unknown | unknown |

## Error detection

Among completed evaluations: caught 4/4 flawed drafts; missed 0; falsely flagged 0/5 accurate drafts.

| Verdict | Precision | Recall | Reference claims scored |
|---|---:|---:|---:|
| supported | 100.0% | 100.0% | 9 |
| contradicted | 100.0% | 100.0% | 3 |
| unsupported | 100.0% | 100.0% | 2 |

## Confusion matrix

Rows are reference verdicts; columns are judge predictions.

| Reference | Supported | Contradicted | Unsupported |
|---|---:|---:|---:|
| supported | 9 | 0 | 0 |
| contradicted | 0 | 3 | 0 |
| unsupported | 0 | 0 | 2 |

## Execution

Elapsed wall time: 5.95 seconds; concurrency: 3; no automatic retries.
Reported cost: $0.004909, available for 9/9 calls. Missing cost is not zero, and failed-response usage may be unavailable.
Recorded tokens: 6704 input, 1159 output. Average successful-call latency: 1905 ms.

## Disagreements

No verdict disagreements among completed evaluations.

## Failures

No evaluation failures.

## Interpretation and limits

This measures agreement with provisional, assistant-authored reference labels, not independently established accuracy. Review disagreements before changing either labels or prompts. Contradicted versus unsupported can be ambiguous.
These 9 drafts reuse claims from only 3 synthetic articles; observations are correlated. They are short X-format samples, not a representative benchmark of long LinkedIn posts or live user campaigns. One run per draft does not establish stability. Evidence substring checks verify quote presence, not semantic correctness.
Development and held-out results are reported separately. The held-out set was inspected in the baseline review, so subsequent comparisons are not untouched confirmatory tests. New independently reviewed cases are required for that. No reference labels are sent to the judge.
Next: review disagreements, add longer article/LinkedIn examples with independent labels, and test claim extraction separately. Passing software tests does not establish judge quality.
