import asyncio
import json

import httpx
import pytest

from app.llm.base import LLMError
from evaluations.judge import evaluate_draft
from evaluations.run_trial import published_sample


SOURCE = "The pilot involved eight volunteers. Accuracy was not measured."
DRAFT = "Eight volunteers tested the pilot. Read the report"


def judge_call(claims, source=SOURCE, draft=DRAFT):
    def handler(request):
        payload = json.loads(request.content)
        assert payload["temperature"] == 0
        assert json.loads(payload["messages"][1]["content"]) == {"source": source, "draft": draft}
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps({"claims": claims})}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost": 0.001},
        })

    return asyncio.run(evaluate_draft(
        source=source, draft=draft, api_key="fake", base_url="https://judge.test/v1",
        model="fake-judge", transport=httpx.MockTransport(handler), prompt_version="v4",
    ))


def claim(**changes):
    return {"claim": "Eight volunteers tested the pilot.", "verdict": "supported",
            "source_excerpt": "The pilot involved eight volunteers.",
            "reason": "The source establishes the participant count.", **changes}


def test_judge_records_grounded_verdict_and_usage():
    result = judge_call([claim()])
    assert result["supported_claim_rate"] == 1
    assert result["requires_review"] is False
    assert result["reported_cost_usd"] == 0.001


@pytest.mark.parametrize("changes", [
    {"source_excerpt": "The source proves improved accuracy."},
    {"source_excerpt": None},
    {"claim": "The pilot involved a thousand volunteers."},
    {"verdict": "probably_supported"},
])
def test_judge_rejects_invalid_evidence_claims_and_verdicts(changes):
    with pytest.raises(LLMError):
        judge_call([claim(**changes)])


def test_unsupported_claim_is_flagged():
    draft = "Accuracy improved. Read the report"
    result = judge_call([claim(claim="Accuracy improved.", verdict="unsupported", source_excerpt=None)], draft=draft)
    assert result["supported_claim_rate"] == 0
    assert result["requires_review"] is True


def test_no_claims_is_unknown_rather_than_a_perfect_score():
    result = judge_call([], draft="Read the report")
    assert result["supported_claim_rate"] is None
    assert result["requires_review"] is None


def test_duplicate_claims_cannot_inflate_the_score():
    with pytest.raises(LLMError):
        judge_call([claim(), claim()])


def test_network_failure_does_not_expose_request_credentials():
    def handler(request):
        raise httpx.ConnectError("secret-token-in-exception", request=request)

    with pytest.raises(LLMError, match="^Judge provider request failed$"):
        asyncio.run(evaluate_draft(
            source=SOURCE, draft=DRAFT, api_key="fake", base_url="https://judge.test/v1",
            model="fake-judge", transport=httpx.MockTransport(handler),
        ))


def test_published_sample_parser_keeps_source_and_reference_separate():
    html = """<h3>Sample Source Article</h3><blockquote><p>Full sample text.</p></blockquote>
    <h3>Actual Tweet related to Article</h3><blockquote>Reference tweet.</blockquote>
    <h3>Predicted Tweet By Model</h3><blockquote>Do not use this.</blockquote>"""
    assert published_sample(html) == ("Full sample text.", "Reference tweet.")


def test_published_sample_parser_handles_section_headers():
    html = """<section><header><h3>Sample Source Article</h3></header>
    <blockquote>Article text.</blockquote></section>
    <section><header><h3>Actual Tweet related to Article</h3></header>
    <blockquote>Tweet text.</blockquote></section>"""
    assert published_sample(html) == ("Article text.", "Tweet text.")


def test_non_factual_spans_are_excluded_from_scores_but_preserved_for_audit():
    draft = "Exciting news! Eight volunteers tested the pilot. Read the report"
    result = judge_call([
        claim(claim="Exciting news!", verdict="non_factual", source_excerpt=None),
        claim(),
        claim(claim="Read the report", verdict="non_factual", source_excerpt=None),
    ], draft=draft)
    assert result["supported_claim_rate"] == 1
    assert result["requires_review"] is False
    assert len(result["claims"]) == 1
    assert len(result["excluded_non_factual"]) == 2


def test_excluding_promotional_text_does_not_hide_an_unsupported_number():
    result = judge_call([
        claim(claim="Amazing!", verdict="non_factual", source_excerpt=None),
        claim(claim="Nine hundred volunteers participated.", verdict="unsupported", source_excerpt=None),
    ], draft="Amazing! Nine hundred volunteers participated.")
    assert result["requires_review"] is True
    assert result["supported_claim_rate"] == 0
    assert len(result["claims"]) == 1


def test_only_non_factual_spans_have_no_factuality_score():
    result = judge_call([claim(claim="Read the report", verdict="non_factual", source_excerpt=None)], draft="Read the report")
    assert result["supported_claim_rate"] is None
    assert result["requires_review"] is None


def test_two_stage_judge_audits_only_facts_and_records_final_verdict_and_total_cost():
    calls = []
    draft = "Exciting news! Eight volunteers tested the pilot."

    def handler(request):
        inputs = json.loads(json.loads(request.content)["messages"][1]["content"])
        calls.append(inputs)
        if len(calls) == 1:
            claims = [claim(claim="Exciting news!", verdict="non_factual", source_excerpt=None), claim()]
        else:
            assert inputs["candidate_claims"] == ["Eight volunteers tested the pilot."]
            claims = [{"claim": "Eight volunteers tested the pilot.", "verdict": "unsupported", "source_passage_id": None, "reason": "Not established."}]
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"claims": claims})}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost": 0.001}})

    result = asyncio.run(evaluate_draft(source=SOURCE, draft=draft, api_key="fake",
        base_url="https://judge.test/v1", model="fake", transport=httpx.MockTransport(handler)))
    assert len(calls) == 2
    assert "candidate_claims" not in calls[0]
    assert result["prompt_version"] == "factuality-judge-v7"
    assert result["requires_review"] is True
    assert result["claims"][0]["verdict"] == "unsupported"
    assert len(result["excluded_non_factual"]) == 1
    assert result["reported_cost_usd"] == 0.002
    assert result["input_tokens"] == 200


def test_failed_second_stage_does_not_return_first_stage_pass():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise httpx.ConnectError("private", request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"claims": [claim()]})}}]})

    with pytest.raises(LLMError, match="^Judge provider request failed$"):
        asyncio.run(evaluate_draft(source=SOURCE, draft=DRAFT, api_key="fake",
            base_url="https://judge.test/v1", model="fake", transport=httpx.MockTransport(handler)))
    assert calls == 2


@pytest.mark.parametrize("passage_id", [0, 99, None])
def test_audit_resolves_source_passage_ids_and_rejects_missing_or_unknown_evidence(passage_id):
    def handler(request):
        payload = json.loads(request.content)
        inputs = json.loads(payload["messages"][1]["content"])
        assert inputs["source_passages"][0]["text"] == "The pilot involved eight volunteers."
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"claims": [{
            "claim": "Eight volunteers tested the pilot.", "verdict": "supported",
            "source_passage_id": passage_id, "reason": "The count is established.",
        }]})}}]})

    def run():
        return asyncio.run(evaluate_draft(source=SOURCE, draft=DRAFT, api_key="fake",
            base_url="https://judge.test/v1", model="fake", prompt_version="v7",
            candidate_claims=["Eight volunteers tested the pilot."], transport=httpx.MockTransport(handler)))
    if passage_id == 0:
        assert run()["claims"][0]["source_excerpt"] == "The pilot involved eight volunteers."
    else:
        with pytest.raises(LLMError):
            run()
