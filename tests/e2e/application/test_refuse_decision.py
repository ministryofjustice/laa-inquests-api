import pytest
from sqlmodel import select

from app.models.application.index import Application


pytestmark = pytest.mark.usefixtures("mock_gov_notify")


def _refuse_decision_payload(overrides=None):
    payload = {
        "reasonForRefusal": "NOT_IN_SCOPE",
        "justification": "The matter does not meet scope requirements.",
    }
    if overrides:
        payload.update(overrides)
    return payload


def test_204_refuse_decision_to_refused(session, client, auth_token):
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/refuse-decision",
        json=_refuse_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 204


def test_404_refuse_decision_application_not_found(client, auth_token):
    response = client.patch(
        "/applications/99999/refuse-decision",
        json=_refuse_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404
