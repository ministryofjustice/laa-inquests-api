from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.models.application.index import (
    Application,
    RefuseApplicationUpdate,
)
from app.ports.update_decision_port import ApplicationDecisionPort
from app.use_cases.exceptions import ApplicationNotFoundError, ProceedingNotFoundError
from app.use_cases.refuse_decision import RefuseDecisionUseCase
from tests.unit.factories import create_base_application


def _make_request():
    return RefuseApplicationUpdate(
        reason_for_refusal="NOT_IN_SCOPE",
        justification="The matter is not in scope.",
    )


def test_refusal_update_rejects_missing_reason_for_refusal():
    with pytest.raises(ValidationError):
        RefuseApplicationUpdate.model_validate(
            {
                "justification": "A justification is provided.",
            }
        )


def test_refusal_update_rejects_missing_justification():
    with pytest.raises(ValidationError):
        RefuseApplicationUpdate.model_validate(
            {
                "reasonForRefusal": "NOT_IN_SCOPE",
            }
        )


def test_refusal_update_rejects_invalid_reason_for_refusal():
    with pytest.raises(ValidationError):
        RefuseApplicationUpdate.model_validate(
            {
                "reasonForRefusal": "INVALID_REASON",
                "justification": "A justification is provided.",
            }
        )


def test_refuse_decision_calls_session_add_and_commit():
    application = create_base_application()
    proceeding = application.proceeding

    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = application
    update_decision_port.update_decision.return_value = None
    gov_notify_port = MagicMock()
    use_case = RefuseDecisionUseCase(update_decision_port, gov_notify_port)

    use_case.execute("1", _make_request())

    update_decision_port.update_decision.assert_called_once_with(proceeding)
    update_decision_port.commit.assert_called_once()


def test_refuse_decision_sets_merits_decision_to_refused():
    application = create_base_application()
    proceeding = application.proceeding

    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = application
    gov_notify_port = MagicMock()
    use_case = RefuseDecisionUseCase(update_decision_port, gov_notify_port)

    use_case.execute("1", _make_request())

    assert proceeding.merits_decision == "REFUSED"


def test_refuse_decision_raises_404_when_application_not_found():
    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = None
    use_case = RefuseDecisionUseCase(update_decision_port, MagicMock())

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("99999", _make_request())


def test_refuse_decision_raises_404_when_no_proceeding():
    application = Application(proceeding=null)
    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = application
    use_case = RefuseDecisionUseCase(update_decision_port, MagicMock())

    with pytest.raises(ProceedingNotFoundError):
        use_case.execute("1", _make_request())


def test_refuse_decision_sets_overall_decision_on_application():
    application = create_base_application()

    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = application
    gov_notify_port = MagicMock()
    use_case = RefuseDecisionUseCase(update_decision_port, gov_notify_port)

    use_case.execute("1", _make_request())

    assert application.overall_decision == "REFUSED"


def test_refuse_decision_raises_exception_and_rolls_back_if_gov_notify_fails():
    application = create_base_application()

    update_decision_port = MagicMock(spec=ApplicationDecisionPort)
    update_decision_port.get_application_by_laa_reference.return_value = application
    gov_notify_port = MagicMock()
    gov_notify_port.send_application_refused_decision_email.side_effect = Exception(
        "Gov Notify is unavailable"
    )
    use_case = RefuseDecisionUseCase(update_decision_port, gov_notify_port)

    with pytest.raises(Exception, match="Failed to refuse application."):
        use_case.execute("1", _make_request())

    update_decision_port.rollback.assert_called_once()
