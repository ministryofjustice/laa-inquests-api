import uuid

import pytest
from sqlmodel import select

from app.models.application.index import Application, CoronersLetter

pytestmark = pytest.mark.usefixtures("mock_gov_notify")


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
    proceeding = requested_application["proceedings"][0]
    assert isinstance(proceeding["proceedingName"], str)
    assert isinstance(proceeding["proceedingDescription"], str)


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
    assert requested_application["client"]["isClientCorrespondenceRecipient"] is True
    assert requested_application["client"]["correspondenceRecipient"] is None


def test_200_returns_explicit_correspondence_recipient_from_stored_application(
    client, auth_token
):
    create_response = client.post(
        "/applications",
        json={
            "coronersLetterId": str(uuid.uuid4()),
            "proceedings": [{"proceedingId": "IQOT"}],
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
                "isClientCorrespondenceRecipient": False,
                "correspondenceRecipient": {
                    "recipientType": "ORGANISATION",
                    "recipientName": "Inquests Support Org",
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
            "provider": {
                "firmCode": "0A123B",
                "officeId": "001",
                "emailAddress": "provider@example.com",
            },
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert create_response.status_code == 201
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
    assert requested_application["client"]["isClientCorrespondenceRecipient"] is False
    assert requested_application["client"]["correspondenceRecipient"] == {
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


def test_200_get_application_includes_provider_email(session, client, auth_token):
    first_application_row = session.exec(select(Application)).first()
    laa_reference = first_application_row.__dict__["laa_reference"]

    response = client.get(
        f"/applications/{laa_reference}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 200
    assert response.json()["provider"]["emailAddress"] == "test@example.com"


def test_200_provider_details_included_on_application_response(
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

    provider = response.json()["provider"]
    assert provider["firmName"] == "Test Firm Name"
    assert provider["accountNumber"] == "0U651L"


def test_200_provider_fields_are_null_when_provider_api_unavailable(
    session, auth_token
):
    from unittest.mock import MagicMock

    from fastapi.testclient import TestClient

    from app import api
    from app.db import get_session
    from app.routers.applications import get_provider_details_port

    mock_port = MagicMock()
    mock_port.get_firm_name.return_value = None

    original_overrides = api.dependency_overrides.copy()
    api.dependency_overrides[get_provider_details_port] = lambda: mock_port

    try:
        with TestClient(api) as test_client:
            api.dependency_overrides[get_session] = lambda: session
            first_application_row = session.exec(select(Application)).first()
            response = test_client.get(
                f"/applications/{first_application_row.laa_reference}",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"Bearer {auth_token}",
                },
            )
    finally:
        api.dependency_overrides = original_overrides

    assert response.json()["provider"]["firmName"] is None


def test_200_read_application_response_coroners_letter_is_none_when_no_letter_exists(
    session, client, auth_token
):
    first_application_row = session.exec(select(Application)).first()
    laa_reference = first_application_row.__dict__["laa_reference"]

    response = client.get(
        f"/applications/{laa_reference}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 200
    assert response.json()["coronersLetter"] is None


def test_200_read_application_response_includes_coroners_letter_file_name(
    session, client, auth_token
):
    first_application_row = session.exec(select(Application)).first()
    laa_reference = first_application_row.__dict__["laa_reference"]

    coroners_letter = CoronersLetter(
        sds_file_name="sds-abc123.pdf",
        file_name="test-document.pdf",
    )
    session.add(coroners_letter)
    session.commit()
    session.refresh(coroners_letter)

    first_application_row.coroners_letter_id = coroners_letter.coroners_letter_id
    session.add(first_application_row)
    session.commit()

    response = client.get(
        f"/applications/{laa_reference}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 200
    assert response.json()["coronersLetter"]["fileName"] == "test-document.pdf"
