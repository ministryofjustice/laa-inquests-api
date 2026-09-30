from app.auth.rbac import Role
from app.rate_limit import create_rate_limiter


def test_rate_limit_is_shared_across_routes_and_exempts_health(client):
    previous_rate_limiter = client.app.state.rate_limiter
    rate_limiter = create_rate_limiter(2, 15)
    client.app.state.rate_limiter = rate_limiter

    try:
        health_responses = [client.get("/health") for _ in range(3)]
        docs_responses = [client.get("/") for _ in range(3)]
        applications_response = client.get(
            "/applications/public-bodies",
            headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
        )
        claims_response = client.post(
            "/claims/evidence",
            files={"file": ("evidence.pdf", b"test content", "application/pdf")},
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )
        second_applications_response = client.get(
            "/applications/public-bodies",
            headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
        )

        assert [response.status_code for response in health_responses] == [200] * 3
        assert [response.status_code for response in docs_responses] == [200] * 3
        assert applications_response.status_code == 200
        assert claims_response.status_code == 201
        assert second_applications_response.status_code == 429
        assert second_applications_response.json() == {"detail": "Rate limit exceeded"}

    finally:
        client.app.state.rate_limiter = previous_rate_limiter
        rate_limiter.close()
