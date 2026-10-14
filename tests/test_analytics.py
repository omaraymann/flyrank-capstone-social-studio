from sqlalchemy import select

from app.database import SessionLocal
from app.models import GenerationRun, PlatformVariant, PublishDelivery, ScheduleSlot
from app.models import utcnow


def seed_workspace(client, headers):
    post = client.post("/posts", headers=headers, json={
        "title": "Analytics", "markdown": "Operational metrics help teams understand their campaign pipeline.",
    }).json()
    with SessionLocal() as db:
        for platform, status, delivery_status in (
            ("x", "published", "succeeded"),
            ("linkedin", "scheduled", "failed"),
            ("discord", "scheduled", "processing"),
        ):
            variant = PlatformVariant(source_post_id=post["id"], platform=platform, content="Draft", status=status)
            db.add(variant)
            db.flush()
            slot = ScheduleSlot(variant_id=variant.id, publish_at=utcnow(), status={
                "succeeded": "completed", "failed": "failed", "processing": "processing",
            }[delivery_status])
            db.add(slot)
            db.flush()
            db.add(PublishDelivery(
                schedule_slot_id=slot.id, platform=platform, idempotency_key=f"{post['id']}-{platform}",
                content_snapshot="Draft", status=delivery_status,
            ))
        db.add_all([
            GenerationRun(
                source_post_id=post["id"], provider="fake", model="test-model", prompt_version="v1",
                examples_version="v1", platforms="x", audience="engineers", goal="traffic",
                tone="educational", call_to_action="Read more", temperature=0.7, top_p=0.9,
                max_output_tokens=1000, status=status, input_tokens=input_tokens, output_tokens=output_tokens,
                estimated_cost_usd=cost, latency_ms=latency, repair_count=repairs,
            )
            for status, input_tokens, output_tokens, cost, latency, repairs in (
                ("succeeded", 100, 50, 0.01, 1000, 1),
                ("failed", 200, 20, None, 3000, 0),
                ("processing", None, None, None, None, 0),
            )
        ])
        db.commit()


def test_analytics_requires_authentication(client):
    assert client.get("/analytics/summary").status_code == 403
    assert client.get("/analytics/summary", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_empty_workspace_has_zero_counts_and_unknown_cost(client, auth_headers):
    response = client.get("/analytics/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["campaigns"] == 0
    for key in ("variants_by_status", "schedules_by_status", "deliveries_by_status"):
        assert all(count == 0 for count in data[key].values())
    assert data["delivery_success_rate"] is None
    assert data["ai_usage"]["runs"] == 0
    assert data["ai_usage"]["reported_cost_usd"] is None
    assert data["ai_usage"]["average_latency_ms"] is None


def test_summary_aggregates_outcomes_and_includes_failed_run_usage(client, auth_headers):
    seed_workspace(client, auth_headers)
    data = client.get("/analytics/summary", headers=auth_headers).json()
    assert data["campaigns"] == 1
    assert data["variants_by_status"] == {"draft": 0, "approved": 0, "rejected": 0, "scheduled": 2, "published": 1}
    assert data["schedules_by_status"] == {"pending": 0, "processing": 1, "completed": 1, "failed": 1}
    assert data["deliveries_by_status"] == {"processing": 1, "succeeded": 1, "failed": 1}
    assert data["delivery_success_rate"] == 0.5
    assert data["ai_usage"] == {
        "runs": 3, "succeeded": 1, "failed": 1, "processing": 1,
        "input_tokens": 300, "output_tokens": 70, "repair_count": 1,
        "reported_cost_usd": 0.01, "runs_with_reported_cost": 1, "average_latency_ms": 2000.0,
    }


def test_every_metric_is_isolated_by_owner(client, auth_headers):
    seed_workspace(client, auth_headers)
    credentials = {"email": "analytics-other@example.com", "password": "password123"}
    client.post("/auth/signup", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {token}"}
    empty = client.get("/analytics/summary", headers=other_headers).json()
    assert empty["campaigns"] == 0
    assert empty["ai_usage"]["runs"] == 0
    assert all(count == 0 for counts in (empty["variants_by_status"], empty["schedules_by_status"], empty["deliveries_by_status"]) for count in counts.values())
    seed_workspace(client, other_headers)
    assert client.get("/analytics/summary", headers=auth_headers).json() == client.get("/analytics/summary", headers=other_headers).json()


def test_zero_reported_cost_is_distinct_from_missing_cost(client, auth_headers):
    seed_workspace(client, auth_headers)
    with SessionLocal() as db:
        run = db.scalar(select(GenerationRun).where(GenerationRun.estimated_cost_usd.is_not(None)))
        run.estimated_cost_usd = 0
        db.commit()
    usage = client.get("/analytics/summary", headers=auth_headers).json()["ai_usage"]
    assert usage["reported_cost_usd"] == 0
    assert usage["runs_with_reported_cost"] == 1
