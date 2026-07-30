from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.models.claim.index import Claim
from app.models.gov_notify_templates.claim_submit_personalisation import (
    NotifyClaimSubmitTemplatePersonalisation,
)
from app.use_cases.notify.create_claim_submission_email_personalisation import (
    _format_submission_date,
    create_claim_submission_email_personalisation,
)
from tests.unit.factories import create_base_application


def test_format_submission_date_formats_to_gov_notify_style():
    assert _format_submission_date(datetime(2026, 7, 28, tzinfo=UTC)) == "28 July 2026"


def test_create_claim_submission_email_personalisation_returns_expected_data():
    application = create_base_application()
    claim = MagicMock(spec=Claim)
    claim.submission_date = datetime(2026, 7, 28, tzinfo=UTC)

    result = create_claim_submission_email_personalisation(claim, application)

    assert isinstance(result, NotifyClaimSubmitTemplatePersonalisation)
    assert result.laa_reference == "12345"
    assert result.client_name == "Jane Doe"
    assert result.submission_date == "28 July 2026"