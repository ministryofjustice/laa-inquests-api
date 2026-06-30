from fastapi.testclient import TestClient


def test_post_token_returns_404_when_local_auth_is_removed(client: TestClient):
    response = client.post(
        "/token",
        data={"username": "fake_user", "password": "incorrect"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 404
