from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.application.enums import ProceedingId
from app.models.application.index import (
    Application,
    ApplicationProceeding,
    Client,
    MeritsDecisionUpdate,
    Provider,
)
from app.routers.applications import patch_merits_decision


def _make_request(value="GRANTED"):
    request_data = {"merits_decision": value}
    if value == "REFUSED":
        request_data["reason_for_refusal"] = "NOT_IN_SCOPE"
        request_data["justification"] = "The matter is not in scope."
    return MeritsDecisionUpdate(**request_data)


def test_merits_decision_defaults_to_pending():
    proceeding = ApplicationProceeding(
        laa_reference=1, proceeding_id=ProceedingId.TEST1
    )
    assert proceeding.merits_decision == "PENDING"


def test_merits_decision_can_be_set_to_refused():
    proceeding = ApplicationProceeding(
        laa_reference=1, proceeding_id=ProceedingId.TEST1
    )
    proceeding.merits_decision = "REFUSED"
    assert proceeding.merits_decision == "REFUSED"


def test_merits_decision_update_parses_camel_case():
    update = MeritsDecisionUpdate.model_validate(
        {
            "meritsDecision": "REFUSED",
            "reasonForRefusal": "NOT_IN_SCOPE",
            "justification": "The matter is not in scope.",
        }
    )
    assert update.merits_decision == "REFUSED"


def test_merits_decision_update_parses_snake_case():
    update = MeritsDecisionUpdate(
        merits_decision="REFUSED",
        reason_for_refusal="NOT_IN_SCOPE",
        justification="The matter is not in scope.",
    )
    assert update.merits_decision == "REFUSED"


def test_merits_decision_update_rejects_invalid_value():
    with pytest.raises(ValidationError):
        MeritsDecisionUpdate(merits_decision="INVALID_VALUE")


def test_merits_decision_update_accepts_granted():
    update = MeritsDecisionUpdate(merits_decision="GRANTED")
    assert update.merits_decision == "GRANTED"


def test_patch_merits_decision_calls_session_add_and_commit():
    proceeding = ApplicationProceeding(
        laa_reference=1, proceeding_id=ProceedingId.TEST1
    )
    application = Application(proceedings=[proceeding])
    session = MagicMock()
    session.get.return_value = application

    patch_merits_decision("1", _make_request("GRANTED"), session)

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

    with patch("app.routers.applications.GovNotifyClient") as mock_client_class:
        mock_client_class.return_value.send_email.return_value = None
        patch_merits_decision("1", _make_request("REFUSED"), session)

    assert proceeding.merits_decision == "REFUSED"


def test_patch_merits_decision_raises_404_when_application_not_found():
    session = MagicMock()
    session.get.return_value = None

    with pytest.raises(HTTPException) as exc:
        patch_merits_decision("99999", _make_request("GRANTED"), session)

    assert exc.value.status_code == 404


def test_patch_merits_decision_raises_404_when_no_proceedings():
    application = Application(proceedings=[])
    session = MagicMock()
    session.get.return_value = application

    with pytest.raises(HTTPException) as exc:
        patch_merits_decision("1", _make_request("GRANTED"), session)

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

    with patch("app.routers.applications.GovNotifyClient") as mock_client_class:
        mock_client_class.return_value.send_email.return_value = None
        patch_merits_decision("1", _make_request("REFUSED"), session)

    assert application.overall_decision == "REFUSED"
