import uuid

import pytest
from sqlmodel import select

from app.models.application.enums import MeritsDecision
from app.models.application.index import Application

pytestmark = pytest.mark.usefixtures("mock_gov_notify")


def _make_request_body(client_overrides=None):
    client = {
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
        "isClientCorrespondenceRecipient": True,
    }
    if client_overrides:
        client.update(client_overrides)
    return {
        "coronersLetterId": str(uuid.uuid4()),
        "proceeding": {"proceedingId": "IQOT"},
        "client": client,
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
            "officeId": "001",
            "emailAddress": "provider@example.com",
        },
    }


def test_201_create_application_response_contains_expected_base_properties(
    client, auth_token
):
    response = client.post(
        "/applications",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )
    assert response.status_code == 201
    new_application = response.json()
    assert isinstance(new_application["laaReference"], int)
    assert isinstance(new_application["createdAt"], str)
    assert isinstance(new_application["updatedAt"], str)
    assert isinstance(new_application["status"], str)
    assert isinstance(new_application["usedDelegatedFunctions"], bool)
    assert isinstance(new_application["applicationType"], str)
    assert isinstance(new_application["autoGrant"], bool)
    assert isinstance(new_application["overallDecision"], str)
    assert isinstance(new_application["proceeding"], dict)


def test_201_create_application_response_contains_expected_proceeding_information(
    client, auth_token
):
    response = client.post(
        "/applications",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )
    new_application = response.json()
    proceeding = new_application["proceeding"]
    assert proceeding["proceedingId"] == "IQOT"
    assert proceeding["categoryOfLaw"] == "INQUESTS"
    assert proceeding["matterType"] == "INQUESTS"
    assert proceeding["levelOfService"] == "FULL_REPRESENTATION"
    assert proceeding["certificateType"] == "SUBSTANTIVE"
    assert proceeding["clientInvolvementType"] == "RESPONDENT"
    assert proceeding["meritsDecision"] == MeritsDecision.PENDING
    assert isinstance(proceeding["substantiveCostLimitation"], int)
    assert isinstance(proceeding["scopeDescription"], str)
    assert isinstance(proceeding["proceedingName"], str)
    assert isinstance(proceeding["proceedingDescription"], str)


def test_201_responds_with_expected_client_details(client, auth_token):
    response = client.post(
        "/applications",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )
    new_application = response.json()
    client = new_application["client"]
    assert isinstance(client["clientId"], int)
    assert client["clientFirstName"] == "Test"
    assert client["clientLastName"] == "Surname"
    assert client["clientLastNameAtBirth"] is None
    assert client["dateOfBirth"] == "01-01-1990"
    assert client["nationalInsuranceNumber"] == "AB12345A"
    assert client["correspondenceAddressSource"] == "USE_SPECIFIED_ADDRESS"
    assert client["correspondenceAddress"] == {
        "addressLine1": "2 Example Lane",
        "addressLine2": None,
        "townOrCity": "London",
        "county": None,
        "postcode": "SW1A 1AA",
    }
    assert new_application["client"]["isClientCorrespondenceRecipient"] is True
    assert new_application["client"]["correspondenceRecipient"] is None
    assert client["homeAddress"] == {
        "addressLine1": "1 Example Lane",
        "addressLine2": "Flat 2",
        "townOrCity": "London",
        "county": "Greater London",
        "postcode": "SW1A 1AA",
    }
    assert not client["hasAppliedPreviously"]


def test_201_create_application_stores_authenticated_users_firm_code(
    client, auth_token, session
):
    response = client.post(
        "/applications",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    laa_reference = response.json()["laaReference"]
    application = session.exec(
        select(Application).where(Application.laa_reference == laa_reference)
    ).one()
    assert application.provider.firm_code == "0A123B"


def test_201_create_application_can_omit_correspondence_address(client, auth_token):
    request_body = _make_request_body(
        {"correspondenceAddressSource": "USE_CLIENT_HOME_ADDRESS"}
    )
    request_body["client"].pop("correspondenceAddress")

    response = client.post(
        "/applications",
        json=request_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    client_details = response.json()["client"]
    assert client_details["correspondenceAddressSource"] == "USE_CLIENT_HOME_ADDRESS"
    assert client_details["correspondenceAddress"] is None


def test_201_create_application_responds_with_expected_public_body_details(
    client, auth_token
):
    response = client.post(
        "/applications",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )
    new_application = response.json()
    assert len(new_application["publicBodies"]) == 1
    public_body = new_application["publicBodies"][0]
    assert public_body["publicBodyDescription"] == "Department for Transport"


def test_201_create_application_response_includes_deceased_details(client, auth_token):
    response = client.post(
        "/applications",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )
    new_application = response.json()
    deceased = new_application["deceased"]
    assert isinstance(deceased["deceasedId"], int)
    assert deceased["deceasedFirstName"] == "Test"
    assert deceased["deceasedLastName"] == "Surname"
    assert deceased["deceasedDateOfBirth"] == "01-01-2000"
    assert deceased["deceasedDateOfDeath"] == "01-01-2025"
    assert deceased["coronersReference"] == "COR-2025-001"
    assert deceased["furtherInformation"] == "Further details to be confirmed"
    assert deceased["clientRelationshipToDeceased"] == "guardian"


def test_201_create_application_response_contains_coroners_letter(client, auth_token):
    upload_response = client.post(
        "/applications/upload-coroners-letter",
        files={"file": ("test-file_abc123.pdf", b"test content", "application/pdf")},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert upload_response.status_code == 201
    coroners_letter_id = upload_response.json()["coronersLetterId"]

    body = _make_request_body()
    body["coronersLetterId"] = coroners_letter_id

    response = client.post(
        "/applications",
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )
    assert response.status_code == 201
    new_application = response.json()
    assert new_application["coronersLetter"] is not None
    assert new_application["coronersLetter"]["fileName"] == "test-file_abc123.pdf"


def test_422_rejected_when_has_no_fixed_abode_is_false_and_home_address_is_absent(
    client, auth_token
):
    body = _make_request_body(
        {"correspondenceAddressSource": "USE_CLIENT_HOME_ADDRESS", "homeAddress": None}
    )
    del body["client"]["correspondenceAddress"]

    response = client.post(
        "/applications",
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_422_rejected_when_has_no_fixed_abode_is_true_and_home_address_is_provided(
    client, auth_token
):
    body = _make_request_body({"hasNoFixedAbode": True})

    response = client.post(
        "/applications",
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_201_accepted_when_has_no_fixed_abode_is_true_and_no_home_address_provided(
    client, auth_token
):
    body = _make_request_body(
        {
            "hasNoFixedAbode": True,
            "correspondenceAddressSource": "USE_SPECIFIED_ADDRESS",
        }
    )
    body["client"].pop("homeAddress")

    response = client.post(
        "/applications",
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    client_data = response.json()["client"]
    assert client_data["hasNoFixedAbode"] is True
    assert client_data["homeAddress"] is None


def test_201_accepted_when_has_no_fixed_abode_is_false_and_home_address_is_provided(
    client, auth_token
):
    response = client.post(
        "/applications",
        json=_make_request_body({"hasNoFixedAbode": False}),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    client_data = response.json()["client"]
    assert client_data["hasNoFixedAbode"] is False
    assert client_data["homeAddress"] is not None
    assert client_data["homeAddress"]["addressLine1"] == "1 Example Lane"


def test_201_create_application_includes_explicit_correspondence_recipient(
    client, auth_token
):
    body = _make_request_body()
    body["client"]["isClientCorrespondenceRecipient"] = False
    body["client"]["correspondenceRecipient"] = {
        "recipientType": "ORGANISATION",
        "recipientName": "Inquests Support Org",
    }

    response = client.post(
        "/applications",
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    assert response.json()["client"]["isClientCorrespondenceRecipient"] is False
    assert response.json()["client"]["correspondenceRecipient"] == {
        "recipientType": "ORGANISATION",
        "recipientName": "Inquests Support Org",
    }


def test_422_rejected_when_client_is_recipient_and_correspondence_recipient_provided(
    client, auth_token
):
    body = _make_request_body()
    body["client"]["correspondenceRecipient"] = {
        "recipientType": "PERSON",
        "recipientName": "Someone Else",
    }

    response = client.post(
        "/applications",
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_201_create_application_response_includes_provider_email(client, auth_token):
    response = client.post(
        "/applications",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    assert response.json()["provider"]["emailAddress"] == "provider@example.com"


def test_422_create_application_rejected_when_provider_email_missing(
    client, auth_token
):
    body = _make_request_body()
    del body["provider"]["emailAddress"]

    response = client.post(
        "/applications",
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_422_rejected_when_client_is_not_recipient_and_correspondence_recipient_missing(
    client, auth_token
):
    body = _make_request_body()
    body["client"]["isClientCorrespondenceRecipient"] = False

    response = client.post(
        "/applications",
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_422_rejected_when_is_client_correspondence_recipient_is_missing(
    client, auth_token
):
    body = _make_request_body()
    del body["client"]["isClientCorrespondenceRecipient"]

    response = client.post(
        "/applications",
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_422_create_application_fails_without_provider(client, auth_token):
    body = _make_request_body()
    del body["provider"]

    response = client.post(
        "/applications",
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_422_create_application_fails_without_office_id(client, auth_token):
    body = _make_request_body()
    del body["provider"]["officeId"]

    response = client.post(
        "/applications",
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_500_create_application_rolls_back_when_gov_notify_fails(
    client, auth_token, session, mock_gov_notify
):
    """
    Test that application creation rolls back when GovNotify email sending fails.

    This test verifies the critical requirement that email sending is atomic with
    application creation - if the email fails, the entire transaction must rollback.

    Verifies:
    - 500 response when GovNotify fails
    - Application is NOT created in database
    - Transaction rollback occurs correctly
    """
    initial_count = len(session.exec(select(Application)).all())

    mock_gov_notify.send_application_submit_confirmation_email.side_effect = Exception(
        "GovNotify API unavailable"
    )

    response = client.post(
        "/applications",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "An internal server error occurred"}

    final_count = len(session.exec(select(Application)).all())
    assert final_count == initial_count, (
        f"Application was created despite email failure. "
        f"Initial count: {initial_count}, Final count: {final_count}"
    )
