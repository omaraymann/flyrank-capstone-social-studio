from datetime import datetime, timedelta, timezone

from app.main import app
from app.publishers.base import PublishRequest, PublishResult, SocialPublisher
from app.publishers.discord import DiscordPublisher
from app.publishers.registry import PublisherRegistry, get_publisher_registry
from app.services.publishing import make_idempotency_key


class CountingPublisher(SocialPublisher):
    def __init__(self):
        self.calls = 0

    async def publish(self, request: PublishRequest) -> PublishResult:
        self.calls += 1
        return PublishResult(external_post_id=f"test-{request.idempotency_key[:12]}")


def test_idempotency_key_is_stable_per_variant_and_slot():
    assert make_idempotency_key(8, 3) == make_idempotency_key(8, 3)
    assert make_idempotency_key(8, 3) != make_idempotency_key(8, 4)


def scheduled_variant(client, auth_headers, platform="x"):
    post = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "Reliable delivery", "markdown": "Idempotency prevents duplicate social posts during retries."},
    ).json()
    variant = client.post(
        f"/posts/{post['id']}/variants", headers=auth_headers, json={"platforms": [platform]}
    ).json()[0]
    client.post(f"/variants/{variant['id']}/approve", headers=auth_headers)
    schedule = client.post(
        f"/variants/{variant['id']}/schedule",
        headers=auth_headers,
        json={"publish_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()},
    ).json()
    return variant, schedule


def test_repeated_publish_uses_one_external_call(client, auth_headers):
    _, schedule = scheduled_variant(client, auth_headers)
    publisher = CountingPublisher()
    app.dependency_overrides[get_publisher_registry] = lambda: PublisherRegistry({"x": publisher})
    try:
        first = client.post(f"/schedules/{schedule['id']}/publish", headers=auth_headers)
        second = client.post(f"/schedules/{schedule['id']}/publish", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(get_publisher_registry, None)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["external_post_id"] == second.json()["external_post_id"]
    assert first.json()["already_published"] is False
    assert second.json()["already_published"] is True
    assert publisher.calls == 1


def test_mock_x_and_linkedin_publishers_are_swappable(client, auth_headers):
    for platform in ("x", "linkedin"):
        _, schedule = scheduled_variant(client, auth_headers, platform)
        response = client.post(f"/schedules/{schedule['id']}/publish", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["external_post_id"].startswith(f"mock-{platform}-")


def test_discord_adapter_reports_missing_configuration(client, auth_headers):
    _, schedule = scheduled_variant(client, auth_headers, "discord")
    app.dependency_overrides[get_publisher_registry] = lambda: PublisherRegistry({"discord": DiscordPublisher(None)})
    try:
        response = client.post(f"/schedules/{schedule['id']}/publish", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(get_publisher_registry, None)
    assert response.status_code == 502
    assert "not configured" in response.json()["detail"]


def test_other_user_cannot_publish_schedule(client, auth_headers):
    _, schedule = scheduled_variant(client, auth_headers)
    credentials = {"email": "publisher@example.com", "password": "password123"}
    client.post("/auth/signup", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    response = client.post(
        f"/schedules/{schedule['id']}/publish", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
