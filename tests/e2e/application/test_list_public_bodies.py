import pytest

from app.auth.rbac import Role


def test_200_list_public_bodies_returns_seeded_record_with_id_and_description(client):
    response = client.get(
        "/applications/public-bodies",
        headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
    )

    assert response.status_code == 200
    public_bodies = response.json()
    assert isinstance(public_bodies, list)
    assert len(public_bodies) == 2
    assert public_bodies[0]["publicBodyId"] == "Department of Health and Social Care"
    assert (
        public_bodies[0]["publicBodyDescription"]
        == "Department of Health and Social Care"
    )


def test_200_list_public_bodies_returns_results_sorted_alphabetically_ignoring_department_for_of(
    client,
):
    response = client.get(
        "/applications/public-bodies",
        headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
    )

    assert response.status_code == 200
    descriptions = [
        public_body["publicBodyDescription"] for public_body in response.json()
    ]
    assert descriptions == [
        "Department of Health and Social Care",
        "Department for Transport",
    ]


def test_401_list_public_bodies_returns_401_when_no_authorization_header(
    client,
):
    response = client.get("/applications/public-bodies")

    assert response.status_code == 401


def test_200_list_public_bodies_returns_200_when_caseworker_token(
    client,
):
    response = client.get(
        "/applications/public-bodies",
        headers={"Authorization": "Bearer Caseworker No Role"},
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "provider_token",
    [Role.PROVIDER_APPLICATION_USER.value, Role.PROVIDER_CLAIMS_USER.value],
)
def test_200_list_public_bodies_returns_200_when_provider_token(client, provider_token):
    response = client.get(
        "/applications/public-bodies",
        headers={"Authorization": f"Bearer {provider_token}"},
    )

    assert response.status_code == 200
