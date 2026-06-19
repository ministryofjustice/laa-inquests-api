"""Unit tests for GovNotifyAdapter."""

from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest

from app.adapters.gov_notify import GovNotifyAdapter
from app.config import Config
from app.models.application.enums import AddressSource, ProceedingId, PublicBodyId
from app.models.application.index import (
    Address,
    Application,
    ApplicationProceeding,
    ApplicationPublicBody,
    Client,
    Deceased,
    Proceeding,
    Provider,
    PublicBody,
)
from app.models.gov_notify_templates.application_refuse_personalisation import (
    NotifyApplicationRefuseTemplatePersonalisation,
)
from app.models.gov_notify_templates.application_submit_personalisation import (
    NotifyApplicationSubmitTemplatePersonalisation,
)


def _create_test_application_and_proceeding():
    utc = ZoneInfo("UTC")
    home_address = Address(
        address_id=1,
        address_line_1="123 Test St",
        town_or_city="London",
        postcode="SW1A 1AA",
    )
    client = Client(
        client_id=1,
        client_first_name="Jane",
        client_last_name="Doe",
        date_of_birth="15-06-1985",
        correspondence_address_source=AddressSource.USE_CLIENT_HOME_ADDRESS,
        home_address_id=1,
        home_address=home_address,
        is_client_correspondence_recipient=True,
    )
    deceased = Deceased(
        deceased_id=1,
        client_id=1,
        deceased_first_name="Robert",
        deceased_last_name="Johnson",
        deceased_date_of_birth="01-01-1950",
        deceased_date_of_death="31-12-2025",
        coroners_reference="COR-2025-123",
        further_information="Test info",
        client_relationship_to_deceased="Son",
    )
    proceeding = Proceeding(
        id=1,
        proceeding_id=ProceedingId.TEST1,
        proceeding_description="Inquest into death",
        matter_type="INQUESTS",
    )
    application_proceeding = ApplicationProceeding(
        application_proceeding_id=1,
        laa_reference=12345,
        proceeding_id=ProceedingId.TEST1,
        proceeding=proceeding,
        merits_decision="REFUSED",
        reason_for_refusal="NOT_IN_SCOPE",
        justification="The matter does not meet scope requirements.",
    )
    public_body = PublicBody(
        id=1,
        public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        public_body_description="Department for Transport",
    )
    application_public_body = ApplicationPublicBody(
        application_public_body_id=1,
        laa_reference=12345,
        public_body_id=PublicBodyId.DEPARTMENT_FOR_TRANSPORT,
        public_body=public_body,
    )
    provider = Provider(provider_id=1, firm_code="ABC123", office_id="001")
    application = Application(
        laa_reference=12345,
        client_id=1,
        client=client,
        deceased_id=1,
        deceased=deceased,
        provider_id=1,
        provider=provider,
        proceedings=[application_proceeding],
        public_bodies=[application_public_body],
        created_at=datetime(2026, 6, 18, 14, 3, tzinfo=utc),
    )
    return application, application_proceeding


def test_gov_notify_adapter_sends_refusal_email_successfully():
    application, proceeding = _create_test_application_and_proceeding()
    mock_notifications_client = Mock()
    mock_notifications_client.send_email_notification.return_value = {
        "id": "test-notification-id"
    }

    with (
        patch("app.adapters.gov_notify.NotificationsAPIClient") as mock_api_client,
        patch.object(
            Config,
            "GOV_NOTIFY_APPLICATION_REFUSE_TEMPLATE_ID",
            "test-refuse-template-id",
        ),
    ):
        mock_api_client.return_value = mock_notifications_client

        adapter = GovNotifyAdapter()
        adapter.send_application_refused_decision_email(
            application, proceeding, "provider@example.com"
        )

        mock_api_client.assert_called_once_with(Config.GOV_NOTIFY_API_KEY)
        call_kwargs = mock_notifications_client.send_email_notification.call_args.kwargs
        assert call_kwargs["email_address"] == "provider@example.com"
        assert call_kwargs["template_id"] == "test-refuse-template-id"
        assert isinstance(
            call_kwargs["personalisation"],
            NotifyApplicationRefuseTemplatePersonalisation,
        )
        assert call_kwargs["personalisation"].laa_reference == "12345"
        assert (
            call_kwargs["personalisation"].application_submitted_at
            == "18 June 2026 14:03 UTC"
        )


def test_gov_notify_adapter_sends_confirmation_email_successfully():
    application, _ = _create_test_application_and_proceeding()
    mock_notifications_client = Mock()
    mock_notifications_client.send_email_notification.return_value = {
        "id": "test-notification-id"
    }

    with (
        patch("app.adapters.gov_notify.NotificationsAPIClient") as mock_api_client,
        patch.object(
            Config,
            "GOV_NOTIFY_APPLICATION_SUBMIT_TEMPLATE_ID",
            "test-submit-template-id",
        ),
        patch.object(
            Config,
            "GOV_NOTIFY_APPLICATION_REFUSE_TEMPLATE_ID",
            "test-refuse-template-id",
        ),
    ):
        mock_api_client.return_value = mock_notifications_client

        adapter = GovNotifyAdapter()
        adapter.send_application_submit_confirmation_email(
            application, "provider@example.com"
        )

        mock_api_client.assert_called_once_with(Config.GOV_NOTIFY_API_KEY)
        call_kwargs = mock_notifications_client.send_email_notification.call_args.kwargs
        assert call_kwargs["email_address"] == "provider@example.com"
        assert call_kwargs["template_id"] == "test-submit-template-id"
        assert isinstance(call_kwargs["personalisation"], dict)
        assert call_kwargs["personalisation"]["laa_reference"] == "12345"
        assert call_kwargs["personalisation"]["client_first_name"] == "Jane"


def test_gov_notify_adapter_raises_exception_on_api_error():
    application, proceeding = _create_test_application_and_proceeding()
    mock_notifications_client = Mock()
    mock_notifications_client.send_email_notification.side_effect = Exception(
        "API Error: Invalid API key"
    )

    with patch("app.adapters.gov_notify.NotificationsAPIClient") as mock_api_client:
        mock_api_client.return_value = mock_notifications_client

        adapter = GovNotifyAdapter()

        with pytest.raises(Exception) as exc_info:
            adapter.send_application_refused_decision_email(
                application, proceeding, "provider@example.com"
            )

        assert "API Error: Invalid API key" in str(exc_info.value)


def test_gov_notify_adapter_uses_config_api_key():
    mock_notifications_client = Mock()

    with patch("app.adapters.gov_notify.NotificationsAPIClient") as mock_api_client:
        mock_api_client.return_value = mock_notifications_client

        GovNotifyAdapter()

        mock_api_client.assert_called_once_with(Config.GOV_NOTIFY_API_KEY)


def test_email_personalisation_rejects_missing_required_fields():
    """
    Test that NotifyApplicationSubmitTemplatePersonalisation model rejects creation with missing required fields.
    """
    with pytest.raises(Exception):
        NotifyApplicationSubmitTemplatePersonalisation(
            laa_reference="12345",
            client_first_name="Test",
        )


def test_email_personalisation_rejects_extra_fields():
    """
    Test that NotifyApplicationSubmitTemplatePersonalisation model rejects extra/unexpected fields.
    """
    with pytest.raises(Exception):
        NotifyApplicationSubmitTemplatePersonalisation(
            laa_reference="12345",
            client_first_name="Test",
            client_last_name="User",
            date_of_birth="01-01-1990",
            has_applied_previously="No",
            client_home_address="Test Address",
            correspondence_address="Test Address",
            correspondence_recipient="Client",
            client_relationship_to_deceased="Son",
            proceeding_description="Test Proceeding",
            matter_type="INQUESTS",
            deceased_first_name="Test",
            deceased_last_name="Deceased",
            deceased_date_of_birth="01-01-1950",
            deceased_date_of_death="01-01-2025",
            coroners_reference="COR-123",
            public_body_description="Test Department",
            unexpected_field="This should not be allowed",
        )
