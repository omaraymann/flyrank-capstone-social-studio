from datetime import timedelta
from sqlalchemy import select
from app.api.fact_checks import get_fact_judge
from app.database import SessionLocal
from app.llm.base import LLMError
from app.main import app
from app.models import FactCheck, PlatformVariant, SourcePost, utcnow


def draft(client, headers):
    post = client.post('/posts', headers=headers, json={
        'title': 'Shared notes', 'markdown': 'A shared notes application lets five collaborators edit notes. Offline collaboration is not available.'}).json()
    variant = client.post(f"/posts/{post['id']}/variants", headers=headers,
        json={'platforms': ['x']}).json()[0]
    return post, variant


def result(content, verdict='supported', requires_review=False):
    return {'status': 'succeeded', 'claims': [{'claim': content, 'verdict': verdict,
        'source_excerpt': None if verdict == 'unsupported' else 'A shared notes application lets five collaborators edit notes.',
        'reason': 'Check the precise supported feature scope.'}], 'requires_review': requires_review,
        'reported_cost_usd': 0.01, 'latency_ms': 20}


def run(client, headers, variant, fake):
    app.dependency_overrides[get_fact_judge] = lambda: fake
    try:
        return client.post(f"/variants/{variant['id']}/fact-check", headers=headers)
    finally:
        app.dependency_overrides.pop(get_fact_judge, None)


def test_check_persists_evidence_usage_and_keeps_approval_manual(client, auth_headers):
    post, variant = draft(client, auth_headers)
    assert client.get(f"/variants/{variant['id']}/fact-check", headers=auth_headers).json() is None
    async def judge(**inputs):
        assert inputs == {'source': post['content'], 'draft': variant['content']}
        return result(variant['content'], 'unsupported', True)
    response = run(client, auth_headers, variant, judge)
    assert response.status_code == 201
    check = response.json()
    assert check['outcome'] == 'needs_review'
    assert check['stale'] is False
    assert check['claims'][0]['verdict'] == 'unsupported'
    assert check['reported_cost_usd'] == 0.01
    assert client.get(f"/variants/{variant['id']}/fact-check", headers=auth_headers).json()['id'] == check['id']
    assert client.get(f"/variants/{variant['id']}", headers=auth_headers).json()['status'] == 'draft'
    assert client.post(f"/variants/{variant['id']}/approve", headers=auth_headers).status_code == 200


def test_edits_and_source_changes_make_checks_stale_rechecking_retains_history(client, auth_headers):
    post, variant = draft(client, auth_headers)
    async def judge(**inputs): return result(inputs['draft'])
    first = run(client, auth_headers, variant, judge).json()
    edited = 'Five collaborators can edit notes. Read the guide.'
    client.patch(f"/variants/{variant['id']}", headers=auth_headers, json={'content': edited}).raise_for_status()
    check = client.get(f"/variants/{variant['id']}/fact-check", headers=auth_headers).json()
    assert check['stale'] is True
    assert check['draft_snapshot'] == variant['content']
    second = run(client, auth_headers, variant, judge).json()
    assert second['id'] != first['id'] and second['stale'] is False
    with SessionLocal() as db:
        assert len(db.scalars(select(FactCheck)).all()) == 2
        source = db.get(SourcePost, post['id']); source.content += ' New information.'; db.commit()
    assert client.get(f"/variants/{variant['id']}/fact-check", headers=auth_headers).json()['stale'] is True


def test_provider_failure_is_stored_and_is_not_a_pass(client, auth_headers):
    _, variant = draft(client, auth_headers)
    async def judge(**inputs): raise LLMError('Judge provider request failed')
    check = run(client, auth_headers, variant, judge).json()
    assert check['status'] == 'failed' and check['outcome'] == 'failed'
    assert check['claims'] == [] and check['reported_cost_usd'] is None
    assert check['error_message'] == 'Judge provider request failed'
    assert client.get(f"/variants/{variant['id']}/fact-check", headers=auth_headers).json()['status'] == 'failed'


def test_no_factual_claims_is_unknown(client, auth_headers):
    _, variant = draft(client, auth_headers)
    async def judge(**inputs): return {'status': 'succeeded', 'claims': [], 'requires_review': None}
    assert run(client, auth_headers, variant, judge).json()['outcome'] == 'unknown'


def test_other_users_cannot_read_or_run_checks(client, auth_headers):
    _, variant = draft(client, auth_headers)
    credentials = {'email': 'other@example.com', 'password': 'other-password'}
    client.post('/auth/signup', json=credentials)
    token = client.post('/auth/login', json=credentials).json()['access_token']
    other = {'Authorization': f'Bearer {token}'}
    async def judge(**inputs): raise AssertionError('Unauthorized request must not invoke provider')
    assert run(client, other, variant, judge).status_code == 404
    assert client.get(f"/variants/{variant['id']}/fact-check", headers=other).status_code == 404
    assert client.post(f"/variants/{variant['id']}/fact-check").status_code == 403


def test_edit_during_check_marks_result_stale(client, auth_headers):
    _, variant = draft(client, auth_headers)
    async def judge(**inputs):
        with SessionLocal() as db:
            row = db.get(PlatformVariant, variant['id']); row.content = 'A changed draft.'; db.commit()
        return result(inputs['draft'])
    check = run(client, auth_headers, variant, judge).json()
    assert check['stale'] is True
    assert check['draft_snapshot'] == variant['content']


def test_duplicate_checks_are_rejected_and_interrupted_checks_can_be_retried(client, auth_headers):
    post, variant = draft(client, auth_headers)
    async def judge(**inputs): return result(inputs['draft'])
    with SessionLocal() as db:
        db.add(FactCheck(variant_id=variant['id'], draft_snapshot=variant['content'], source_snapshot=post['content'],
            draft_hash='old', source_hash='old', prompt_version='test', extraction_model='fake', audit_model='fake', status='processing'))
        db.commit()
    assert run(client, auth_headers, variant, judge).status_code == 409
    with SessionLocal() as db:
        check = db.scalar(select(FactCheck)); check.created_at = utcnow() - timedelta(hours=1); db.commit()
    assert client.get(f"/variants/{variant['id']}/fact-check", headers=auth_headers).json()['outcome'] == 'failed'
    assert run(client, auth_headers, variant, judge).status_code == 201
    with SessionLocal() as db:
        checks = db.scalars(select(FactCheck).order_by(FactCheck.id)).all()
        assert [c.status for c in checks] == ['failed', 'succeeded']
