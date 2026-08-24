from sqlmodel import select

from app.models.application.enums import PublicBodyId
from app.models.application.index import Application


def test_204_update_application_public_bodies_updates_the_application_public_bodies(
    session, client, auth_token
):
    application = session.exec(select(Application)).first()

    response = client.patch(
        f"/applications/{application.laa_reference}/public-bodies",
        json={"publicBodies": ["Ministry of Defence"]},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 204

    updated_application = session.get(Application, application.laa_reference)
    assert updated_application is not None
    assert len(updated_application.public_bodies) == 1
    assert (
        updated_application.public_bodies[0].public_body_id
        == PublicBodyId.MINISTRY_OF_DEFENCE
    )


def test_404_update_application_public_bodies_returns_not_found_for_not_found_application(
    client, auth_token
):
    response = client.patch(
        "/applications/99999/public-bodies",
        json={"publicBodies": ["Ministry of Defence"]},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}


def test_422_update_application_public_bodies_returns_unprocessable_entity_when_list_is_empty(
    client, auth_token
):
    response = client.patch(
        "/applications/1/public-bodies",
        json={"publicBodies": []},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "At least one public body must be provided."}


def test_401_update_application_public_bodies_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.patch(
        "/applications/1/public-bodies",
        json={"publicBodies": ["Ministry of Defence"]},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 401


def test_403_update_application_public_bodies_returns_403_when_token_is_a_provider_token(
    entra_auth_client,
):
    response = entra_auth_client.patch(
        "/applications/1/public-bodies",
        json={"publicBodies": ["Ministry of Defence"]},
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-provider-entra-token",
        },
    )

    assert response.status_code == 403
