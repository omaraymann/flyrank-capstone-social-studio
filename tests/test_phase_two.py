from app.services.ingestion import IngestedArticle
from app.services.variants import validate_variant


def test_markdown_ingestion_and_distinct_variants(client, auth_headers):
    created = client.post(
        "/posts",
        headers=auth_headers,
        json={"title": "Reliable AI", "markdown": "A practical article about building reliable artificial intelligence systems."},
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
    assert variants[0]["content"] != variants[1]["content"]
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
