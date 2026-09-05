"""Create a small end-to-end campaign against the locally running API."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:8000"
EMAIL = "demo@example.com"
PASSWORD = "demo-password-2026"


def request(method: str, path: str, payload: dict | None = None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(req) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"{method} {path} failed ({exc.code}): {detail}") from exc


def main() -> None:
    try:
        request("POST", "/auth/signup", {"email": EMAIL, "password": PASSWORD})
    except RuntimeError as exc:
        if "already" not in str(exc).lower() and "registered" not in str(exc).lower():
            raise

    login = request("POST", "/auth/login", {"email": EMAIL, "password": PASSWORD})
    token = login["access_token"]
    source = request(
        "POST",
        "/posts",
        {
            "title": "How durable publishing protects a social campaign",
            "markdown": (
                "A reliable campaign pipeline stores schedules before delivery, prevents duplicate "
                "publishing with idempotency keys, and records every attempt for operators. Human "
                "approval remains the final gate before automation begins."
            ),
        },
        token,
    )
    variants = request("POST", f"/posts/{source['id']}/variants", {"platforms": ["x", "linkedin"]}, token)
    publish_at = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    schedules = []
    for variant in variants:
        request("POST", f"/variants/{variant['id']}/approve", {}, token)
        schedules.append(request("POST", f"/variants/{variant['id']}/schedule", {"publish_at": publish_at}, token))

    print(json.dumps({"source_id": source["id"], "variant_ids": [v["id"] for v in variants], "schedule_ids": [s["id"] for s in schedules]}, indent=2))


if __name__ == "__main__":
    main()
