from datetime import UTC, date, datetime
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
from app.ports.update_decision_port import ApplicationDecisionPort
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    GrantDecisionError,
    ProceedingNotFoundError,
)
from app.use_cases.grant_decision import GrantDecisionUseCase


@pytest.fixture
def grant_request() -> GrantApplicationUpdate:
    return GrantApplicationUpdate(certificate_start_date=date(2000, 1, 1))


@pytest.fixture
def application() -> Application:
    proceeding = ApplicationProceeding(laa_reference=1, proceeding_id=ProceedingId.IQOT)
    client = Client(
        client_first_name="Test",
        client_last_name="Client",
        date_of_birth="01-01-1990",
        correspondence_address_source="USE_CLIENT_HOME_ADDRESS",
    )
    provider = Provider(
        firm_code="0A123B", office_id="001", email_address="test@example.com"
    )
    return Application(proceeding=proceeding, provider=provider, client=client)


@pytest.fixture
def update_decision_port(application: Application) -> MagicMock:
    port = MagicMock(spec=ApplicationDecisionPort)
    port.get_application_by_laa_reference.return_value = application
    port.update_decision.return_value = None
    return port


@pytest.fixture
def create_certificate_context_use_case() -> MagicMock:
    return MagicMock()


@pytest.fixture
def send_grant_email_use_case() -> MagicMock:
    return MagicMock()


@pytest.fixture
def send_grant_letter_use_case() -> MagicMock:
    return MagicMock()


@pytest.fixture
def use_case(
    update_decision_port: MagicMock,
    create_certificate_context_use_case: MagicMock,
    send_grant_email_use_case: MagicMock,
    send_grant_letter_use_case: MagicMock,
) -> GrantDecisionUseCase:
    return GrantDecisionUseCase(
        update_decision_port,
        create_certificate_context_use_case,
        send_grant_email_use_case,
        send_grant_letter_use_case,
    )


def test_grant_decision_calls_required_ports_and_commit(
    use_case,
    create_certificate_context_use_case,
    application,
    update_decision_port,
    send_grant_email_use_case,
    grant_request,
):
    use_case.execute("1", grant_request)

    create_certificate_context_use_case.populate_certificate_context.assert_called_once_with(
        application, application.proceeding
    )
    update_decision_port.update_decision.assert_called_once_with(application.proceeding)
    update_decision_port.commit.assert_called_once()
    send_grant_email_use_case.execute.assert_called_once_with(
        application,
        application.proceeding,
        create_certificate_context_use_case.prepare_context_for_display.return_value,
    )


def test_grant_decision_sets_merits_decision_to_granted(
    use_case, application, grant_request
):
    use_case.execute("1", grant_request)

    assert application.proceeding.merits_decision == MeritsDecision.GRANTED


def test_grant_decision_sets_certificate_dates(use_case, application, grant_request):
    use_case.execute("1", grant_request)

    assert application.proceeding.certificate_start_date == date(2000, 1, 1)
    assert application.proceeding.certificate_issue_date == datetime.now(UTC).date()


def test_grant_decision_clears_refusal_fields(use_case, application, grant_request):
    application.proceeding.reason_for_refusal = "NOT_IN_SCOPE"
    application.proceeding.justification = "A previous justification."

    use_case.execute("1", grant_request)

    assert application.proceeding.reason_for_refusal is None
    assert application.proceeding.justification is None


def test_grant_decision_sets_overall_decision_on_application(
    use_case, application, grant_request
):
    use_case.execute("1", grant_request)

    assert application.overall_decision == MeritsDecision.GRANTED


def test_grant_decision_raises_404_when_application_not_found(
    use_case, update_decision_port, grant_request
):
    update_decision_port.get_application_by_laa_reference.return_value = None

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("99999", grant_request)


def test_grant_decision_raises_404_when_no_proceeding(
    use_case, update_decision_port, grant_request
):
    update_decision_port.get_application_by_laa_reference.return_value = Application(
        proceeding=None
    )

    with pytest.raises(ProceedingNotFoundError):
        use_case.execute("1", grant_request)


def test_grant_decision_raises_exception_when_create_certificate_model_use_case_fails_and_rollbacks(
    use_case,
    update_decision_port,
    create_certificate_context_use_case,
    grant_request,
):
    create_certificate_context_use_case.populate_certificate_context.side_effect = (
        Exception("Create Certificate Model failure")
    )

    with pytest.raises(GrantDecisionError):
        use_case.execute("1", grant_request)

    update_decision_port.rollback.assert_called_once()


def test_grant_decision_raises_exception_when_send_grant_email_fails_and_rollbacks(
    use_case, update_decision_port, send_grant_email_use_case, grant_request
):
    send_grant_email_use_case.execute.side_effect = Exception(
        "Send grant email failure"
    )

    with pytest.raises(GrantDecisionError):
        use_case.execute("1", grant_request)

    update_decision_port.rollback.assert_called_once()


def test_grant_decision_calls_send_grant_letter_use_case(
    use_case,
    create_certificate_context_use_case,
    send_grant_letter_use_case,
    grant_request,
):
    use_case.execute("1", grant_request)

    send_grant_letter_use_case.execute.assert_called_once_with(
        create_certificate_context_use_case.prepare_context_for_display.return_value,
    )


def test_grant_decision_raises_exception_when_send_grant_letter_fails_and_rollbacks(
    use_case,
    update_decision_port,
    send_grant_letter_use_case,
    grant_request,
):
    send_grant_letter_use_case.execute.side_effect = Exception(
        "Send grant letter failure"
    )

    with pytest.raises(GrantDecisionError):
        use_case.execute("1", grant_request)

    update_decision_port.rollback.assert_called_once()
