from datetime import UTC, datetime

from app.auth.rbac import Role
from app.models.application.enums import MeritsDecision
from tests.factories.persisted import create_application


def test_200_read_certificate_returns_expected_certificate_context(session, client):
    today = datetime.now(tz=UTC).date()
    application = create_application(
        session,
        client_overrides={"client_first_name": "Ada", "client_last_name": "Lovelace"},
        proceeding_overrides={
            "merits_decision": MeritsDecision.GRANTED,
            "certificate_issue_date": today,
            "certificate_start_date": today,
        },
    )

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
    assert body["clientName"] == "Ada Lovelace"
    assert body["firmName"] == "Test Firm Name"
    assert body["officeAddress"] is not None
    assert body["officeAddress"]["addressLine1"] == "Test Office Street"
    assert body["officeAddress"]["townOrCity"] == "Test City"
    assert body["officeAddress"]["postcode"] == "TE1 1ST"
    assert body["opponentDetails"] == ["Department for Transport"]
    assert body["dateCreated"] == today.isoformat()
    assert body["effectiveDate"] == today.isoformat()


def test_404_read_certificate_returns_404_when_application_not_found(client):
    response = client.get(
        "/applications/99999/certificate",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 404
