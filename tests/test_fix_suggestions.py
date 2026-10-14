import json
from datetime import timedelta
import pytest
from sqlalchemy import select
from app.database import SessionLocal
from app.main import app
from app.llm.base import LLMResult
from app.llm.registry import get_llm_provider
from app.models import GenerationRun, PlatformVariant, RevisionSuggestion, SourcePost, utcnow
from test_fact_checks import draft, result, run

FIXED = 'Five collaborators can edit shared notes. Offline collaboration is unavailable. Explore the update'

class Provider:
    name = 'fake'
    def __init__(self, content=FIXED, edit=None):
        self.content, self.edit, self.calls = content, edit, []
    async def generate(self, **inputs):
        self.calls.append(inputs)
        if self.edit: self.edit()
        return LLMResult({'x': self.content}, 100, 30, 0.001)

@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.pop(get_llm_provider, None)

def setup(client, headers):
    post, variant = draft(client, headers)
    original = 'Offline access is unavailable. Explore the update'
    variant = client.patch(f"/variants/{variant['id']}", headers=headers, json={'content': original}).json()
    with SessionLocal() as db:
        db.add(GenerationRun(source_post_id=post['id'], provider='fake', model='fake', prompt_version='test',
            examples_version='test', platforms='x', audience='beta users', goal='awareness', tone='friendly',
            call_to_action='Explore the update', temperature=.2, top_p=.9, max_output_tokens=100, status='succeeded'))
        db.commit()
    async def judge(**inputs): return result(inputs['draft'], 'unsupported', True)
    check = run(client, headers, variant, judge).json()
    return post, variant, check

def suggest(client, headers, variant, check, provider):
    app.dependency_overrides[get_llm_provider] = lambda: provider
    return client.post(f"/variants/{variant['id']}/fix-suggestions", headers=headers, json={'fact_check_id': check['id']})

def apply(client, headers, variant, proposal):
    return client.post(f"/variants/{variant['id']}/fix-suggestions/{proposal['id']}/apply", headers=headers)

def test_proposal_one_call_then_apply_recheck_and_manual_approval(client, auth_headers):
    post, variant, check = setup(client, auth_headers)
    provider = Provider()
    response = suggest(client, auth_headers, variant, check, provider)
    assert response.status_code == 201
    proposal = response.json()
    assert proposal['status'] == 'succeeded' and not proposal['stale']
    assert proposal['reported_cost_usd'] == .001
    assert len(provider.calls) == 1
    inputs = provider.calls[0]
    assert inputs['platforms'] == ['x'] and inputs['settings'].temperature == .2
    prompt = json.loads(inputs['user_prompt'])
    assert prompt['source'] == post['content'] and prompt['draft'] == variant['content']
    assert prompt['protected_call_to_action'] == 'Explore the update'
    assert prompt['flagged_claims'][0]['verdict'] == 'unsupported'
    assert client.get(f"/variants/{variant['id']}", headers=auth_headers).json()['content'] == variant['content']
    assert client.get(f"/variants/{variant['id']}/fix-suggestions/latest", headers=auth_headers).json()['id'] == proposal['id']
    applied = apply(client, auth_headers, variant, proposal).json()
    assert applied['content'] == FIXED and applied['status'] == 'draft' and applied['fact_recheck_required']
    assert apply(client, auth_headers, variant, proposal).status_code == 409
    assert client.get(f"/variants/{variant['id']}/fact-check", headers=auth_headers).json()['stale']
    assert client.post(f"/variants/{variant['id']}/approve", headers=auth_headers).status_code == 409
    async def failed(**inputs): raise RuntimeError('failed')
    run(client, auth_headers, variant, failed)
    assert client.post(f"/variants/{variant['id']}/approve", headers=auth_headers).status_code == 409
    async def fresh(**inputs): return result(inputs['draft'])
    assert not run(client, auth_headers, variant, fresh).json()['stale']
    assert client.get(f"/variants/{variant['id']}", headers=auth_headers).json()['status'] == 'draft'
    assert client.post(f"/variants/{variant['id']}/approve", headers=auth_headers).status_code == 200
    assert len(provider.calls) == 1

@pytest.mark.parametrize('bad', ['x' * 281, 'Five collaborators can edit notes.', 'Offline access is unavailable. Explore the update'])
def test_invalid_proposals_cannot_be_applied(client, auth_headers, bad):
    _, variant, check = setup(client, auth_headers)
    proposal = suggest(client, auth_headers, variant, check, Provider(bad)).json()
    assert proposal['status'] == 'failed' and proposal['error_message']
    assert proposal['reported_cost_usd'] == .001
    assert apply(client, auth_headers, variant, proposal).status_code == 409
    assert client.get(f"/variants/{variant['id']}", headers=auth_headers).json()['content'] == variant['content']

@pytest.mark.parametrize('change', ['draft', 'source', 'check'])
def test_proposal_rejects_changed_inputs(client, auth_headers, change):
    post, variant, check = setup(client, auth_headers)
    proposal = suggest(client, auth_headers, variant, check, Provider()).json()
    if change == 'check':
        async def judge(**inputs): return result(inputs['draft'], 'unsupported', True)
        run(client, auth_headers, variant, judge)
    else:
        with SessionLocal() as db:
            row = db.get(PlatformVariant, variant['id']) if change == 'draft' else db.get(SourcePost, post['id'])
            row.content += ' Changed.'; db.commit()
    assert apply(client, auth_headers, variant, proposal).status_code == 409
    assert client.get(f"/variants/{variant['id']}/fix-suggestions/latest", headers=auth_headers).json()['stale']

def test_edit_during_generation_cannot_be_overwritten(client, auth_headers):
    _, variant, check = setup(client, auth_headers)
    def edit():
        with SessionLocal() as db:
            row = db.get(PlatformVariant, variant['id']); row.content = 'My own edit.'; db.commit()
    proposal = suggest(client, auth_headers, variant, check, Provider(edit=edit)).json()
    assert proposal['stale'] and proposal['status'] == 'succeeded'
    assert apply(client, auth_headers, variant, proposal).status_code == 409
    assert client.get(f"/variants/{variant['id']}", headers=auth_headers).json()['content'] == 'My own edit.'

def test_ownership_and_stale_check_never_call_model(client, auth_headers):
    _, variant, check = setup(client, auth_headers)
    credentials = {'email': 'other@example.com', 'password': 'other-password'}
    client.post('/auth/signup', json=credentials)
    other = {'Authorization': 'Bearer ' + client.post('/auth/login', json=credentials).json()['access_token']}
    provider = Provider()
    assert suggest(client, other, variant, check, provider).status_code == 404
    assert client.get(f"/variants/{variant['id']}/fix-suggestions/latest", headers=other).status_code == 404
    client.patch(f"/variants/{variant['id']}", headers=auth_headers, json={'content': 'My edit'})
    assert suggest(client, auth_headers, variant, check, provider).status_code == 409
    assert not provider.calls

def test_processing_recovery_and_duplicate_prevention(client, auth_headers):
    _, variant, check = setup(client, auth_headers)
    with SessionLocal() as db:
        db.add(RevisionSuggestion(variant_id=variant['id'], fact_check_id=check['id'], draft_snapshot=variant['content'],
            draft_hash='test', source_hash='test', model='fake', prompt_version='test', status='processing'))
        db.commit()
    provider = Provider()
    assert suggest(client, auth_headers, variant, check, provider).status_code == 409
    assert not provider.calls
    with SessionLocal() as db:
        row = db.scalar(select(RevisionSuggestion)); row.created_at = utcnow() - timedelta(hours=1); db.commit()
    assert client.get(f"/variants/{variant['id']}/fix-suggestions/latest", headers=auth_headers).json()['status'] == 'failed'
    assert suggest(client, auth_headers, variant, check, provider).json()['status'] == 'succeeded'

def test_stale_recheck_does_not_unlock_approval(client, auth_headers):
    _, variant, check = setup(client, auth_headers)
    proposal = suggest(client, auth_headers, variant, check, Provider()).json()
    apply(client, auth_headers, variant, proposal)
    async def judge(**inputs):
        with SessionLocal() as db:
            row = db.get(PlatformVariant, variant['id']); row.content = 'Newer manual edit.'; db.commit()
        return result(inputs['draft'])
    assert run(client, auth_headers, variant, judge).json()['stale']
    assert client.post(f"/variants/{variant['id']}/approve", headers=auth_headers).status_code == 409

def test_concurrent_ai_edit_cannot_bypass_approval_gate(client, auth_headers, monkeypatch):
    import app.api.variants as routes
    _, variant, _ = setup(client, auth_headers)
    original = routes.approve_variant
    def concurrent(row):
        original(row)
        with SessionLocal() as db:
            changed = db.get(PlatformVariant, row.id)
            changed.content = FIXED
            changed.fact_recheck_required = True
            db.commit()
    monkeypatch.setattr(routes, 'approve_variant', concurrent)
    assert client.post(f"/variants/{variant['id']}/approve", headers=auth_headers).status_code == 409
    saved = client.get(f"/variants/{variant['id']}", headers=auth_headers).json()
    assert saved['status'] == 'draft' and saved['fact_recheck_required']
