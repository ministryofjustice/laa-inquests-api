import pytest
from sqlmodel import select

from app.models.application.index import Application, ApplicationProceeding


pytestmark = pytest.mark.usefixtures("mock_gov_notify")


def _refuse_decision_payload(overrides=None):
    payload = {
        "meritsDecision": "REFUSED",
        "reasonForRefusal": "NOT_IN_SCOPE",
        "justification": "The matter does not meet scope requirements.",
    }
    if overrides:
        payload.update(overrides)
    return payload


def test_204_patch_merits_decision_to_refused(session, client, auth_token):
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/merits-decision",
        json=_refuse_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 204


def test_422_patch_merits_decision_with_invalid_value(client, auth_token):
    response = client.patch(
        "/applications/1/merits-decision",
        json={"meritsDecision": "INVALID_VALUE"},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_404_patch_merits_decision_application_not_found(client, auth_token):
    response = client.patch(
        "/applications/99999/merits-decision",
        json=_refuse_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404


def test_204_patch_merits_decision_updates_db(session, client, auth_token):
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference

    client.patch(
        f"/applications/{laa_reference}/merits-decision",
        json=_refuse_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    session.expire_all()
    proceeding = session.exec(
        select(ApplicationProceeding).where(
            ApplicationProceeding.laa_reference == laa_reference
        )
    ).first()
    assert proceeding.merits_decision == "REFUSED"
    assert getattr(proceeding, "reason_for_refusal", None) == "NOT_IN_SCOPE"
    assert (
        getattr(proceeding, "justification", None)
        == "The matter does not meet scope requirements."
    )

    application = session.exec(
        select(Application).where(Application.laa_reference == laa_reference)
    ).first()
    assert application.overall_decision == "REFUSED"


def test_422_patch_merits_decision_refused_missing_reason_for_refusal(
    client, auth_token
):
    response = client.patch(
        "/applications/1/merits-decision",
        json={
            "meritsDecision": "REFUSED",
            "justification": "A justification is provided.",
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_422_patch_merits_decision_refused_missing_justification(client, auth_token):
    response = client.patch(
        "/applications/1/merits-decision",
        json={
            "meritsDecision": "REFUSED",
            "reasonForRefusal": "NOT_IN_SCOPE",
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_422_patch_merits_decision_refused_with_invalid_reason(client, auth_token):
    response = client.patch(
        "/applications/1/merits-decision",
        json={
            "meritsDecision": "REFUSED",
            "reasonForRefusal": "INVALID_REASON",
            "justification": "A justification is provided.",
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_204_patch_merits_decision_persists_when_notify_fails(
    session, client, auth_token, mock_gov_notify
):
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference

    mock_gov_notify.send_email.side_effect = RuntimeError("Gov Notify is unavailable")

    response = client.patch(
        f"/applications/{laa_reference}/merits-decision",
        json=_refuse_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 204

    session.expire_all()
    proceeding = session.exec(
        select(ApplicationProceeding).where(
            ApplicationProceeding.laa_reference == laa_reference
        )
    ).first()
    assert proceeding.merits_decision == "REFUSED"
    assert getattr(proceeding, "reason_for_refusal", None) == "NOT_IN_SCOPE"
    assert (
        getattr(proceeding, "justification", None)
        == "The matter does not meet scope requirements."
    )

    application = session.exec(
        select(Application).where(Application.laa_reference == laa_reference)
    ).first()
    assert application.overall_decision == "REFUSED"
