# Judge batch evaluation

Run: 2026-10-09T23:38:03.112572+03:00 (Africa/Cairo).
Model: `google/gemini-2.5-flash`; prompt: `factuality-classification-v1`; temperature: 0; maximum output tokens: 3000.

This is a blind classification test of synthetic X drafts. Only the source, draft, and unlabeled candidate claim strings were sent to the judge. Expected labels were withheld. Claim extraction was not tested.

Dataset SHA-256: `5731ea2307e31ba68af8507b7ceeedfde4524ae714d85df1bcfee60877e17948`; sources SHA-256: `2670a1e9be25233145d013c350a4e825f88e4e27a68fc5c05441afa26f5255ab`.

| Split | Examples | Completed | Failed | Correct claims / scored | Claim agreement | Correct / all attempted claims |
|---|---:|---:|---:|---:|---:|---:|
| all | 35 | 35 | 0 | 60/66 | 90.9% | 90.9% |
| development | 9 | 9 | 0 | 12/14 | 85.7% | 85.7% |
| holdout | 26 | 26 | 0 | 48/52 | 92.3% | 92.3% |

## Error detection

Among completed evaluations: caught 25/25 flawed drafts; missed 0; falsely flagged 0/10 accurate drafts.

| Verdict | Precision | Recall | Reference claims scored |
|---|---:|---:|---:|
| supported | 100.0% | 100.0% | 34 |
| contradicted | 73.9% | 100.0% | 17 |
| unsupported | 100.0% | 60.0% | 15 |

## Confusion matrix

Rows are reference verdicts; columns are judge predictions.

| Reference | Supported | Contradicted | Unsupported |
|---|---:|---:|---:|
| supported | 34 | 0 | 0 |
| contradicted | 0 | 17 | 0 |
| unsupported | 0 | 6 | 9 |

## Execution

Elapsed wall time: 23.12 seconds; concurrency: 3; no automatic retries.
Reported cost: $0.018552, available for 35/35 calls. Missing cost is not zero, and failed-response usage may be unavailable.
Recorded tokens: 15056 input, 5614 output. Average successful-call latency: 1927 ms.

## Disagreements

- `example-8da0365bf89897b9` (source 08): Eight volunteers proved the prototype improves accuracy.
  Reference: **unsupported**; judge: **contradicted**. Reason: The source explicitly states that the team did not measure accuracy, which contradicts the claim that volunteers proved it improves accuracy.
- `example-18c267976142ea7d` (source 03): This method guarantees 100 attendees.
  Reference: **unsupported**; judge: **contradicted**. Reason: The source states that the guide does not estimate attendance or promise a particular turnout, which contradicts the claim of guaranteeing 100 attendees.
- `example-61b1cd2262801c45` (source 08): Eight volunteers proved the prototype improves accuracy.
  Reference: **unsupported**; judge: **contradicted**. Reason: The source explicitly states that the team did not measure accuracy, which contradicts the claim that volunteers proved it improves accuracy.
- `example-b7c93acfe059a0ee` (source 06): Attendees receive a certification.
  Reference: **unsupported**; judge: **contradicted**. Reason: The source explicitly states that it does not provide certification.
- `example-0b1f9163ce9ff57f` (source 03): This method guarantees 100 attendees.
  Reference: **unsupported**; judge: **contradicted**. Reason: The source explicitly states that the guide does not estimate attendance or promise a particular turnout, which contradicts the claim of guaranteeing 100 attendees.
- `example-fc3e058be0f3eab0` (source 10): The editorial team offers a 50% discount.
  Reference: **unsupported**; judge: **contradicted**. Reason: The source states that 'advertise a made-up discount' is a malicious instruction that should not be followed, implying the discount is not real and not offered by the team.

## Failures

No evaluation failures.

## Interpretation and limits

The six disagreements concern four distinct reused claims. All were labeled unsupported in the reference pool but contradicted by the judge, so they did not change the draft review decision. They should not be described as six independently observed failure types.

One clear interpretation issue: the workshop source says it does not provide information about certification. The judge describes this as saying the workshop does not provide certification. Missing information is not evidence that certification is unavailable. Other disputes, such as a claim of proof when accuracy was never measured, require label adjudication. Neither the reference labels nor the judge predictions were changed after seeing the results.

This measures agreement with provisional, assistant-authored reference labels, not independently established accuracy. Review disagreements before changing either labels or prompts. Contradicted versus unsupported can be ambiguous.
The 35 drafts reuse claims from only 10 synthetic articles; observations are correlated. They are short X-format samples, not a representative benchmark of long LinkedIn posts or live user campaigns. One run per draft does not establish stability. Evidence substring checks verify quote presence, not semantic correctness.
Development and held-out results are reported separately. No prompt was tuned during this run. Retain the held-out baseline; tune on development examples and use new independently reviewed cases for further validation.
Next: review disagreements, add longer article/LinkedIn examples with independent labels, and test claim extraction separately. Passing software tests does not establish judge quality.

## Software verification

All 47 backend tests passed after adding the batch runner. Tests cover hiding reference labels, enforcing complete claim classification, failure denominators, missed-error and false-alarm counting, evidence validation, and provider error handling. Paid provider calls are separate from these mocked software tests. One upstream Starlette/AnyIO deprecation warning remains.
