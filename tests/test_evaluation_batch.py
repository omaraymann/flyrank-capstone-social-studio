import asyncio
import json

import httpx
import pytest

from app.llm.base import LLMError
from evaluations.judge import evaluate_draft
from evaluations.run_batch import metrics


@pytest.mark.parametrize("version", ["v1", "v2", "v3", "v4", "v5"])
def test_classification_request_hides_reference_labels(version):
    source = "The team has five members."
    draft = "The team has fifty members."

    def handler(request):
        payload = json.loads(request.content)
        inputs = json.loads(payload["messages"][1]["content"])
        assert inputs == {"source": source, "draft": draft, "candidate_claims": [draft]}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"claims": [{
            "claim": draft, "verdict": "contradicted", "source_excerpt": source,
            "reason": "Five is not fifty.",
        }]})}}], "usage": {}})

    result = asyncio.run(evaluate_draft(source=source, draft=draft, candidate_claims=[draft],
        api_key="fake", base_url="https://judge.test/v1", model="fake", transport=httpx.MockTransport(handler), prompt_version=version))
    assert result["requires_review"] is True
    assert result["prompt_version"] == f"factuality-classification-{version}"


def test_classifier_cannot_skip_a_supplied_claim():
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"claims": []}'}}]})

    with pytest.raises(LLMError, match="exactly the supplied"):
        asyncio.run(evaluate_draft(source="Five members.", draft="Fifty members.",
            candidate_claims=["Fifty members."], api_key="fake", base_url="https://judge.test/v1",
            model="fake", transport=httpx.MockTransport(handler)))


def test_metrics_count_false_alarms_missed_errors_and_failures_separately():
    def row(identifier, gold, predicted):
        judge = {"status": "failed", "error": "Timeout"} if predicted is None else {
            "status": "succeeded", "requires_review": predicted != "supported",
            "claims": [{"claim": "Claim", "verdict": predicted, "reason": "Reason"}],
        }
        return {"id": identifier, "source_case_id": "01", "gold_claims": [{"claim": "Claim", "verdict": gold}],
            "expected_requires_review": gold != "supported", "judge": judge}

    result = metrics([
        row("caught", "contradicted", "contradicted"),
        row("missed", "unsupported", "supported"),
        row("false_alarm", "supported", "unsupported"),
        row("failed", "unsupported", None),
    ])
    assert result["failed"] == 1
    assert result["scored_claims"] == 3
    assert result["claim_accuracy_on_successes"] == 1 / 3
    assert result["correct_claim_fraction_all_attempts"] == 1 / 4
    assert result["flawed_drafts_caught"] == 1
    assert result["flawed_drafts_missed"] == 1
    assert result["accurate_drafts_flagged"] == 1
    assert len(result["disagreements"]) == 2
