from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.application.enums import MeritsDecision
from app.models.gov_notify_templates.application_refuse_personalisation import (
    NotifyApplicationRefuseTemplatePersonalisation,
)
from app.use_cases.notify.create_application_refusal_email_personalisation import (
    create_application_refusal_email_personalisation,
)
from tests.factories.builders import build_application, build_application_proceeding


def _create_test_application_and_proceeding():
    proceeding = build_application_proceeding(
        merits_decision=MeritsDecision.REFUSED,
        reason_for_refusal="NOT_IN_SCOPE",
        justification="The matter does not meet scope requirements.",
    )
    application = build_application(
        created_at=datetime(2026, 6, 18, 14, 3, tzinfo=UTC),
        proceeding=proceeding,
    )

    return application, proceeding


def test_create_application_refusal_email_personalisation_returns_all_required_fields():
    application, proceeding = _create_test_application_and_proceeding()

    result = create_application_refusal_email_personalisation(application, proceeding)

    assert isinstance(result, NotifyApplicationRefuseTemplatePersonalisation)
    assert result.client_first_name == "Jane"
    assert result.client_last_name == "Doe"
    assert result.laa_reference == "INQ-YYY-YYY"
    assert result.application_submitted_at == "18 June 2026 14:03 UTC"
    assert result.reason_for_refusal == "NOT_IN_SCOPE"
    assert result.justification == "The matter does not meet scope requirements."


def test_create_application_refusal_email_personalisation_rejects_missing_required_fields():
    """
    Test that NotifyApplicationRefuseTemplatePersonalisation model rejects creation with missing required fields.
    """
    with pytest.raises(ValidationError):
        NotifyApplicationRefuseTemplatePersonalisation(
            laa_reference="12345",
        )


def test_create_application_refusal_email_personalisation_rejects_extra_fields():
    """
    Test that NotifyApplicationRefuseTemplatePersonalisation model rejects creation with extra/unexpected fields.
    """
    with pytest.raises(ValidationError):
        NotifyApplicationRefuseTemplatePersonalisation(
            laa_reference="12345",
            client_first_name="Jane",
            client_last_name="Doe",
            application_submitted_at="18 June 2026 14:03 UTC",
            reason_for_refusal="NOT_IN_SCOPE",
            justification="The matter does not meet scope requirements.",
            unexpected_field="This should not be allowed",
        )
