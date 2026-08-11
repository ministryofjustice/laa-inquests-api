from app.models.application.enums import MeritsDecision
from tests.unit.factories import create_base_application_proceeding


def test_substantive_cost_limitation_is_zero_when_pending():
    application_proceeding = create_base_application_proceeding(
        merits_decision=MeritsDecision.PENDING
    )

    assert application_proceeding.substantive_cost_limitation == 0


def test_substantive_cost_limitation_is_zero_when_refused():
    application_proceeding = create_base_application_proceeding(
        merits_decision=MeritsDecision.REFUSED
    )

    assert application_proceeding.substantive_cost_limitation == 0


def test_substantive_cost_limitation_matches_proceeding_when_granted():
    application_proceeding = create_base_application_proceeding(
        merits_decision=MeritsDecision.GRANTED
    )

    assert (
        application_proceeding.substantive_cost_limitation
        == application_proceeding.proceeding.substantive_cost_limitation
    )
