from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.models.application.enums import ProceedingId
from app.models.application.index import (
    Application,
    ApplicationProceeding,
    Client,
    MeritsDecisionUpdateRefuse,
    Provider,
)
from app.ports.commit_decision_port import ApplicationDecisionPort
from app.use_cases.exceptions import ApplicationNotFoundError, ProceedingsNotFoundError
from app.use_cases.refuse_decision import RefuseDecisionUseCase


def _make_request(value):
    request_data = {"merits_decision": value}
    if value == "REFUSED":
        request_data["reason_for_refusal"] = "NOT_IN_SCOPE"
        request_data["justification"] = "The matter is not in scope."
    return MeritsDecisionUpdateRefuse(**request_data)


# TODO remove this when meritsDecision is removed from model
def test_merits_decision_update_parses_camel_case():
    update = MeritsDecisionUpdateRefuse.model_validate(
        {
            "meritsDecision": "REFUSED",
            "reasonForRefusal": "NOT_IN_SCOPE",
            "justification": "The matter is not in scope.",
        }
    )
    assert update.merits_decision == "REFUSED"


# TODO remove this when meritsDecision is removed from model
def test_merits_decision_update_parses_snake_case():
    update = MeritsDecisionUpdateRefuse(
        merits_decision="REFUSED",
        reason_for_refusal="NOT_IN_SCOPE",
        justification="The matter is not in scope.",
    )
    assert update.merits_decision == "REFUSED"


# TODO remove this when meritsDecision is removed from model
def test_merits_decision_update_rejects_invalid_value():
    with pytest.raises(ValidationError):
        MeritsDecisionUpdateRefuse(merits_decision="INVALID_VALUE")


def test_merits_decision_update_rejects_missing_reason_for_refusal_when_refused():
    with pytest.raises(ValidationError):
        MeritsDecisionUpdateRefuse.model_validate(
            {
                "meritsDecision": "REFUSED",
                "justification": "A justification is provided.",
            }
        )


def test_merits_decision_update_rejects_missing_justification_when_refused():
    with pytest.raises(ValidationError):
        MeritsDecisionUpdateRefuse.model_validate(
            {
                "meritsDecision": "REFUSED",
                "reasonForRefusal": "NOT_IN_SCOPE",
            }
        )


def test_merits_decision_update_rejects_invalid_reason_for_refusal_when_refused():
    with pytest.raises(ValidationError):
        MeritsDecisionUpdateRefuse.model_validate(
            {
                "meritsDecision": "REFUSED",
                "reasonForRefusal": "INVALID_REASON",
                "justification": "A justification is provided.",
            }
        )


def test_refuse_decision_calls_session_add_and_commit():
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
    application = Application(
        proceedings=[proceeding], provider=provider, client=client
    )
    commit_decision_port = MagicMock(spec=ApplicationDecisionPort)
    commit_decision_port.get_application_by_laa_reference.return_value = application
    gov_notify_port = MagicMock()
    use_case = RefuseDecisionUseCase(commit_decision_port, gov_notify_port)

    use_case.execute("1", _make_request("REFUSED"))

    # update_decision
    commit_decision_port.commit_decision.assert_called_once_with(proceeding)
    # commit is called


def test_refuse_decision_sets_merits_decision_to_refused():
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
    application = Application(
        proceedings=[proceeding], provider=provider, client=client
    )
    commit_decision_port = MagicMock(spec=ApplicationDecisionPort)
    commit_decision_port.get_application_by_laa_reference.return_value = application
    gov_notify_port = MagicMock()
    use_case = RefuseDecisionUseCase(commit_decision_port, gov_notify_port)

    use_case.execute("1", _make_request("REFUSED"))

    assert proceeding.merits_decision == "REFUSED"


def test_refuse_decision_raises_404_when_application_not_found():
    commit_decision_port = MagicMock(spec=ApplicationDecisionPort)
    commit_decision_port.get_application_by_laa_reference.return_value = None
    use_case = RefuseDecisionUseCase(commit_decision_port, MagicMock())

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("99999", _make_request("REFUSED"))


def test_refuse_decision_raises_404_when_no_proceedings():
    application = Application(proceedings=[])
    commit_decision_port = MagicMock(spec=ApplicationDecisionPort)
    commit_decision_port.get_application_by_laa_reference.return_value = application
    use_case = RefuseDecisionUseCase(commit_decision_port, MagicMock())

    with pytest.raises(ProceedingsNotFoundError):
        use_case.execute("1", _make_request("REFUSED"))


def test_refuse_decision_sets_overall_decision_on_application():
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
    application = Application(
        proceedings=[proceeding], provider=provider, client=client
    )
    commit_decision_port = MagicMock(spec=ApplicationDecisionPort)
    commit_decision_port.get_application_by_laa_reference.return_value = application
    gov_notify_port = MagicMock()
    use_case = RefuseDecisionUseCase(commit_decision_port, gov_notify_port)

    use_case.execute("1", _make_request("REFUSED"))

    assert application.overall_decision == "REFUSED"


def test_refuse_decision_returns_204_when_notify_fails_after_commit():
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
    application = Application(
        proceedings=[proceeding], provider=provider, client=client
    )
    commit_decision_port = MagicMock(spec=ApplicationDecisionPort)
    commit_decision_port.get_application_by_laa_reference.return_value = application
    gov_notify_port = MagicMock()
    gov_notify_port.send_application_refused_decision_email.side_effect = RuntimeError(
        "Gov Notify is unavailable"
    )
    use_case = RefuseDecisionUseCase(commit_decision_port, gov_notify_port)

    use_case.execute("1", _make_request("REFUSED"))
    commit_decision_port.commit_decision.assert_called_once_with(proceeding)

    # if notify fails
    # port.rollback called
