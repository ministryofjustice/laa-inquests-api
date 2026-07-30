def test_200_list_public_bodies_returns_seeded_record_with_id_and_description(
    client, auth_token
):
    response = client.get(
        "/applications/public-bodies",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    public_bodies = response.json()
    assert isinstance(public_bodies, list)
    assert len(public_bodies) == 1
    assert public_bodies[0]["publicBodyId"] == "Department for Transport"
    assert public_bodies[0]["publicBodyDescription"] == "Department for Transport"


def test_401_list_public_bodies_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.get("/applications/public-bodies")

    assert response.status_code == 401


def test_403_list_public_bodies_returns_403_when_caseworker_token(entra_auth_client):
    response = entra_auth_client.get(
        "/applications/public-bodies",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 403
