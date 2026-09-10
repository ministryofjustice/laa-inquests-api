from tests.helpers.provider_details import (
    override_provider_details_port_with_error,
    override_provider_details_port_with_provider_offices,
)


def test_200_list_provider_offices_returns_expected_response_shape(client, auth_token):
    override_provider_details_port_with_provider_offices()

    response = client.get(
        "/applications/provider-offices/123",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "officeCode": "0A123A",
            "address": {
                "addressLine1": "1 Test Street",
                "addressLine2": "",
                "townOrCity": "London",
                "county": "",
                "postcode": "SW1A 1AA",
            },
        }
    ]


def test_500_list_provider_offices_when_provider_details_lookup_fails(
    client, auth_token
):
    override_provider_details_port_with_error()

    response = client.get(
        "/applications/provider-offices/123",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 500
    assert (
        response.json()["detail"]
        == "Failed to retrieve provider offices from provider details service"
    )


def test_403_list_provider_offices_when_caseworker_token(entra_auth_client):
    response = entra_auth_client.get(
        "/applications/provider-offices/123",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 403
