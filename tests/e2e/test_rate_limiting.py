from app.auth.rbac import Role
from app.rate_limit import limiter


def test_route_rate_limit_is_enforced_for_public_bodies(client):
    limiter.reset()

    responses = [
        client.get(
            "/applications/public-bodies",
            headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
        )
        for _ in range(3)
    ]

    assert [response.status_code for response in responses] == [200, 200, 429]
    assert responses[2].headers["retry-after"]
    assert responses[2].headers["x-request-id"]
    assert responses[2].headers["x-correlation-id"]
