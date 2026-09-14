import uuid

import pytest
from sqlmodel import select

from app import api
from app.auth.rbac import Permission, get_current_user_permissions
from app.models.application.enums import MeritsDecision
from app.models.application.index import Application
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from tests.helpers.entra_auth import override_entra_auth_app_roles

pytestmark = pytest.mark.usefixtures("mock_gov_notify")


def _make_request_body(client_overrides=None):
    client = {
        "clientFirstName": "Test",
        "clientLastName": "Surname",
        "dateOfBirth": "1990-01-01",
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
            "deceasedDateOfBirth": "2000-01-01",
            "deceasedDateOfDeath": "2025-01-01",
            "coronersReference": "COR-2025-001",
            "furtherInformation": "Further details to be confirmed",
            "clientRelationshipToDeceased": "guardian",
        },
        "provider": {
            "officeId": "0U651L",
            "emailAddress": "provider@example.com",
        },
    }


class TestCreateApplication:
    def test_201_create_application_response_contains_expected_base_properties(
        self, client, auth_token
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
        assert isinstance(new_application["laaReference"], str)
        assert isinstance(new_application["createdAt"], str)
        assert isinstance(new_application["updatedAt"], str)
        assert isinstance(new_application["status"], str)
        assert isinstance(new_application["usedDelegatedFunctions"], bool)
        assert isinstance(new_application["applicationType"], str)
        assert isinstance(new_application["autoGrant"], bool)
        assert isinstance(new_application["overallDecision"], str)
        assert isinstance(new_application["proceeding"], dict)

    def test_201_create_application_response_contains_expected_proceeding_information(
        self, client, auth_token
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
        assert proceeding["substantiveCostLimitation"] == 0
        assert isinstance(proceeding["scopeDescription"], str)
        assert isinstance(proceeding["proceedingName"], str)
        assert isinstance(proceeding["proceedingDescription"], str)

    def test_201_responds_with_expected_client_details(self, client, auth_token):
        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
        )
        new_application = response.json()
        client_data = new_application["client"]
        assert isinstance(client_data["clientId"], int)
        assert client_data["clientFirstName"] == "Test"
        assert client_data["clientLastName"] == "Surname"
        assert client_data["clientLastNameAtBirth"] is None
        assert client_data["dateOfBirth"] == "1990-01-01"
        assert client_data["nationalInsuranceNumber"] == "AB12345A"
        assert client_data["correspondenceAddressSource"] == "USE_SPECIFIED_ADDRESS"
        assert client_data["correspondenceAddress"] == {
            "addressLine1": "2 Example Lane",
            "addressLine2": None,
            "townOrCity": "London",
            "county": None,
            "postcode": "SW1A 1AA",
        }
        assert new_application["client"]["correspondenceRecipient"] is None
        assert client_data["homeAddress"] == {
            "addressLine1": "1 Example Lane",
            "addressLine2": "Flat 2",
            "townOrCity": "London",
            "county": "Greater London",
            "postcode": "SW1A 1AA",
        }
        assert not client_data["hasAppliedPreviously"]

    def test_201_create_application_stores_authenticated_users_firm_code(
        self, client, auth_token, session
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

    def test_201_create_application_creates_history_event(
        self, client, auth_token, session
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

        history_event = session.exec(
            select(HistoryEvent).where(
                (HistoryEvent.application_id == application.application_id)
                & (
                    HistoryEvent.event_reference
                    == HistoryEventReference.APPLICATION_SUBMITTED
                )
            )
        ).one()

        assert (
            history_event.event_reference == HistoryEventReference.APPLICATION_SUBMITTED
        )
        assert history_event.actor == "provider@example.com"
        assert history_event.actor_type == ActorType.PROVIDER
        assert history_event.event_data is None
        assert history_event.application_id == application.application_id

    def test_201_create_application_can_omit_correspondence_address(
        self, client, auth_token
    ):
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
        assert (
            client_details["correspondenceAddressSource"] == "USE_CLIENT_HOME_ADDRESS"
        )
        assert client_details["correspondenceAddress"] is None

    def test_201_create_application_responds_with_expected_public_body_details(
        self, client, auth_token
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

    def test_201_create_application_response_includes_deceased_details(
        self, client, auth_token
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
        deceased = new_application["deceased"]
        assert isinstance(deceased["deceasedId"], int)
        assert deceased["deceasedFirstName"] == "Test"
        assert deceased["deceasedLastName"] == "Surname"
        assert deceased["deceasedDateOfBirth"] == "2000-01-01"
        assert deceased["deceasedDateOfDeath"] == "2025-01-01"
        assert deceased["coronersReference"] == "COR-2025-001"
        assert deceased["furtherInformation"] == "Further details to be confirmed"
        assert deceased["clientRelationshipToDeceased"] == "guardian"

    def test_201_create_application_response_contains_coroners_letter(
        self, client, auth_token
    ):
        upload_response = client.post(
            "/applications/upload-coroners-letter",
            files={
                "file": (
                    "test-file_abc123.pdf",
                    b"test content",
                    "application/pdf",
                )
            },
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
        self, client, auth_token
    ):
        body = _make_request_body(
            {
                "correspondenceAddressSource": "USE_CLIENT_HOME_ADDRESS",
                "homeAddress": None,
            }
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
        self, client, auth_token
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
        self, client, auth_token
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
        self, client, auth_token
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
        self, client, auth_token
    ):
        body = _make_request_body()
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
        assert response.json()["client"]["correspondenceRecipient"] == {
            "recipientType": "ORGANISATION",
            "recipientName": "Inquests Support Org",
        }

    def test_201_create_application_response_includes_provider_email(
        self, client, auth_token
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
        assert response.json()["provider"]["emailAddress"] == "provider@example.com"

    def test_422_create_application_rejected_when_provider_email_missing(
        self, client, auth_token
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

    def test_422_create_application_fails_without_provider(self, client, auth_token):
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

    def test_422_create_application_fails_without_office_id(self, client, auth_token):
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
        self, client, auth_token, session, mock_gov_notify
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

        mock_gov_notify.send_application_submit_confirmation_email.side_effect = (
            Exception("GovNotify API unavailable")
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


class TestCreateApplicationRbac:
    def test_201_create_application_with_provider_application_user_app_role(
        self, client, auth_token
    ):
        override_entra_auth_app_roles({"Inquests - Provider Application User"})

        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
        )
        assert response.status_code == 201

    def test_403_create_application_with_app_role_missing_create_permission(
        self, client, auth_token
    ):
        override_entra_auth_app_roles({"Inquests - Provider Claims User"})

        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
        )
        assert response.status_code == 403

    def test_403_create_application_with_unmapped_app_role(self, client, auth_token):
        override_entra_auth_app_roles({"Some Unknown Role"})

        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
        )
        assert response.status_code == 403

    def test_201_create_application_with_permission_override(self, client, auth_token):
        def get_current_user_permissions_override():
            return {Permission.APPLICATION_CREATE}

        api.dependency_overrides[get_current_user_permissions] = (
            get_current_user_permissions_override
        )

        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
        )
        assert response.status_code == 201

    def test_403_create_application_with_empty_permission_override(
        self, client, auth_token
    ):
        def get_current_user_permissions_override():
            return set()

        api.dependency_overrides[get_current_user_permissions] = (
            get_current_user_permissions_override
        )

        response = client.post(
            "/applications",
            json=_make_request_body(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
        )
        assert response.status_code == 403
