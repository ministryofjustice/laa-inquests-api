from sqlmodel import select

from app.models.application.index import Application


def test_204_grant_decision_to_granted(session, client, auth_token):
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/grant-decision",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 204

    session.refresh(application)
    assert application.proceedings[0].merits_decision == "GRANTED"


def test_404_grant_decision_application_not_found(client, auth_token):
    response = client.patch(
        "/applications/99999/grant-decision",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404
