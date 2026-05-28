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


def test_200_returns_client_correspondence_recipient_flag_when_client_is_recipient(
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
    assert requested_application["isClientCorrespondenceRecipient"] is True
    assert requested_application["correspondenceRecipient"] is None


def test_200_returns_explicit_correspondence_recipient_from_stored_application(
    client, auth_token
):
    create_response = client.post(
        "/applications",
        json={
            "proceedings": [{"proceedingId": "TEST1"}],
            "isClientCorrespondenceRecipient": False,
            "client": {
                "clientFirstName": "Test",
                "clientLastName": "Surname",
                "dateOfBirth": "01-01-1990",
                "nationalInsuranceNumber": "AB12345A",
                "correspondenceAddressSource": "USE_SPECIFIED_ADDRESS",
                "correspondenceAddress": {
                    "addressLine1": "2 Example Lane",
                    "townOrCity": "London",
                    "postcode": "SW1A 1AA",
                },
                "hasNoFixedAbode": False,
                "homeAddress": {
                    "addressLine1": "1 Example Lane",
                    "addressLine2": "Flat 2",
                    "townOrCity": "London",
                    "county": "Greater London",
                    "postcode": "SW1A 1AA",
                },
            },
            "publicBodies": [{"publicBodyId": "Department for Transport"}],
            "deceased": {
                "deceasedFirstName": "Test",
                "deceasedLastName": "Surname",
                "deceasedDateOfBirth": "01-01-2000",
                "deceasedDateOfDeath": "01-01-2025",
                "coronersReference": "COR-2025-001",
                "furtherInformation": "Further details to be confirmed",
                "clientRelationshipToDeceased": "guardian",
            },
            "correspondenceRecipient": {
                "recipientType": "ORGANISATION",
                "recipientName": "Inquests Support Org",
            },
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    created_application = create_response.json()
    laa_reference = created_application["laaReference"]

    response = client.get(
        f"/applications/{laa_reference}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    requested_application = response.json()
    assert requested_application["isClientCorrespondenceRecipient"] is False
    assert requested_application["correspondenceRecipient"] == {
        "recipientType": "ORGANISATION",
        "recipientName": "Inquests Support Org",
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
