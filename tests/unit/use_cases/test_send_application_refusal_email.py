"""Unit tests for send_application_refusal_email use case."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from app.config import Config
from app.models.application.enums import AddressSource, ProceedingId
from app.models.application.index import (
    Application,
    ApplicationProceeding,
    Client,
)
from app.models.gov_notify_templates.application_refuse_personalisation import (
    NotifyApplicationRefuseTemplatePersonalisation,
)
from app.use_cases.notify.send_application_refusal_email import (
    send_application_refusal_email,
)


def _create_test_application_and_proceeding(laa_reference: int = 12345):
    """Helper to build application/proceeding objects needed for refusal email tests."""
    client = Client(
        client_id=1,
        client_first_name="Jane",
        client_last_name="Doe",
        date_of_birth="15-06-1985",
        correspondence_address_source=AddressSource.USE_CLIENT_HOME_ADDRESS,
    )

    application = Application(
        laa_reference=laa_reference,
        created_at=datetime(2026, 6, 18, 14, 3, tzinfo=UTC),
        client_id=1,
        client=client,
        deceased_id=1,
        provider_id=1,
    )

    proceeding = ApplicationProceeding(
        application_proceeding_id=1,
        laa_reference=laa_reference,
        proceeding_id=ProceedingId.TEST1,
        merits_decision="REFUSED",
        reason_for_refusal="NOT_IN_SCOPE",
        justification="The matter does not meet scope requirements.",
    )

    return application, proceeding


def test_send_application_refusal_email_calls_adapter_with_correct_parameters():
    """Test that send_application_refusal_email calls adapter with expected args."""
    application, proceeding = _create_test_application_and_proceeding(
        laa_reference=12345
    )
    mock_adapter = Mock()
    provider_email = "provider@example.com"

    send_application_refusal_email(
        mock_adapter, application, proceeding, provider_email
    )

    assert mock_adapter.send_email.call_count == 1

    call_args = mock_adapter.send_email.call_args
    assert call_args.kwargs["email_address"] == "provider@example.com"
    assert (
        call_args.kwargs["template_id"]
        == Config.GOV_NOTIFY_APPLICATION_REFUSE_TEMPLATE_ID
    )


def test_send_application_refusal_email_propagates_adapter_exceptions():
    """Test that send_application_refusal_email propagates adapter exceptions."""
    application, proceeding = _create_test_application_and_proceeding()
    mock_adapter = Mock()
    provider_email = "provider@example.com"
    mock_adapter.send_email.side_effect = Exception("GovNotify API error")

    with pytest.raises(Exception) as exc_info:
        send_application_refusal_email(
            mock_adapter, application, proceeding, provider_email
        )

    assert "GovNotify API error" in str(exc_info.value)


def test_send_application_refusal_email_builds_complete_personalisation():
    """Test refusal email personalisation includes all expected fields."""
    application, proceeding = _create_test_application_and_proceeding(
        laa_reference=99999
    )
    mock_adapter = Mock()
    provider_email = "provider@example.com"

    send_application_refusal_email(
        mock_adapter, application, proceeding, provider_email
    )

    personalisation = mock_adapter.send_email.call_args.kwargs["personalisation"]

    assert isinstance(personalisation, NotifyApplicationRefuseTemplatePersonalisation)
    assert personalisation.client_first_name == "Jane"
    assert personalisation.client_last_name == "Doe"
    assert personalisation.laa_reference == "99999"
    assert personalisation.application_submitted_at == "18 June 2026 14:03 UTC"
    assert personalisation.reason_for_refusal == "NOT_IN_SCOPE"
    assert (
        personalisation.justification == "The matter does not meet scope requirements."
    )
