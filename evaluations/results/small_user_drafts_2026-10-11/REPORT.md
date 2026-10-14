# Small end-to-end judge review

Six exact user-pasted generated posts, from two fresh fictional sources, evaluated with judge v2. The judge received only source and draft; no candidate claims, expected verdicts, or manual notes. No regeneration, automatic retries, or prompt changes were made. Manual reference notes were saved before the calls.

| Source | Platform | Extracted spans | Supported | Review flag |
|---|---|---:|---:|---|
| library | x | 2 | 2 | False |
| library | linkedin | 4 | 4 | False |
| library | discord | 4 | 4 | False |
| notenest | x | 4 | 3 | True |
| notenest | linkedin | 5 | 4 | True |
| notenest | discord | 4 | 4 | False |

Completed calls: 6/6. Extracted spans: 23. Provider-reported cost: $0.006824. All returned claim spans and source excerpts passed exact-substring validation. This confirms structure and quote presence, not correctness of interpretation.

## Findings

- Two clear extraction errors: NoteNest X included “NoteNest desktop beta users, get ready!” and NoteNest LinkedIn included “Exciting news for NoteNest desktop beta users!” as unsupported claims. Their reasons explicitly describe an exclamation or subjective opinion. These should have been ignored according to the judge instructions, and each caused a review flag.
- The judge accepted the library Discord uncertainty sentence. Consistent with the user correction, this wording is ambiguous rather than a definitive causal error; it is not scored as a missed factual error.
- The judge treated the possible contribution of community events as supported. This is a reasonable tentative interpretation, rather than a causal finding.
- The judge did not distinguish offline access from offline collaboration in the NoteNest X and Discord drafts. The source only excludes collaboration offline; the broader wording merits review.
- Fine qualifiers were not carefully assessed: recently/just finished imply recency; initial/first version implies release history. These details are not explicitly established by the sources. Compound extraction grouped some of these with supported statements.

## Interpretation

There is no defensible overall accuracy percentage for this run: reference notes include ambiguous wording and do not contain a complete independently labeled atomic claim list or semantic claim alignment. The returned supported-claim rates are model judgments, not measured accuracy. The two non-factual extractions are observable failures, not proof that all other claims were extracted or judged correctly.

This set consists of six generated posts on two fictional sources, uses the same model family for generation and judging, and contains no deliberately corrupted controls. It cannot establish detection recall for factual errors. No new control drafts were silently mixed into user outputs.

Next improvement: enforce ignoring non-factual exclamations/opinions, and evaluate each qualifier in compound spans. Keep these results as the extraction-mode baseline; compare a revised judge separately on this set and fresh examples.

## Per-draft evidence

### library / x

Brookfield Library's 6-week trial of longer opening hours saw average weekly visits rise from 800 to 1,000. Two community events were also held during this period. Read the trial summary. #BrookfieldLibrary #Community

- **supported**: Brookfield Library's 6-week trial of longer opening hours saw average weekly visits rise from 800 to 1,000.
  Reason: The source states that Brookfield Library tested longer opening hours for six weeks and that average weekly visits increased from 800 to 1,000 during this trial.
- **supported**: Two community events were also held during this period.
  Reason: The source explicitly states that 'The library also held two community events during this period'.

### library / linkedin

Brookfield Library recently concluded a six-week trial of extended opening hours. During this period, the library observed an increase in average weekly visits from 800 to 1,000. It is noted that two community events were also hosted during the trial, which may have contributed to the increased visitation. The library has not yet made a decision regarding the permanence of the new hours. Read the trial summary. #BrookfieldLibrary #CommunityEngagement #LibraryServices

- **supported**: Brookfield Library recently concluded a six-week trial of extended opening hours.
  Reason: The source states that Brookfield Library tested longer opening hours for six weeks, which aligns with the claim.
- **supported**: During this period, the library observed an increase in average weekly visits from 800 to 1,000.
  Reason: The source confirms the increase in average weekly visits from 800 to 1,000 during the trial.
- **supported**: It is noted that two community events were also hosted during the trial, which may have contributed to the increased visitation.
  Reason: The source states that two community events were held during the trial and that staff cannot determine if longer hours alone caused the increase, implying the events may have contributed.
- **supported**: The library has not yet made a decision regarding the permanence of the new hours.
  Reason: The source explicitly states that the library has not decided whether to make the new hours permanent.

### library / discord

Hey everyone! Brookfield Library just finished a 6-week trial with longer opening hours. We saw average weekly visits go up from 800 to 1,000! Just a heads up, we also had two community events during that time, so we're not sure if the longer hours were the only reason for the boost. No decisions yet on making the new hours permanent. Read the trial summary. #BrookfieldLibrary #LocalCommunity #LibraryNews

- **supported**: Brookfield Library just finished a 6-week trial with longer opening hours.
  Reason: The source states that Brookfield Library tested longer opening hours for six weeks, which directly supports the claim.
- **supported**: We saw average weekly visits go up from 800 to 1,000!
  Reason: The source explicitly states that average weekly visits increased from 800 to 1,000 during the trial.
- **supported**: we also had two community events during that time, so we're not sure if the longer hours were the only reason for the boost.
  Reason: The source confirms that two community events were held and that staff cannot determine if longer hours alone caused the increase, supporting the claim.
- **supported**: No decisions yet on making the new hours permanent.
  Reason: The source explicitly states that the library has not decided whether to make the new hours permanent, directly supporting the claim.

### notenest / x

NoteNest desktop beta users, get ready! Shared folders are here. Invite up to 5 collaborators to view and edit notes. Offline and mobile access are not included in this release. Explore the update #NoteNest #SharedFolders

- **unsupported**: NoteNest desktop beta users, get ready!
  Reason: This is an exclamation and not a factual claim that can be supported or contradicted by the source.
- **supported**: Shared folders are here.
  Reason: The source states that NoteNest has introduced shared folders.
- **supported**: Invite up to 5 collaborators to view and edit notes.
  Reason: The source explicitly states that folder owners can invite up to five collaborators who can view and edit notes.
- **supported**: Offline and mobile access are not included in this release.
  Reason: The source explicitly states that offline collaboration and mobile access are not included in this release.

### notenest / linkedin

Exciting news for NoteNest desktop beta users! We're rolling out shared folders, a new feature designed to enhance collaboration. Folder owners can now invite up to five collaborators to view and edit notes within shared folders. This initial release focuses on desktop functionality, with offline collaboration and mobile access not yet available. Your feedback as beta users will be invaluable in shaping future updates. Explore the update #NoteNest #ProductUpdate #Collaboration #BetaFeatures

- **unsupported**: Exciting news for NoteNest desktop beta users!
  Reason: The source does not contain any information about whether the news is exciting or not. This is a subjective opinion.
- **supported**: We're rolling out shared folders, a new feature designed to enhance collaboration.
  Reason: The source states that NoteNest has introduced shared folders, which implies they are being rolled out. The claim that it's designed to enhance collaboration is a reasonable inference from the feature's description.
- **supported**: Folder owners can now invite up to five collaborators to view and edit notes within shared folders.
  Reason: The source directly states that folder owners can invite up to five collaborators who can view and edit notes.
- **supported**: This initial release focuses on desktop functionality, with offline collaboration and mobile access not yet available.
  Reason: The source explicitly states that offline collaboration and mobile access are not included in this release, which supports the claim that the release focuses on desktop functionality and these features are not yet available.
- **supported**: Your feedback as beta users will be invaluable in shaping future updates.
  Reason: The source states that feedback from beta users will help inform future updates, which supports the claim that their feedback will be invaluable in shaping future updates.

### notenest / discord

Hey NoteNest desktop beta users! We've got a cool new update for you: shared folders are here! 🎉 You can now invite up to 5 friends or teammates to view and edit notes together. Just a heads-up, this first version is for desktop only, so no offline or mobile access yet. We're really keen to hear what you think, as your feedback will help us make it even better. Explore the update

- **supported**: NoteNest desktop beta users! We've got a cool new update for you: shared folders are here!
  Reason: The source states that NoteNest has introduced shared folders for its desktop beta users.
- **supported**: You can now invite up to 5 friends or teammates to view and edit notes together.
  Reason: The source confirms that folder owners can invite up to five collaborators to view and edit notes.
- **supported**: this first version is for desktop only, so no offline or mobile access yet.
  Reason: The source explicitly states that offline collaboration and mobile access are not included in this release.
- **supported**: We're really keen to hear what you think, as your feedback will help us make it even better.
  Reason: The source states that feedback from beta users will help inform future updates, which aligns with the claim.
