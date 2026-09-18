from app.auth.rbac import Role
from app.models.application.index import Application
from sqlmodel import select


def test_200_retrieve_coroners_letter(session, client):
    application = session.exec(select(Application)).first()

    response = client.get(
        f"/applications/{application.laa_reference}/coroners-letter",
        headers={"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"  # Set in SDS mock in client fixture
