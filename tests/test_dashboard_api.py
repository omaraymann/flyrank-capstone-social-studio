from datetime import datetime, timedelta, timezone


def _schedule(client, headers):
    post = client.post(
        "/posts",
        headers=headers,
        json={"title": "Dashboard test", "markdown": "Dashboard users can inspect their own durable schedules."},
    ).json()
    variant = client.post(
        f"/posts/{post['id']}/variants",
        headers=headers,
        json={"platforms": ["x"]},
    ).json()[0]
    client.post(f"/variants/{variant['id']}/approve", headers=headers)
    return client.post(
        f"/variants/{variant['id']}/schedule",
        headers=headers,
        json={"publish_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()},
    ).json()


def test_dashboard_origin_is_allowed(client):
    response = client.options(
        "/posts",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_schedule_list_is_owned(client, auth_headers):
    schedule = _schedule(client, auth_headers)
    response = client.get("/schedules", headers=auth_headers)
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [schedule["id"]]

    credentials = {"email": "dashboard-other@example.com", "password": "password123"}
    client.post("/auth/signup", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    other = client.get("/schedules", headers={"Authorization": f"Bearer {token}"})
    assert other.json() == []
