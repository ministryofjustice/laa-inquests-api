from sqlmodel import select

from app.models.application.index import Application, ApplicationProceeding


def test_204_patch_merits_decision_to_refused(session, client, auth_token):
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/merits-decision",
        json={"meritsDecision": "REFUSED"},
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
        json={"meritsDecision": "REFUSED"},
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
        json={"meritsDecision": "REFUSED"},
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

    application = session.exec(
        select(Application).where(Application.laa_reference == laa_reference)
    ).first()
    assert application.overall_decision == "REFUSED"
