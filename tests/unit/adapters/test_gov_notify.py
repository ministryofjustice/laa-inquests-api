"""Unit tests for GovNotifyAdapter."""

from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest

from app.adapters.gov_notify import GovNotifyAdapter
from app.config import Config
from tests.unit.factories import (
    create_base_application,
    create_base_application_proceeding,
)


def _create_test_application_and_proceeding():
    """Create test application with specific overrides for GovNotify tests."""
    utc = ZoneInfo("UTC")
    application = create_base_application(
        created_at=datetime(2026, 6, 18, 14, 3, tzinfo=utc),
        proceedings=[
            create_base_application_proceeding(
                merits_decision="REFUSED",
                reason_for_refusal="NOT_IN_SCOPE",
                justification="The matter does not meet scope requirements.",
            )
        ],
    )
    return application, application.proceedings[0]


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
        assert isinstance(call_kwargs["personalisation"], dict)
        assert call_kwargs["personalisation"]["laa_reference"] == "12345"
        assert (
            call_kwargs["personalisation"]["application_submitted_at"]
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


def test_gov_notify_adapter_sends_grant_email_successfully():
    from datetime import date

    application, proceeding = _create_test_application_and_proceeding()
    proceeding.merits_decision = "GRANTED"
    proceeding.certificate_issue_date = date(2026, 6, 18)

    mock_notifications_client = Mock()
    mock_notifications_client.send_email_notification.return_value = {
        "id": "test-notification-id"
    }

    with (
        patch("app.adapters.gov_notify.NotificationsAPIClient") as mock_api_client,
        patch.object(
            Config,
            "GOV_NOTIFY_APPLICATION_GRANT_TEMPLATE_ID",
            "test-grant-template-id",
        ),
    ):
        mock_api_client.return_value = mock_notifications_client

        adapter = GovNotifyAdapter()
        adapter.send_application_granted_decision_email(
            application, proceeding, "provider@example.com"
        )

        mock_api_client.assert_called_once_with(Config.GOV_NOTIFY_API_KEY)
        call_kwargs = mock_notifications_client.send_email_notification.call_args.kwargs
        assert call_kwargs["email_address"] == "provider@example.com"
        assert call_kwargs["template_id"] == "test-grant-template-id"
        assert isinstance(call_kwargs["personalisation"], dict)
        assert call_kwargs["personalisation"]["laa_reference"] == "12345"
        assert call_kwargs["personalisation"]["issue_date"] == "18 June 2026"
