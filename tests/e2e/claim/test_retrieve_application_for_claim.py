from app.auth.rbac import Role
from tests.e2e.factories import create_application_in_db, create_claim_in_db


def test_200_retrieve_application_for_claim_returns_application_reference(
    session, client
):
    application = create_application_in_db(session)
    claim = create_claim_in_db(
        session,
        application_id=application.application_id,
    )

    response = client.get(
        f"/claims/{claim.claim_reference}/application",
        headers={
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"laaReference": application.laa_reference}


def test_404_retrieve_application_for_claim_returns_not_found_for_unknown_claim(
    client,
):
    response = client.get(
        "/claims/INQC-ZZZZ-ZZZZ/application",
        headers={
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Claim not found"}
