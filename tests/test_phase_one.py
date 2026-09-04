def test_signup_and_login(client):
    credentials = {"email": "omar@example.com", "password": "password123"}
    assert client.post("/auth/signup", json=credentials).status_code == 201
    login = client.post("/auth/login", json=credentials)
    assert login.status_code == 200
    assert "access_token" in login.json()
