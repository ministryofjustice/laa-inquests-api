from app.domain.application import ApplicationDomain
from app.models.application.enums import MeritsDecision


def test_is_granted_true_when_overall_decision_is_granted():
    application = ApplicationDomain(overall_decision=MeritsDecision.GRANTED)

    assert application.is_granted is True


def test_is_granted_false_when_overall_decision_is_pending():
    application = ApplicationDomain(overall_decision=MeritsDecision.PENDING)

    assert application.is_granted is False


def test_is_granted_false_when_overall_decision_is_refused():
    application = ApplicationDomain(overall_decision=MeritsDecision.REFUSED)

    assert application.is_granted is False
