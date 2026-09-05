import asyncio
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import ScheduleSlot
from app.publishers.base import PublisherError, PublishRequest, PublishResult, SocialPublisher
from app.publishers.registry import PublisherRegistry
from app.services.worker import run_once


class CountingPublisher(SocialPublisher):
    def __init__(self):
        self.calls = 0

    async def publish(self, request: PublishRequest) -> PublishResult:
        self.calls += 1
        return PublishResult(external_post_id=f"worker-{request.idempotency_key[:12]}")


class FailOncePublisher(CountingPublisher):
    async def publish(self, request: PublishRequest) -> PublishResult:
        self.calls += 1
        if self.calls == 1:
            raise PublisherError("Temporary test failure")
        return PublishResult(external_post_id=f"recovered-{request.idempotency_key[:12]}")


def create_schedule(client, auth_headers, platform="x"):
    post = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "Durable worker", "markdown": "A durable worker publishes due jobs and survives process restarts."},
    ).json()
    variant = client.post(
        f"/posts/{post['id']}/variants", headers=auth_headers, json={"platforms": [platform]}
    ).json()[0]
    client.post(f"/variants/{variant['id']}/approve", headers=auth_headers)
    return client.post(
        f"/variants/{variant['id']}/schedule",
        headers=auth_headers,
        json={"publish_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()},
    ).json()


def make_due(schedule_id: int):
    with SessionLocal() as db:
        schedule = db.get(ScheduleSlot, schedule_id)
        schedule.publish_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        schedule.next_attempt_at = None
        db.commit()


def test_worker_publishes_due_schedule_and_history_is_visible(client, auth_headers):
    schedule = create_schedule(client, auth_headers)
    make_due(schedule["id"])
    publisher = CountingPublisher()
    registry = PublisherRegistry({"x": publisher})

    assert asyncio.run(run_once(registry, "test-worker")) is True
    assert asyncio.run(run_once(registry, "test-worker")) is False
    assert publisher.calls == 1

    history = client.get(f"/schedules/{schedule['id']}/history", headers=auth_headers)
    assert history.status_code == 200
    assert [attempt["status"] for attempt in history.json()] == ["succeeded"]
    all_history = client.get("/publish-history", headers=auth_headers)
    assert all_history.status_code == 200
    assert all_history.json()[0]["delivery"]["status"] == "succeeded"


def test_expired_claim_is_recovered_without_duplicate(client, auth_headers):
    schedule = create_schedule(client, auth_headers)
    make_due(schedule["id"])
    with SessionLocal() as db:
        stored = db.get(ScheduleSlot, schedule["id"])
        stored.status = "processing"
        stored.worker_id = "crashed-worker"
        stored.claimed_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        stored.lease_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    publisher = CountingPublisher()
    assert asyncio.run(run_once(PublisherRegistry({"x": publisher}), "replacement-worker")) is True
    assert publisher.calls == 1
    with SessionLocal() as db:
        assert db.get(ScheduleSlot, schedule["id"]).status == "completed"


def test_temporary_failure_retries_with_attempt_history(client, auth_headers):
    schedule = create_schedule(client, auth_headers)
    make_due(schedule["id"])
    publisher = FailOncePublisher()
    registry = PublisherRegistry({"x": publisher})

    assert asyncio.run(run_once(registry, "retry-worker")) is True
    with SessionLocal() as db:
        stored = db.get(ScheduleSlot, schedule["id"])
        assert stored.status == "pending"
        stored.next_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    assert asyncio.run(run_once(registry, "retry-worker")) is True
    assert publisher.calls == 2
    history = client.get(f"/schedules/{schedule['id']}/history", headers=auth_headers).json()
    assert [attempt["status"] for attempt in history] == ["failed", "succeeded"]


def test_other_user_cannot_view_publish_history(client, auth_headers):
    schedule = create_schedule(client, auth_headers)
    make_due(schedule["id"])
    asyncio.run(run_once(PublisherRegistry({"x": CountingPublisher()}), "history-worker"))

    credentials = {"email": "history@example.com", "password": "password123"}
    client.post("/auth/signup", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {token}"}
    assert client.get(f"/schedules/{schedule['id']}/history", headers=other_headers).status_code == 404
    assert client.get("/publish-history", headers=other_headers).json() == []


def test_manual_retry_only_accepts_failed_safe_schedule(client, auth_headers):
    schedule = create_schedule(client, auth_headers)
    assert client.post(f"/schedules/{schedule['id']}/retry", headers=auth_headers).status_code == 409
    with SessionLocal() as db:
        stored = db.get(ScheduleSlot, schedule["id"])
        stored.status = "failed"
        stored.last_error = "Maximum retries reached"
        db.commit()
    response = client.post(f"/schedules/{schedule['id']}/retry", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
