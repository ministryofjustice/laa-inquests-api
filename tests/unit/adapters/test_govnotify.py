"""Unit tests for GovNotify adapter."""

from unittest.mock import Mock, patch
import pytest
from app.adapters.govnotify import GovNotifyClient
from app.models.notifications.personalisation import EmailPersonalisation
from app.config import Config


def test_govnotify_client_sends_email_successfully():
    """
    Test that GovNotifyClient successfully sends an email via the notifications API.
    """
    # Arrange
    mock_notifications_client = Mock()
    mock_response = {"id": "test-notification-id", "content": {"body": "test"}}
    mock_notifications_client.send_email_notification.return_value = mock_response

    personalisation = EmailPersonalisation(
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
        feedback_link="https://example.com",
    )

    with patch(
        "app.adapters.govnotify.NotificationsAPIClient"
    ) as mock_api_client_class:
        mock_api_client_class.return_value = mock_notifications_client

        client = GovNotifyClient()

        # Act
        client.send_email(
            email_address="test@example.com",
            template_id="test-template-id",
            personalisation=personalisation,
        )

        # Assert
        mock_api_client_class.assert_called_once_with(Config.GOVNOTIFY_API_KEY)
        mock_notifications_client.send_email_notification.assert_called_once_with(
            email_address="test@example.com",
            template_id="test-template-id",
            personalisation=personalisation.model_dump(),
        )


def test_govnotify_client_raises_exception_on_api_error():
    """
    Test that GovNotifyClient raises an exception when the API returns an error.
    """
    # Arrange
    mock_notifications_client = Mock()
    mock_notifications_client.send_email_notification.side_effect = Exception(
        "API Error: Invalid API key"
    )

    personalisation = EmailPersonalisation(
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
        feedback_link="https://example.com",
    )

    with patch(
        "app.adapters.govnotify.NotificationsAPIClient"
    ) as mock_api_client_class:
        mock_api_client_class.return_value = mock_notifications_client

        client = GovNotifyClient()

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            client.send_email(
                email_address="test@example.com",
                template_id="test-template-id",
                personalisation=personalisation,
            )

        assert "API Error: Invalid API key" in str(exc_info.value)


def test_govnotify_client_uses_config_api_key():
    """
    Test that GovNotifyClient uses the API key from Config.
    """
    # Arrange
    mock_notifications_client = Mock()

    with patch(
        "app.adapters.govnotify.NotificationsAPIClient"
    ) as mock_api_client_class:
        mock_api_client_class.return_value = mock_notifications_client

        # Act
        GovNotifyClient()

        # Assert - verify API key from config is used
        mock_api_client_class.assert_called_once_with(Config.GOVNOTIFY_API_KEY)


def test_email_personalisation_rejects_missing_required_fields():
    """
    Test that EmailPersonalisation model rejects creation with missing required fields.
    """
    # Act & Assert - missing required fields should raise validation error
    with pytest.raises(Exception):  # Pydantic ValidationError
        EmailPersonalisation(
            laa_reference="12345",
            client_first_name="Test",
            # Missing many required fields
        )


def test_email_personalisation_rejects_extra_fields():
    """
    Test that EmailPersonalisation model rejects extra/unexpected fields.
    """
    # Act & Assert - extra fields should raise validation error
    with pytest.raises(Exception):  # Pydantic ValidationError
        EmailPersonalisation(
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
            feedback_link="https://example.com",
            unexpected_field="This should not be allowed",
        )
