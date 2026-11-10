import pytest

from app.auth.rbac import Role
from app.models.application.enums import MeritsDecision
from tests.e2e.factories import create_application_in_db

pytestmark = pytest.mark.usefixtures("mock_gov_notify")


def _refuse_decision_payload(overrides=None):
    payload = {
        "reasonForRefusal": "NOT_IN_SCOPE",
        "justification": "The matter does not meet scope requirements.",
    }
    if overrides:
        payload.update(overrides)
    return payload


def test_204_refuse_decision_to_refused(session, client):
    application = create_application_in_db(session)
    laa_reference = application.laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/refuse-decision",
        json=_refuse_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 204


def test_404_refuse_decision_application_not_found(client):
    response = client.patch(
        "/applications/99999/refuse-decision",
        json=_refuse_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 404


def test_409_refuse_decision_application_already_granted(client, session):
    application = create_application_in_db(
        session, proceeding_overrides={"merits_decision": MeritsDecision.GRANTED}
    )
    laa_reference = application.laa_reference
    application.proceeding.merits_decision = MeritsDecision.GRANTED
    session.add(application.proceeding)
    session.commit()
    session.refresh(application)

    response = client.patch(
        f"/applications/{laa_reference}/refuse-decision",
        json=_refuse_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 409
