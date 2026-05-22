from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.application.enums import ProceedingId
from app.models.application.index import (
    Application,
    ApplicationProceeding,
    MeritsDecisionUpdate,
)
from app.routers.applications import patch_merits_decision


def _make_request(value="REFUSED"):
    return MeritsDecisionUpdate(merits_decision=value)


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
    update = MeritsDecisionUpdate.model_validate({"meritsDecision": "REFUSED"})
    assert update.merits_decision == "REFUSED"


def test_merits_decision_update_parses_snake_case():
    update = MeritsDecisionUpdate(merits_decision="REFUSED")
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

    patch_merits_decision("1", _make_request(), session)

    session.add.assert_called_once_with(proceeding)
    session.commit.assert_called_once()


def test_patch_merits_decision_sets_merits_decision_to_refused():
    proceeding = ApplicationProceeding(
        laa_reference=1, proceeding_id=ProceedingId.TEST1
    )
    application = Application(proceedings=[proceeding])
    session = MagicMock()
    session.get.return_value = application

    patch_merits_decision("1", _make_request("REFUSED"), session)

    assert proceeding.merits_decision == "REFUSED"


def test_patch_merits_decision_raises_404_when_application_not_found():
    session = MagicMock()
    session.get.return_value = None

    with pytest.raises(HTTPException) as exc:
        patch_merits_decision("99999", _make_request(), session)

    assert exc.value.status_code == 404


def test_patch_merits_decision_raises_404_when_no_proceedings():
    application = Application(proceedings=[])
    session = MagicMock()
    session.get.return_value = application

    with pytest.raises(HTTPException) as exc:
        patch_merits_decision("1", _make_request(), session)

    assert exc.value.status_code == 404
