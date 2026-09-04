from datetime import datetime, timedelta, timezone


def create_variant(client, auth_headers, platform="x"):
    post = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "Review workflow", "markdown": "Human review keeps generated social media content safe to publish."},
    ).json()
    return client.post(
        f"/posts/{post['id']}/variants",
        headers=auth_headers,
        json={"platforms": [platform]},
    ).json()[0]


def future_time():
    return (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


def test_list_edit_approve_and_schedule(client, auth_headers):
    variant = create_variant(client, auth_headers)
    listed = client.get(f"/posts/1/variants", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == variant["id"]

    edited = client.patch(
        f"/variants/{variant['id']}", headers=auth_headers, json={"content": "Quick take: Human review protects publishing.\n#Insights"}
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "draft"

    approved = client.post(f"/variants/{variant['id']}/approve", headers=auth_headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    scheduled = client.post(
        f"/variants/{variant['id']}/schedule", headers=auth_headers, json={"publish_at": future_time()}
    )
    assert scheduled.status_code == 201
    assert scheduled.json()["status"] == "pending"


def test_unapproved_variant_cannot_be_scheduled(client, auth_headers):
    variant = create_variant(client, auth_headers)
    response = client.post(
        f"/variants/{variant['id']}/schedule", headers=auth_headers, json={"publish_at": future_time()}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Cannot change variant from draft to scheduled"


def test_rejection_reason_and_edit_returns_to_draft(client, auth_headers):
    variant = create_variant(client, auth_headers)
    rejected = client.post(
        f"/variants/{variant['id']}/reject", headers=auth_headers, json={"reason": "The opening needs a clearer message."}
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejection_reason"] == "The opening needs a clearer message."

    edited = client.patch(
        f"/variants/{variant['id']}", headers=auth_headers, json={"content": "Quick take: A clearer message for readers.\n#Insights"}
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "draft"
    assert edited.json()["rejection_reason"] is None


def test_invalid_edit_and_status_transition_are_blocked(client, auth_headers):
    variant = create_variant(client, auth_headers)
    invalid_edit = client.patch(
        f"/variants/{variant['id']}", headers=auth_headers, json={"content": "word " * 80}
    )
    assert invalid_edit.status_code == 422
    assert "280 characters" in invalid_edit.json()["detail"]

    client.post(f"/variants/{variant['id']}/approve", headers=auth_headers)
    repeated = client.post(f"/variants/{variant['id']}/approve", headers=auth_headers)
    assert repeated.status_code == 409


def test_past_or_timezone_naive_schedule_is_blocked(client, auth_headers):
    variant = create_variant(client, auth_headers)
    client.post(f"/variants/{variant['id']}/approve", headers=auth_headers)
    naive = client.post(
        f"/variants/{variant['id']}/schedule", headers=auth_headers, json={"publish_at": "2030-01-01T12:00:00"}
    )
    assert naive.status_code == 422
    past = client.post(
        f"/variants/{variant['id']}/schedule",
        headers=auth_headers,
        json={"publish_at": "2020-01-01T12:00:00Z"},
    )
    assert past.status_code == 422


def test_other_user_cannot_review_variant(client, auth_headers):
    variant = create_variant(client, auth_headers)
    credentials = {"email": "reviewer@example.com", "password": "password123"}
    client.post("/auth/signup", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    other_headers = {"Authorization": f"Bearer {token}"}
    assert client.get(f"/variants/{variant['id']}", headers=other_headers).status_code == 404
    assert client.post(f"/variants/{variant['id']}/approve", headers=other_headers).status_code == 404
