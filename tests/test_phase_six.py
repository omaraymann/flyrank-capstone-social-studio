import httpx
import pytest

from app.llm.base import GenerationSettings, LLMError, LLMResult
from app.llm.openrouter import OpenRouterProvider
from app.llm.registry import get_llm_provider
from app.main import app


class FakeLLM:
    name = "fake"

    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []

    async def generate(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.responses.pop(0)


def create_post(client, headers):
    return client.post(
        "/posts",
        headers=headers,
        json={
            "title": "Reliable analytics pipelines",
            "markdown": "Reliable analytics pipelines persist jobs, validate data and record every processing outcome.",
        },
    ).json()


def llm_payload():
    return {
        "platforms": ["x", "linkedin"],
        "generation_mode": "llm",
        "audience": "data engineers",
        "goal": "traffic",
        "tone": "educational",
        "call_to_action": "Read the engineering guide",
    }


def test_llm_generates_distinct_variants_and_records_metadata(client, auth_headers):
    post = create_post(client, auth_headers)
    fake = FakeLLM(
        [
            LLMResult(
                variants={
                    "x": "Reliable pipelines make failures visible. Read the engineering guide. #DataEngineering",
                    "linkedin": (
                        "Reliable analytics starts with observable pipelines.\n\n"
                        "Persist each job, validate incoming data, and record every outcome. "
                        "These controls make recovery safer for data teams.\n\nRead the engineering guide. #DataEngineering"
                    ),
                },
                input_tokens=200,
                output_tokens=80,
                cost_usd=0.001,
            )
        ]
    )
    app.dependency_overrides[get_llm_provider] = lambda: fake
    try:
        response = client.post(f"/posts/{post['id']}/variants", headers=auth_headers, json=llm_payload())
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)

    assert response.status_code == 201
    variants = response.json()
    assert variants[0]["content"] != variants[1]["content"]
    assert "Few-shot examples" in fake.calls[0]["system_prompt"]
    assert "Audience: data engineers" in fake.calls[0]["user_prompt"]
    assert fake.calls[0]["settings"].top_p == 0.9
    assert fake.calls[0]["settings"].top_k == 40

    runs = client.get(f"/posts/{post['id']}/generations", headers=auth_headers).json()
    assert runs[0]["status"] == "succeeded"
    assert runs[0]["input_tokens"] == 200
    assert runs[0]["output_tokens"] == 80
    assert runs[0]["repair_count"] == 0


def test_invalid_draft_is_repaired_once(client, auth_headers):
    post = create_post(client, auth_headers)
    fake = FakeLLM(
        [
            LLMResult(variants={"x": "x" * 281}),
            LLMResult(variants={"x": "A repaired concise draft. Read the engineering guide. #Engineering"}),
        ]
    )
    payload = llm_payload()
    payload["platforms"] = ["x"]
    app.dependency_overrides[get_llm_provider] = lambda: fake
    try:
        response = client.post(f"/posts/{post['id']}/variants", headers=auth_headers, json=payload)
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)
    assert response.status_code == 201
    assert response.json()[0]["content"].startswith("A repaired")
    assert fake.calls[1]["settings"].temperature == 0.1
    runs = client.get(f"/posts/{post['id']}/generations", headers=auth_headers).json()
    assert runs[0]["repair_count"] == 1


def test_provider_failure_is_safe_and_audited(client, auth_headers):
    post = create_post(client, auth_headers)
    fake = FakeLLM(error=LLMError("LLM provider timed out"))
    app.dependency_overrides[get_llm_provider] = lambda: fake
    try:
        response = client.post(f"/posts/{post['id']}/variants", headers=auth_headers, json=llm_payload())
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)
    assert response.status_code == 502
    assert response.json()["detail"] == "LLM provider timed out"
    assert client.get(f"/posts/{post['id']}/variants", headers=auth_headers).json() == []
    runs = client.get(f"/posts/{post['id']}/generations", headers=auth_headers).json()
    assert runs[0]["status"] == "failed"


def test_generation_history_is_private(client, auth_headers):
    post = create_post(client, auth_headers)
    credentials = {"email": "llm-other@example.com", "password": "password123"}
    client.post("/auth/signup", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    response = client.get(
        f"/posts/{post['id']}/generations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_openrouter_rejects_invalid_structured_output():
    def handler(request):
        response = {"choices": [{"message": {"content": "not-json"}}], "usage": {}}
        return httpx.Response(200, json=response)

    provider = OpenRouterProvider("test-key", "https://openrouter.test/v1", 1, httpx.MockTransport(handler))
    settings = GenerationSettings(model="test", temperature=0.7, top_p=0.9, top_k=40, max_output_tokens=100)
    import asyncio
    with pytest.raises(LLMError, match="invalid structured output"):
        asyncio.run(
            provider.generate(system_prompt="rules", user_prompt="article", platforms=["x"], settings=settings)
        )
