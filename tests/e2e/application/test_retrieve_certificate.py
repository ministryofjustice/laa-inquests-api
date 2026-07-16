from datetime import date

from sqlmodel import select

from app.models.application.index import Application


def test_200_read_certificate_returns_expected_certificate_context(
    session, client, auth_token
):
    application = session.exec(select(Application)).first()

    response = client.get(
        f"/applications/{application.laa_reference}/certificate",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["laaReference"] == application.laa_reference
    assert body["clientName"] == "Test Surname"
    assert body["firmName"] == "Test Firm Name"
    assert body["officeAddress"] == "TBD"
    assert body["opponentDetails"] == "Department for Transport"
    assert body["dateCreated"] == date.today().isoformat()
    assert body["effectiveDate"] == date.today().isoformat()


def test_404_read_certificate_returns_404_when_application_not_found(
    client, auth_token
):
    response = client.get(
        "/applications/99999/certificate",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404


def test_401_read_certificate_returns_401_when_no_authorization_header(client):
    response = client.get("/applications/1/certificate")

    assert response.status_code == 401


def test_403_read_certificate_returns_403_when_provider_token(entra_auth_client):
    response = entra_auth_client.get(
        "/applications/1/certificate",
        headers={"Authorization": "Bearer valid-provider-entra-token"},
    )

    assert response.status_code == 403
