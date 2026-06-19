from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.application.enums import ProceedingId
from app.models.application.index import (
    Application,
    ApplicationProceeding,
    Client,
    MeritsDecisionUpdateRefuse,
    Provider,
)
from app.routers.applications import patch_merits_decision


def _make_request(value):
    request_data = {"merits_decision": value}
    if value == "REFUSED":
        request_data["reason_for_refusal"] = "NOT_IN_SCOPE"
        request_data["justification"] = "The matter is not in scope."
    return MeritsDecisionUpdateRefuse(**request_data)


def test_merits_decision_update_parses_camel_case():
    update = MeritsDecisionUpdateRefuse.model_validate(
        {
            "meritsDecision": "REFUSED",
            "reasonForRefusal": "NOT_IN_SCOPE",
            "justification": "The matter is not in scope.",
        }
    )
    assert update.merits_decision == "REFUSED"


def test_merits_decision_update_parses_snake_case():
    update = MeritsDecisionUpdateRefuse(
        merits_decision="REFUSED",
        reason_for_refusal="NOT_IN_SCOPE",
        justification="The matter is not in scope.",
    )
    assert update.merits_decision == "REFUSED"


def test_merits_decision_update_rejects_invalid_value():
    with pytest.raises(ValidationError):
        MeritsDecisionUpdateRefuse(merits_decision="INVALID_VALUE")


def test_patch_merits_decision_calls_session_add_and_commit():
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
    session = MagicMock()
    session.get.return_value = application
    gov_notify_port = MagicMock()

    patch_merits_decision("1", _make_request("REFUSED"), session, gov_notify_port)

    session.add.assert_any_call(application)
    session.add.assert_any_call(proceeding)
    assert session.add.call_count == 2
    session.commit.assert_called_once()


def test_patch_merits_decision_sets_merits_decision_to_refused():
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
    session = MagicMock()
    session.get.return_value = application
    gov_notify_port = MagicMock()

    patch_merits_decision("1", _make_request("REFUSED"), session, gov_notify_port)

    assert proceeding.merits_decision == "REFUSED"


def test_patch_merits_decision_raises_404_when_application_not_found():
    session = MagicMock()
    session.get.return_value = None

    with pytest.raises(HTTPException) as exc:
        patch_merits_decision("99999", _make_request("REFUSED"), session)

    assert exc.value.status_code == 404


def test_patch_merits_decision_raises_404_when_no_proceedings():
    application = Application(proceedings=[])
    session = MagicMock()
    session.get.return_value = application

    with pytest.raises(HTTPException) as exc:
        patch_merits_decision("1", _make_request("REFUSED"), session)

    assert exc.value.status_code == 404


def test_patch_merits_decision_sets_overall_decision_on_application():
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
    session = MagicMock()
    session.get.return_value = application
    gov_notify_port = MagicMock()

    patch_merits_decision("1", _make_request("REFUSED"), session, gov_notify_port)

    assert application.overall_decision == "REFUSED"


def test_patch_merits_decision_returns_204_when_notify_fails_after_commit():
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
    session = MagicMock()
    session.get.return_value = application
    gov_notify_port = MagicMock()
    gov_notify_port.send_application_refused_decision_email.side_effect = RuntimeError(
        "Gov Notify is unavailable"
    )

    response = patch_merits_decision(
        "1", _make_request("REFUSED"), session, gov_notify_port
    )

    assert response.status_code == 204
    session.commit.assert_called_once()
    session.rollback.assert_not_called()
