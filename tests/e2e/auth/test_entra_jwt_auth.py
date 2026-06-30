def test_200_read_all_applications_returns_200_when_valid_entra_token(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications",
        headers={"Authorization": "Bearer valid-entra-token"},
    )

    assert response.status_code == 200


def test_401_read_all_applications_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.get("/applications")

    assert response.status_code == 401


def test_401_read_all_applications_returns_401_when_bearer_token_is_invalid(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_403_read_all_applications_returns_403_when_scope_is_not_provider(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 403
