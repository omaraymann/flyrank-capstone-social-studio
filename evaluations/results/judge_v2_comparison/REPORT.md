# Judge batch evaluation

Run: 2026-10-09T23:47:16.367152+03:00 (Africa/Cairo).
Model: `google/gemini-2.5-flash`; prompt: `factuality-classification-v2`; temperature: 0; maximum output tokens: 3000.

This is a blind classification test of synthetic X drafts. Only the source, draft, and unlabeled candidate claim strings were sent to the judge. Expected labels were withheld. Claim extraction was not tested.

Dataset SHA-256: `5731ea2307e31ba68af8507b7ceeedfde4524ae714d85df1bcfee60877e17948`; sources SHA-256: `2670a1e9be25233145d013c350a4e825f88e4e27a68fc5c05441afa26f5255ab`.

| Split | Examples | Completed | Failed | Correct claims / scored | Claim agreement | Correct / all attempted claims |
|---|---:|---:|---:|---:|---:|---:|
| all | 35 | 3 | 32 | 5/5 | 100.0% | 7.6% |
| development | 9 | 2 | 7 | 4/4 | 100.0% | 28.6% |
| holdout | 26 | 1 | 25 | 1/1 | 100.0% | 1.9% |

## Error detection

Among completed evaluations: caught 1/1 flawed drafts; missed 0; falsely flagged 0/2 accurate drafts.

| Verdict | Precision | Recall | Reference claims scored |
|---|---:|---:|---:|
| supported | 100.0% | 100.0% | 3 |
| contradicted | 100.0% | 100.0% | 2 |
| unsupported | unknown | unknown | 0 |

## Confusion matrix

Rows are reference verdicts; columns are judge predictions.

| Reference | Supported | Contradicted | Unsupported |
|---|---:|---:|---:|
| supported | 3 | 0 | 0 |
| contradicted | 0 | 2 | 0 |
| unsupported | 0 | 0 | 0 |

## Execution

Elapsed wall time: 33.60 seconds; concurrency: 3; no automatic retries.
Reported cost: $0.001579, available for 3/35 calls. Missing cost is not zero, and failed-response usage may be unavailable.
Recorded tokens: 2221 input, 365 output. Average successful-call latency: 2165 ms.

## Disagreements

No verdict disagreements among completed evaluations.

## Failures

- `example-8da0365bf89897b9`: Judge provider request failed
- `example-287d06ca6f4cc69a`: Judge provider request failed
- `example-bd9c66b3ad3c2d6d`: Judge provider request failed
- `example-7412b29347294739`: Judge provider request failed
- `example-61b1cd2262801c45`: Judge provider request failed
- `example-18c267976142ea7d`: Judge provider request failed
- `example-ff5e9ff0ff50bde4`: Judge provider request failed
- `example-b7c93acfe059a0ee`: Judge provider request failed
- `example-11ce5dd2b45ed1f0`: Judge provider request failed
- `example-3f22faf823bed01d`: Judge provider request failed
- `example-4b0dbb418d5288f1`: Judge provider request failed
- `example-c17af08a1745d6d8`: Judge provider request failed
- `example-f50bea63371ecd7b`: Judge provider request failed
- `example-35a240ae5af30553`: Judge provider request failed
- `example-e27a984d654821d0`: Judge provider request failed
- `example-d7c524a55304317f`: Judge provider request failed
- `example-0b1f9163ce9ff57f`: Judge provider request failed
- `example-fc3e058be0f3eab0`: Judge provider request failed
- `example-b83cfe0be037e5ed`: Judge provider request failed
- `example-6123fdf77656af72`: Judge provider request failed
- `example-956269f0e5d7b875`: Judge provider request failed
- `example-e2817efdae849217`: Judge provider request failed
- `example-04fc6d827d154385`: Judge provider request failed
- `example-1b3dbd5ce9a1fa6f`: Judge provider request failed
- `example-448aaa9e66b2bc5b`: Judge provider request failed
- `example-a0a04dc427209bdf`: Judge provider request failed
- `example-4737819096da1dac`: Judge provider request failed
- `example-5fb8d16c2720797d`: Judge provider request failed
- `example-e0c53cb83da9c2a9`: Judge provider request failed
- `example-6c307511b2b9437a`: Judge provider request failed
- `example-392456de3eb13b90`: Judge provider request failed
- `example-baa80dd488bd6407`: Judge provider request failed

## Interpretation and limits

This measures agreement with provisional, assistant-authored reference labels, not independently established accuracy. Review disagreements before changing either labels or prompts. Contradicted versus unsupported can be ambiguous.
These 35 drafts reuse claims from only 10 synthetic articles; observations are correlated. They are short X-format samples, not a representative benchmark of long LinkedIn posts or live user campaigns. One run per draft does not establish stability. Evidence substring checks verify quote presence, not semantic correctness.
Development and held-out results are reported separately. The held-out set was inspected in the baseline review, so subsequent comparisons are not untouched confirmatory tests. New independently reviewed cases are required for that. No reference labels are sent to the judge.
Next: review disagreements, add longer article/LinkedIn examples with independent labels, and test claim extraction separately. Passing software tests does not establish judge quality.
