from datetime import UTC, datetime

from sqlmodel import select

from app.auth.rbac import Role
from app.models.application.enums import CorrespondenceRecipientType, MeritsDecision
from app.models.application.index import Application
from tests.e2e.factories import create_application_in_db


def test_200_read_certificate_returns_expected_certificate_context(session, client):
    application = session.exec(select(Application)).first()
    application.proceeding.merits_decision = MeritsDecision.GRANTED
    session.add(application)
    session.commit()

    response = client.get(
        f"/applications/{application.laa_reference}/certificate",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["laaReference"] == application.laa_reference
    assert body["clientName"] == "Test Surname"
    assert body["firmName"] == "Test Firm Name"
    assert body["officeAddress"] is not None
    assert body["officeAddress"]["addressLine1"] == "Test Office Street"
    assert body["officeAddress"]["townOrCity"] == "Test City"
    assert body["officeAddress"]["postcode"] == "TE1 1ST"
    assert body["opponentDetails"] == ["Department for Transport"]
    assert body["dateCreated"] == datetime.now(tz=UTC).date().isoformat()
    assert body["effectiveDate"] == datetime.now(tz=UTC).date().isoformat()


def test_200_read_certificate_after_grant_prefixes_care_of_recipient_only_once(
    session, client
):
    application = create_application_in_db(
        session,
        client_overrides={
            "correspondence_recipient_type": CorrespondenceRecipientType.PERSON,
            "correspondence_recipient_name": "Test Recipient Name",
        },
    )
    address_line_1 = application.client.home_address.address_line_1
    headers = {"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"}

    grant_response = client.patch(
        f"/applications/{application.laa_reference}/grant-decision",
        json={"certificateStartDate": "2000-01-01"},
        headers=headers,
    )
    assert grant_response.status_code == 204

    response = client.get(
        f"/applications/{application.laa_reference}/certificate",
        headers=headers,
    )

    assert response.status_code == 200
    assert (
        response.json()["clientAddress"]["addressLine1"]
        == f"c/o Test Recipient Name {address_line_1}"
    )


def test_404_read_certificate_returns_404_when_application_not_found(client):
    response = client.get(
        "/applications/99999/certificate",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 404
