"""Judge the six user-pasted drafts without supplying candidate claims or labels."""
import argparse
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone
from app.config import settings
from app.llm.base import LLMError
from evaluations.judge import evaluate_draft

SOURCES = {
'library': "Brookfield Library tested longer opening hours for six weeks. During the trial, average weekly visits increased from 800 to 1,000—a 25% increase. The library also held two community events during this period, so staff cannot determine whether longer hours alone caused the increase. Visitor satisfaction was not measured. The library has not decided whether to make the new hours permanent.",
'notenest': "NoteNest, a fictional note-taking app, has introduced shared folders for its existing desktop beta users. Folder owners can invite up to five collaborators, who can view and edit notes. Offline collaboration and mobile access are not included in this release. The company has not announced pricing or a public launch date. Feedback from beta users will help inform future updates.",
}
DRAFTS = [
('library','x',"Brookfield Library's 6-week trial of longer opening hours saw average weekly visits rise from 800 to 1,000. Two community events were also held during this period. Read the trial summary. #BrookfieldLibrary #Community"),
('library','linkedin',"Brookfield Library recently concluded a six-week trial of extended opening hours. During this period, the library observed an increase in average weekly visits from 800 to 1,000. It is noted that two community events were also hosted during the trial, which may have contributed to the increased visitation. The library has not yet made a decision regarding the permanence of the new hours. Read the trial summary. #BrookfieldLibrary #CommunityEngagement #LibraryServices"),
('library','discord',"Hey everyone! Brookfield Library just finished a 6-week trial with longer opening hours. We saw average weekly visits go up from 800 to 1,000! Just a heads up, we also had two community events during that time, so we're not sure if the longer hours were the only reason for the boost. No decisions yet on making the new hours permanent. Read the trial summary. #BrookfieldLibrary #LocalCommunity #LibraryNews"),
('notenest','x',"NoteNest desktop beta users, get ready! Shared folders are here. Invite up to 5 collaborators to view and edit notes. Offline and mobile access are not included in this release. Explore the update #NoteNest #SharedFolders"),
('notenest','linkedin',"Exciting news for NoteNest desktop beta users! We're rolling out shared folders, a new feature designed to enhance collaboration. Folder owners can now invite up to five collaborators to view and edit notes within shared folders. This initial release focuses on desktop functionality, with offline collaboration and mobile access not yet available. Your feedback as beta users will be invaluable in shaping future updates. Explore the update #NoteNest #ProductUpdate #Collaboration #BetaFeatures"),
('notenest','discord',"Hey NoteNest desktop beta users! We've got a cool new update for you: shared folders are here! 🎉 You can now invite up to 5 friends or teammates to view and edit notes together. Just a heads-up, this first version is for desktop only, so no offline or mobile access yet. We're really keen to hear what you think, as your feedback will help us make it even better. Explore the update"),
]
# Frozen before observing judge output. Ambiguous wording is not a definitive error label.
MANUAL_REVIEW = {
'library/x':'Core facts supported; no explicit causal assertion.',
'library/linkedin':'Core facts supported; events may have contributed is tentative interpretation; preserve source uncertainty. Recently concluded adds timing not explicitly given.',
'library/discord':'Core facts supported; only reason is ambiguous, not a clear causal assertion. We assumes library-account voice. Just finished adds timing not explicitly given.',
'notenest/x':'Core features supported; offline access is broader than source offline collaboration.',
'notenest/linkedin':'Core features supported; not yet available may imply a future roadmap but does not promise one. We assumes company-account voice.',
'notenest/discord':'Core features supported; offline access broader than offline collaboration. First version not established; source only says this release. Better is promotional language.',
}

async def main(args):
    out=args.output; out.mkdir(parents=True,exist_ok=True)
    report={'started_at':datetime.now(timezone.utc).isoformat(),'model':settings.llm_model,'scope':'Six user-pasted generated drafts, two fictional sources; extraction mode, no supplied claims or labels. No regeneration or prompt changes.','sources':SOURCES,'manual_review_before_judge':MANUAL_REVIEW,'results':[]}
    def save(): (out/'raw_results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    save()
    for case,platform,draft in DRAFTS:
        try:
            result=await evaluate_draft(source=SOURCES[case],draft=draft,api_key=settings.openrouter_api_key,base_url=settings.openrouter_base_url,model=settings.llm_model,timeout=settings.llm_timeout_seconds,prompt_version=args.prompt_version)
        except LLMError as exc: result={'status':'failed','error':str(exc)}
        report['results'].append({'case':case,'platform':platform,'draft':draft,'judge':result}); save()
        print(case,platform,json.dumps(result,ensure_ascii=False),flush=True)
    report['finished_at']=datetime.now(timezone.utc).isoformat(); save()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt-version',choices=('v1','v2','v3','v4','v5','v6','v7'),default='v7')
    parser.add_argument('--output',type=Path,required=True)
    asyncio.run(main(parser.parse_args()))
