from app.services.ingestion import IngestedArticle
from app.services.variants import validate_variant


def test_markdown_ingestion_and_distinct_variants(client, auth_headers):
    created = client.post(
        "/posts",
        headers=auth_headers,
        json={
            "title": "Reliable AI",
            "markdown": (
                "Reliable AI starts with measurable requirements. "
                "Deterministic validation catches predictable failures. "
                "Human review remains important before publication."
            ),
        },
    )
    assert created.status_code == 201
    generated = client.post(
        f"/posts/{created.json()['id']}/variants",
        headers=auth_headers,
        json={"platforms": ["x", "linkedin"]},
    )
    assert generated.status_code == 201
    variants = generated.json()
    assert {item["platform"] for item in variants} == {"x", "linkedin"}
    by_platform = {item["platform"]: item["content"] for item in variants}
    assert by_platform["x"].startswith("Quick take:")
    assert len(by_platform["x"]) <= 280
    assert "Key takeaways from the article:" in by_platform["linkedin"]
    assert "Which takeaway stands out to you?" in by_platform["linkedin"]
    assert by_platform["linkedin"].count("\n") > by_platform["x"].count("\n")
    assert all(item["status"] == "draft" for item in variants)


def test_url_ingestion_stores_fetched_copy(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.api.posts.fetch_article",
        lambda _: IngestedArticle(title="Fetched article", content="A permanent stored copy of the fetched article body."),
    )
    response = client.post("/posts", headers=auth_headers, json={"url": "https://example.com/article"})
    assert response.status_code == 201
    assert response.json()["title"] == "Fetched article"
    assert response.json()["content"] == "A permanent stored copy of the fetched article body."


def test_posts_are_private_to_the_owner(client, auth_headers):
    created = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "Private post", "markdown": "This content belongs only to the first authenticated user."},
    ).json()
    second = {"email": "second@example.com", "password": "password123"}
    client.post("/auth/signup", json=second)
    token = client.post("/auth/login", json=second).json()["access_token"]
    response = client.get(f"/posts/{created['id']}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_constraint_validation_names_broken_rules():
    for platform, content, expected in (
        ("x", "word " * 80, "280 characters"),
        ("linkedin", "This is professional lol absolutely", "professional tone"),
    ):
        try:
            validate_variant(platform, content)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"Expected invalid {platform} variant to be rejected")
