from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.models.claim.index import Claim
from app.models.gov_notify_templates.claim_reject_personalisation import (
    NotifyClaimRejectTemplatePersonalisation,
)
from app.use_cases.notify.create_claim_rejection_email_personalisation import (
    _format_submitted_at,
    create_claim_rejection_email_personalisation,
)
from tests.unit.factories import create_base_application


def test_format_submitted_at_formats_to_gov_notify_style():
    assert (
        _format_submitted_at(datetime(2026, 6, 18, 14, 3, tzinfo=UTC))
        == "18 June 2026 14:03 UTC"
    )


def test_create_claim_rejection_email_personalisation_returns_expected_data():
    application = create_base_application()
    claim = MagicMock(spec=Claim)
    claim.claim_id = 7
    claim.submission_date = datetime(2026, 6, 18, 14, 3, tzinfo=UTC)

    result = create_claim_rejection_email_personalisation(
        claim, application, "Rejected following manual review."
    )

    assert isinstance(result, NotifyClaimRejectTemplatePersonalisation)
    assert result.laa_reference == "12345"
    assert result.claim_id == "7"
    assert result.client_first_name == "Jane"
    assert result.client_last_name == "Doe"
    assert result.claim_submitted_at == "18 June 2026 14:03 UTC"
    assert result.justification == "Rejected following manual review."
