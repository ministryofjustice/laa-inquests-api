from unittest.mock import MagicMock, call

import pytest
from pydantic import ValidationError

from app.models.application.index import (
    RefuseApplicationUpdate,
)
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.notifications.enums import NotificationType
from app.ports.update_decision_port import ApplicationDecisionPort
from app.use_cases.exceptions import ApplicationNotFoundError, RefuseDecisionError
from app.use_cases.refuse_decision import RefuseDecisionUseCase
from tests.unit.factories import create_base_application


@pytest.fixture
def refuse_request() -> RefuseApplicationUpdate:
    return RefuseApplicationUpdate(
        reason_for_refusal="NOT_IN_SCOPE",
        justification="The matter is not in scope.",
    )


@pytest.fixture
def application():
    return create_base_application()


@pytest.fixture
def update_decision_port(application) -> MagicMock:
    port = MagicMock(spec=ApplicationDecisionPort)
    port.get_application_by_laa_reference.return_value = application
    port.update_decision.return_value = None
    return port


@pytest.fixture
def create_history_event_port() -> MagicMock:
    return MagicMock()


@pytest.fixture
def gov_notify_port() -> MagicMock:
    return MagicMock()


@pytest.fixture
def use_case(
    update_decision_port, gov_notify_port, create_history_event_port
) -> RefuseDecisionUseCase:
    return RefuseDecisionUseCase(
        update_decision_port, gov_notify_port, create_history_event_port
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


def test_refuse_decision_calls_required_ports_and_commit(
    use_case,
    update_decision_port,
    application,
    refuse_request,
    create_history_event_port,
):
    use_case.execute("1", refuse_request, "Caseworker")

    update_decision_port.update_decision.assert_called_once_with(application.proceeding)
    update_decision_port.commit.assert_called_once()


def test_refuse_decision_creates_required_history_events(
    use_case,
    application,
    refuse_request,
    create_history_event_port,
):
    use_case.execute("1", refuse_request, "Caseworker")

    assert create_history_event_port.create_history_event.call_count == 2
    create_history_event_port.create_history_event.assert_has_calls(
        [
            call(
                event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
                actor="Caseworker",
                actor_type=ActorType.CASEWORKER,
                laa_reference=application.laa_reference,
                event_data={
                    "merits_decision": "Refused",
                    "refusal_reason": "NOT_IN_SCOPE",
                    "refusal_justification": "The matter is not in scope.",
                },
            ),
            call(
                event_reference=HistoryEventReference.APPLICATION_REFUSED,
                actor="System",
                actor_type=ActorType.SYSTEM,
                laa_reference=application.laa_reference,
                event_data={
                    "recipient": application.provider.email_address,
                    "channel": NotificationType.EMAIL,
                },
            ),
        ]
    )

    create_history_event_port.commit.assert_called_once()
    create_history_event_port.rollback.assert_not_called()


def test_refuse_decision_sets_merits_decision_to_refused(
    use_case, application, refuse_request
):
    use_case.execute("1", refuse_request, "Caseworker")

    assert application.proceeding.merits_decision == "REFUSED"


def test_refuse_decision_raises_404_when_application_not_found(
    use_case, update_decision_port, refuse_request
):
    update_decision_port.get_application_by_laa_reference.return_value = None

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("99999", refuse_request, "Caseworker")


def test_refuse_decision_sets_overall_decision_on_application(
    use_case, application, refuse_request
):
    use_case.execute("1", refuse_request, "Caseworker")

    assert application.overall_decision == "REFUSED"


def test_refuse_decision_raises_exception_and_rolls_back_if_gov_notify_fails(
    use_case,
    update_decision_port,
    gov_notify_port,
    create_history_event_port,
    refuse_request,
):
    gov_notify_port.send_application_refused_decision_email.side_effect = Exception(
        "Gov Notify is unavailable"
    )

    with pytest.raises(RefuseDecisionError, match="Failed to refuse application."):
        use_case.execute("1", refuse_request, "Caseworker")

    update_decision_port.rollback.assert_called_once()
    create_history_event_port.rollback.assert_called_once()
