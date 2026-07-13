from datetime import date, datetime, UTC
from unittest.mock import MagicMock

import pytest

from app.models.application.enums import MeritsDecision, ProceedingId
from app.models.application.index import (
    Application,
    ApplicationProceeding,
    Client,
    GrantApplicationUpdate,
    Provider,
)
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.update_decision_port import ApplicationDecisionPort
from app.ports.pdf_generation_port import PdfGenerationPort
from app.use_cases.exceptions import ApplicationNotFoundError, ProceedingsNotFoundError
from app.use_cases.grant_decision import GrantDecisionUseCase


def _grant_request() -> GrantApplicationUpdate:
    return GrantApplicationUpdate(certificate_start_date=date(2000, 1, 1))


def _make_application() -> Application:
    proceeding = ApplicationProceeding(
        laa_reference=1, proceeding_id=ProceedingId.TEST1
    )
    client = Client(
        client_first_name="Test",
        client_last_name="Client",
        date_of_birth="01-01-1990",
        correspondence_address_source="USE_CLIENT_HOME_ADDRESS",
    )
    provider = Provider(
        firm_code="0A123B", office_id="001", email_address="test@example.com"
    )
    return Application(proceedings=[proceeding], provider=provider, client=client)


def test_grant_decision_calls_update_decision_and_commit():
    application = _make_application()
    pdf_generation_port = MagicMock(spec=PdfGenerationPort)
    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = application
    update_decision_port.update_decision.return_value = None
    gov_notify_port = MagicMock(spec=GovNotifyPort)
    use_case = GrantDecisionUseCase(
        update_decision_port, gov_notify_port, pdf_generation_port
    )

    use_case.execute("1", _grant_request())

    update_decision_port.update_decision.assert_called_once_with(
        application.proceedings[0]
    )
    update_decision_port.commit.assert_called_once()


def test_grant_decision_sets_merits_decision_to_granted():
    application = _make_application()
    pdf_generation_port = MagicMock(spec=PdfGenerationPort)
    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = application
    gov_notify_port = MagicMock(spec=GovNotifyPort)
    use_case = GrantDecisionUseCase(
        update_decision_port, gov_notify_port, pdf_generation_port
    )

    use_case.execute("1", _grant_request())

    assert application.proceedings[0].merits_decision == MeritsDecision.GRANTED


def test_grant_decision_sets_certificate_dates():
    application = _make_application()
    pdf_generation_port = MagicMock(spec=PdfGenerationPort)
    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = application
    gov_notify_port = MagicMock(spec=GovNotifyPort)
    use_case = GrantDecisionUseCase(
        update_decision_port, gov_notify_port, pdf_generation_port
    )

    use_case.execute("1", _grant_request())

    assert application.proceedings[0].certificate_start_date == date(2000, 1, 1)
    assert application.proceedings[0].certificate_issue_date == datetime.now(UTC).date()


def test_grant_decision_clears_refusal_fields():
    application = _make_application()
    application.proceedings[0].reason_for_refusal = "NOT_IN_SCOPE"
    application.proceedings[0].justification = "A previous justification."
    pdf_generation_port = MagicMock(spec=PdfGenerationPort)
    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = application
    gov_notify_port = MagicMock(spec=GovNotifyPort)
    use_case = GrantDecisionUseCase(
        update_decision_port, gov_notify_port, pdf_generation_port
    )

    use_case.execute("1", _grant_request())

    assert application.proceedings[0].reason_for_refusal is None
    assert application.proceedings[0].justification is None


def test_grant_decision_sets_overall_decision_on_application():
    application = _make_application()
    pdf_generation_port = MagicMock(spec=PdfGenerationPort)
    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = application
    gov_notify_port = MagicMock(spec=GovNotifyPort)
    use_case = GrantDecisionUseCase(
        update_decision_port, gov_notify_port, pdf_generation_port
    )

    use_case.execute("1", _grant_request())

    assert application.overall_decision == MeritsDecision.GRANTED


def test_grant_decision_raises_404_when_application_not_found():
    pdf_generation_port = MagicMock(spec=PdfGenerationPort)
    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = None
    gov_notify_port = MagicMock(spec=GovNotifyPort)
    use_case = GrantDecisionUseCase(
        update_decision_port, gov_notify_port, pdf_generation_port
    )

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("99999", _grant_request())


def test_grant_decision_raises_404_when_no_proceedings():
    application = Application(proceedings=[])
    pdf_generation_port = MagicMock(spec=PdfGenerationPort)
    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = application
    gov_notify_port = MagicMock(spec=GovNotifyPort)
    use_case = GrantDecisionUseCase(
        update_decision_port, gov_notify_port, pdf_generation_port
    )

    with pytest.raises(ProceedingsNotFoundError):
        use_case.execute("1", _grant_request())
