# Judge extraction and evidence audit fix

The six user-pasted drafts and source articles are unchanged. Version v7 is the default experimental extraction-mode judge. It uses Flash to separate non-factual spans from facts, excludes non-factual spans in Python while retaining them for audit, and sends only retained spans to a focused Gemini Pro evidence audit. The audit references numbered source passages; Python resolves IDs into exact quotes. Initial extraction judgments never override the audit outcome. Failures do not become passes.

Generator prompts were not changed in this fix. The judge remains an evaluation script, not a dashboard feature. Its audit model can be set with `JUDGE_AUDIT_MODEL`. Old judge versions are retained.

## Live results

| Draft | Final factual spans | Unsupported | Excluded non-factual spans | Review |
|---|---:|---:|---:|---|
| library / x | 2 | 0 | 2 | False |
| library / linkedin | 4 | 1 | 2 | True |
| library / discord | 4 | 1 | 3 | True |
| notenest / x | 3 | 1 | 2 | True |
| notenest / linkedin | 5 | 1 | 3 | True |
| notenest / discord | 4 | 1 | 2 | True |

Completed: 6/6 drafts. Reported cost across both stages: $0.101972. Average two-stage latency: 16.5 seconds. This is more costly and slower than the previous single Flash call. Each stage, its model, usage, cost and output is preserved in raw_results.json.

## What improved

- “Get ready!” and “Exciting news” are excluded from factuality scores, eliminating the two observed non-factual false warnings.
- NoteNest X’s “offline access” is now unsupported: the source only excludes offline collaboration. The supported mobile limitation does not make the whole compound statement supported.
- Unsupported recency claims (“recently concluded”, “just finished”) are identified in the library LinkedIn and Discord posts.
- NoteNest Discord’s “first version” is flagged because the source only describes this release, without release history. Its compound wording is flagged but the final reasoning emphasizes release history, not all scope problems.
- The user-corrected library uncertainty sentence remains supported, rather than being treated as a definite causal assertion.
- The final audit no longer writes its own evidence excerpts; validated IDs select exact source passages. A correct citation alone still does not prove entailment.

## Remaining limits

The strict audit marks NoteNest LinkedIn’s “invaluable in shaping” feedback claim unsupported as an exaggeration. “Invaluable” can also be read as subjective promotion, so this is a potential remaining false warning in a mixed opinion/fact sentence and requires human review. Standalone opinion filtering is verified on this run; all mixed wording is not solved. The model also accepts “initial release” while flagging “first version”, so release-history interpretation remains inconsistent.

No overall accuracy percentage is reported. There is no complete independent atomic-claim reference set, and these six drafts were used to tune the judge. Claim extraction can still omit facts or misclassify opinions. Fresh reviewed examples and factual-error controls are needed for general validation.

## All tuning attempts preserved

| Version | Completed drafts | Change / observation | Reported cost on completed drafts |
|---|---:|---|---:|
| v3 | 6/6 | Additional instructions alone: false warnings persisted. | $0.007465 |
| v4 | 6/6 | Explicit non-factual schema: standalone false warnings removed; scope missed. | $0.008045 |
| v5 | 6/6 | Two Flash stages: scope still missed. | $0.015225 |
| v6 | 4/6 | Pro evidence audit: scope detected; two exact-quote validation failures. | $0.052413 |
| v7 | 6/6 | Pro audit with source-passage IDs: all six completed. | $0.101972 |

Failed-call costs and successful first-stage costs lost on a subsequent failure are not completely captured by the error records; the aggregate is therefore incomplete for failed attempts, not zero. No attempt was silently replaced. All attempts are tuning evidence, not independent validation.

## Software validation

59 pytest tests passed, with one dependency deprecation warning. Tests cover non-factual exclusion, preserving real errors inside promotional text, unknown/no-claims scores, two-stage verdict precedence and summed usage, candidate coverage, invalid evidence IDs, and failures in the second stage. These fake-provider tests verify software behavior, not model semantics.

## Final claims and reasoning

### library / x

Brookfield Library's 6-week trial of longer opening hours saw average weekly visits rise from 800 to 1,000. Two community events were also held during this period. Read the trial summary. #BrookfieldLibrary #Community

- **supported**: Brookfield Library's 6-week trial of longer opening hours saw average weekly visits rise from 800 to 1,000.
  Reason: The source confirms the duration of the trial was six weeks and states, "During the trial, average weekly visits increased from 800 to 1,000".
- **supported**: Two community events were also held during this period.
  Reason: The source explicitly states, "The library also held two community events during this period".

### library / linkedin

Brookfield Library recently concluded a six-week trial of extended opening hours. During this period, the library observed an increase in average weekly visits from 800 to 1,000. It is noted that two community events were also hosted during the trial, which may have contributed to the increased visitation. The library has not yet made a decision regarding the permanence of the new hours. Read the trial summary. #BrookfieldLibrary #CommunityEngagement #LibraryServices

- **unsupported**: Brookfield Library recently concluded a six-week trial of extended opening hours.
  Reason: The source confirms a six-week trial of longer hours but does not state that it "recently concluded." The timing of the trial is not mentioned.
- **supported**: During this period, the library observed an increase in average weekly visits from 800 to 1,000.
  Reason: The source explicitly states that during the trial, "average weekly visits increased from 800 to 1,000".
- **supported**: It is noted that two community events were also hosted during the trial, which may have contributed to the increased visitation.
  Reason: The source states that two community events were held and that staff "cannot determine whether longer hours alone caused the increase," which implies the events may have been a contributing factor.
- **supported**: The library has not yet made a decision regarding the permanence of the new hours.
  Reason: The source directly states, "The library has not decided whether to make the new hours permanent."

### library / discord

Hey everyone! Brookfield Library just finished a 6-week trial with longer opening hours. We saw average weekly visits go up from 800 to 1,000! Just a heads up, we also had two community events during that time, so we're not sure if the longer hours were the only reason for the boost. No decisions yet on making the new hours permanent. Read the trial summary. #BrookfieldLibrary #LocalCommunity #LibraryNews

- **unsupported**: Brookfield Library just finished a 6-week trial with longer opening hours.
  Reason: The source confirms a six-week trial of longer hours but does not state when it concluded, so the claim that it "just finished" is not supported.
- **supported**: We saw average weekly visits go up from 800 to 1,000!
  Reason: The source explicitly states that during the trial, "average weekly visits increased from 800 to 1,000".
- **supported**: Just a heads up, we also had two community events during that time, so we're not sure if the longer hours were the only reason for the boost.
  Reason: The source states that the library held two community events and that "staff cannot determine whether longer hours alone caused the increase," which aligns with the claim's uncertainty.
- **supported**: No decisions yet on making the new hours permanent.
  Reason: The source directly states, "The library has not decided whether to make the new hours permanent."

### notenest / x

NoteNest desktop beta users, get ready! Shared folders are here. Invite up to 5 collaborators to view and edit notes. Offline and mobile access are not included in this release. Explore the update #NoteNest #SharedFolders

- **supported**: Shared folders are here.
  Reason: The source states that NoteNest "has introduced shared folders for its existing desktop beta users."
- **supported**: Invite up to 5 collaborators to view and edit notes.
  Reason: The source states, "Folder owners can invite up to five collaborators, who can view and edit notes."
- **unsupported**: Offline and mobile access are not included in this release.
  Reason: The source states that "Offline collaboration" is not included, which is more specific than the claim's "Offline access". The source does not rule out other forms of offline access, such as viewing notes.

### notenest / linkedin

Exciting news for NoteNest desktop beta users! We're rolling out shared folders, a new feature designed to enhance collaboration. Folder owners can now invite up to five collaborators to view and edit notes within shared folders. This initial release focuses on desktop functionality, with offline collaboration and mobile access not yet available. Your feedback as beta users will be invaluable in shaping future updates. Explore the update #NoteNest #ProductUpdate #Collaboration #BetaFeatures

- **supported**: We're rolling out shared folders, a new feature designed to enhance collaboration.
  Reason: The source states that NoteNest "has introduced shared folders for its existing desktop beta users" (passage 0) and that these folders allow owners to invite collaborators to view and edit notes (passage 1), which is a collaborative function.
- **supported**: Folder owners can now invite up to five collaborators to view and edit notes within shared folders.
  Reason: The source explicitly states, "Folder owners can invite up to five collaborators, who can view and edit notes."
- **supported**: This initial release focuses on desktop functionality
  Reason: The source states the feature has been introduced "for its existing desktop beta users" and passage 2 confirms "mobile access" is not included, thereby establishing the focus on desktop functionality.
- **supported**: with offline collaboration and mobile access not yet available.
  Reason: The source directly states, "Offline collaboration and mobile access are not included in this release," which means they are not yet available.
- **unsupported**: Your feedback as beta users will be invaluable in shaping future updates.
  Reason: The source says, "Feedback from beta users will help inform future updates." The claim's wording "invaluable in shaping" is an exaggeration; the source does not state the feedback will be "invaluable" or that it will "shape" updates, only that it will "help inform" them.

### notenest / discord

Hey NoteNest desktop beta users! We've got a cool new update for you: shared folders are here! 🎉 You can now invite up to 5 friends or teammates to view and edit notes together. Just a heads-up, this first version is for desktop only, so no offline or mobile access yet. We're really keen to hear what you think, as your feedback will help us make it even better. Explore the update

- **supported**: shared folders are here!
  Reason: The source states that NoteNest "has introduced shared folders for its existing desktop beta users."
- **supported**: You can now invite up to 5 friends or teammates to view and edit notes together.
  Reason: The source states: "Folder owners can invite up to five collaborators, who can view and edit notes."
- **unsupported**: Just a heads-up, this first version is for desktop only, so no offline or mobile access yet.
  Reason: The source refers to "this release" but does not explicitly state that it is the "first version" of the feature. While other parts of the claim are supported, this specific assertion is not present in the source text.
- **supported**: We're really keen to hear what you think, as your feedback will help us make it even better.
  Reason: The source states, "Feedback from beta users will help inform future updates," which supports the claim that feedback will be used for improvements.
