"""Unit tests for GovNotifyAdapter."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest

from app.adapters.gov_notify import GovNotifyAdapter
from app.config import Config
from app.models.claim.index import Claim
from tests.unit.factories import (
    create_base_application,
    create_base_application_proceeding,
)


def _create_test_application_and_proceeding():
    """Create test application with specific overrides for GovNotify tests."""
    utc = ZoneInfo("UTC")
    application = create_base_application(
        created_at=datetime(2026, 6, 18, 14, 3, tzinfo=utc),
        proceeding=create_base_application_proceeding(
            merits_decision="REFUSED",
            reason_for_refusal="NOT_IN_SCOPE",
            justification="The matter does not meet scope requirements.",
        ),
    )
    return application, application.proceeding


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


def test_gov_notify_adapter_sends_claim_submit_confirmation_email_successfully():
    application, _ = _create_test_application_and_proceeding()
    claim = Claim(
        claim_id=1,
        laa_reference=12345,
        claim_type_id="PAYMENT_ON_ACCOUNT",
        submission_date=datetime(2026, 6, 18, 14, 3, tzinfo=ZoneInfo("UTC")),
        total_profit_cost_net=1000,
        total_profit_cost_gross=1200,
        poa_type_id="PROFIT_COST",
    )
    mock_notifications_client = Mock()
    mock_notifications_client.send_email_notification.return_value = {
        "id": "test-notification-id"
    }

    with (
        patch("app.adapters.gov_notify.NotificationsAPIClient") as mock_api_client,
        patch.object(
            Config,
            "GOV_NOTIFY_CLAIM_SUBMIT_TEMPLATE_ID",
            "test-claim-submit-template-id",
        ),
    ):
        mock_api_client.return_value = mock_notifications_client

        adapter = GovNotifyAdapter()
        adapter.send_claim_submit_confirmation_email(
            claim,
            application,
            "provider@example.com",
        )

        mock_api_client.assert_called_once_with(Config.GOV_NOTIFY_API_KEY)
        call_kwargs = mock_notifications_client.send_email_notification.call_args.kwargs
        assert call_kwargs["email_address"] == "provider@example.com"
        assert call_kwargs["template_id"] == "test-claim-submit-template-id"
        assert isinstance(call_kwargs["personalisation"], dict)
        assert call_kwargs["personalisation"]["laa_reference"] == "12345"
        assert call_kwargs["personalisation"]["client_name"] == "Jane Doe"
        assert call_kwargs["personalisation"]["submission_date"] == "18 June 2026"


def test_gov_notify_adapter_sends_claim_rejected_decision_email_successfully():
    application, _ = _create_test_application_and_proceeding()
    claim = Claim(
        claim_id=7,
        laa_reference=12345,
        claim_type_id="PAYMENT_ON_ACCOUNT",
        submission_date=datetime(2026, 6, 18, 14, 3, tzinfo=ZoneInfo("UTC")),
        total_profit_cost_net=1000,
        total_profit_cost_gross=1200,
        poa_type_id="PROFIT_COST",
    )
    mock_notifications_client = Mock()
    mock_notifications_client.send_email_notification.return_value = {
        "id": "test-notification-id"
    }

    with (
        patch("app.adapters.gov_notify.NotificationsAPIClient") as mock_api_client,
        patch.object(
            Config,
            "GOV_NOTIFY_CLAIM_REJECT_TEMPLATE_ID",
            "test-claim-reject-template-id",
        ),
    ):
        mock_api_client.return_value = mock_notifications_client

        adapter = GovNotifyAdapter()
        adapter.send_claim_rejected_decision_email(
            claim,
            application,
            "Rejected following manual review.",
            "claimant-123@provider.co.uk",
        )

        mock_api_client.assert_called_once_with(Config.GOV_NOTIFY_API_KEY)
        call_kwargs = mock_notifications_client.send_email_notification.call_args.kwargs
        assert call_kwargs["email_address"] == "claimant-123@provider.co.uk"
        assert call_kwargs["template_id"] == "test-claim-reject-template-id"
        assert isinstance(call_kwargs["personalisation"], dict)
        assert call_kwargs["personalisation"]["laa_reference"] == "12345"
        assert call_kwargs["personalisation"]["claim_id"] == "7"
        assert call_kwargs["personalisation"]["client_first_name"] == "Jane"
        assert call_kwargs["personalisation"]["client_last_name"] == "Doe"
        assert (
            call_kwargs["personalisation"]["claim_submitted_at"]
            == "18 June 2026 14:03 UTC"
        )
        assert (
            call_kwargs["personalisation"]["justification"]
            == "Rejected following manual review."
        )


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
            application,
            proceeding,
            "provider@example.com",
            certificate_pdf=b"dummy-pdf-content",
        )

        mock_api_client.assert_called_once_with(Config.GOV_NOTIFY_API_KEY)
        call_kwargs = mock_notifications_client.send_email_notification.call_args.kwargs
        assert call_kwargs["email_address"] == "provider@example.com"
        assert call_kwargs["template_id"] == "test-grant-template-id"
        assert isinstance(call_kwargs["personalisation"], dict)
        assert call_kwargs["personalisation"]["laa_reference"] == "12345"
        assert call_kwargs["personalisation"]["issue_date"] == "18 June 2026"


def test_gov_notify_formats_filename():
    from datetime import date

    application, proceeding = _create_test_application_and_proceeding()
    proceeding.merits_decision = "GRANTED"
    proceeding.certificate_issue_date = date(2026, 6, 18)

    mock_notifications_client = Mock()
    mock_notifications_client.send_email_notification.return_value = {
        "id": "test-notification-id"
    }
    mock_datetime = datetime(2026, 6, 18, 14, 3, 0, tzinfo=UTC)
    expected_filename = "12345_Certificate_20260618_140300.pdf"

    with (
        patch("app.adapters.gov_notify.NotificationsAPIClient") as mock_api_client,
        patch("app.adapters.gov_notify.datetime") as mock_datetime_module,
        patch("app.adapters.gov_notify.prepare_upload") as mock_prepare_upload,
        patch.object(
            Config,
            "GOV_NOTIFY_APPLICATION_GRANT_TEMPLATE_ID",
            "test-grant-template-id",
        ),
    ):
        mock_api_client.return_value = mock_notifications_client
        mock_datetime_module.now.return_value = mock_datetime
        mock_prepare_upload.return_value = {"file": "encoded-content"}

        adapter = GovNotifyAdapter()
        adapter.send_application_granted_decision_email(
            application,
            proceeding,
            "provider@example.com",
            certificate_pdf=b"dummy-pdf-content",
        )

        # Verify prepare_upload was called with the correctly formatted filename
        mock_prepare_upload.assert_called_once()
        call_kwargs = mock_prepare_upload.call_args.kwargs
        assert call_kwargs["filename"] == expected_filename
