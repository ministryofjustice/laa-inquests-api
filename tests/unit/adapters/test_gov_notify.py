"""Unit tests for GovNotify adapter."""

from unittest.mock import Mock, patch
import pytest
from app.adapters.gov_notify import GovNotifyClient
from app.models.gov_notify_templates.application_submit_personalisation import (
    NotifyApplicationSubmitTemplatePersonalisation,
)
from app.config import Config


def test_gov_notify_client_sends_email_successfully():
    """
    Test that GovNotifyClient successfully sends an email via the notifications API.
    """
    mock_notifications_client = Mock()
    mock_response = {"id": "test-notification-id", "content": {"body": "test"}}
    mock_notifications_client.send_email_notification.return_value = mock_response

    personalisation = NotifyApplicationSubmitTemplatePersonalisation(
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
        deceased_has_other_related_applications="Yes",
        deceased_related_applications_information="Stuff",
        coroners_reference="COR-123",
        public_body_description="Test Department",
    )

    with patch(
        "app.adapters.gov_notify.NotificationsAPIClient"
    ) as mock_api_client_class:
        mock_api_client_class.return_value = mock_notifications_client

        client = GovNotifyClient()

        client.send_email(
            email_address="test@example.com",
            template_id="test-template-id",
            personalisation=personalisation,
        )

        mock_api_client_class.assert_called_once_with(Config.GOV_NOTIFY_API_KEY)
        mock_notifications_client.send_email_notification.assert_called_once_with(
            email_address="test@example.com",
            template_id="test-template-id",
            personalisation=personalisation.model_dump(),
        )


def test_gov_notify_client_raises_exception_on_api_error():
    """
    Test that GovNotifyClient raises an exception when the API returns an error.
    """
    mock_notifications_client = Mock()
    mock_notifications_client.send_email_notification.side_effect = Exception(
        "API Error: Invalid API key"
    )

    personalisation = NotifyApplicationSubmitTemplatePersonalisation(
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
        deceased_has_other_related_applications="Yes",
        deceased_related_applications_information="Stuff",
        coroners_reference="COR-123",
        public_body_description="Test Department",
    )

    with patch(
        "app.adapters.gov_notify.NotificationsAPIClient"
    ) as mock_api_client_class:
        mock_api_client_class.return_value = mock_notifications_client

        client = GovNotifyClient()

        with pytest.raises(Exception) as exc_info:
            client.send_email(
                email_address="test@example.com",
                template_id="test-template-id",
                personalisation=personalisation,
            )

        assert "API Error: Invalid API key" in str(exc_info.value)


def test_gov_notify_client_uses_config_api_key():
    """
    Test that GovNotifyClient uses the API key from Config.
    """
    mock_notifications_client = Mock()

    with patch(
        "app.adapters.gov_notify.NotificationsAPIClient"
    ) as mock_api_client_class:
        mock_api_client_class.return_value = mock_notifications_client

        GovNotifyClient()

        mock_api_client_class.assert_called_once_with(Config.GOV_NOTIFY_API_KEY)


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
