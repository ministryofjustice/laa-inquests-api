from app.models.application.index import Application
from sqlmodel import select


def test_200_read_application_by_reference_returns_expected_application(
    session, client, auth_token
):
    first_application_row = session.exec(select(Application)).first()
    first_application_laa_reference = int(
        first_application_row.__dict__["laa_reference"]
    )

    response = client.get(
        f"/applications/{first_application_laa_reference}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    requested_application = response.json()
    assert requested_application["laaReference"] == 1


def test_200_proceeding_details_included_on_application_response(
    session, client, auth_token
):
    first_application_row = session.exec(select(Application)).first()
    first_application_laa_reference = first_application_row.__dict__["laa_reference"]

    response = client.get(
        f"/applications/{first_application_laa_reference}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    requested_application = response.json()
    assert len(requested_application["proceedings"]) == 1


def test_200_client_addresses_included_on_application_response(
    session, client, auth_token
):
    first_application_row = session.exec(select(Application)).first()
    first_application_laa_reference = first_application_row.__dict__["laa_reference"]

    response = client.get(
        f"/applications/{first_application_laa_reference}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    requested_application = response.json()
    client_details = requested_application["client"]
    assert client_details["correspondenceAddressSource"] == "USE_CLIENT_HOME_ADDRESS"
    assert client_details["correspondenceAddress"] is None
    assert client_details["homeAddress"] == {
        "addressLine1": "1 Example Lane",
        "addressLine2": None,
        "townOrCity": "London",
        "county": None,
        "postcode": "SW1A 1AA",
    }


def test_404_read_application_returns_404_when_not_found(client, auth_token):
    response = client.get(
        "/applications/99999",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404
