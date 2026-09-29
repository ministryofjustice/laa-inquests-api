from app.auth.rbac import Role
from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus
from tests.factories.builders import build_nil_bill_claim
from tests.factories.persisted import create_claim, create_claim_decision


def test_200_returns_empty_list_when_application_has_no_claims(
    client, seeded_application
):
    laa_reference = seeded_application.laa_reference

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_200_assessed_true_returns_only_non_submitted_claims(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    create_claim(session, seeded_application, status_id=ClaimStatus.SUBMITTED)
    assessed_claim = create_claim(
        session, seeded_application, status_id=ClaimStatus.ACCEPTED
    )

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [c["claimReference"] for c in body] == [assessed_claim.claim_reference]
    assert set(body[0].keys()) == {
        "claimReference",
        "claimTypeId",
        "submissionDate",
        "totalProfitCostNet",
        "totalProfitCostGross",
        "totalProfitCostVatZero",
        "totalFundsRemainingAfterClaim",
        "poaTypeId",
        "statusId",
        "claimDecisionStatus",
    }


def test_200_includes_claim_status_for_each_claim(session, client, seeded_application):
    laa_reference = seeded_application.laa_reference
    create_claim(session, seeded_application, status_id=ClaimStatus.ACCEPTED)

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["statusId"] == "ACCEPTED"


def test_200_includes_claim_decision_status_when_a_decision_exists(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application, status_id=ClaimStatus.REJECTED)
    create_claim_decision(session, claim, decision=ClaimDecisionStatus.REJECT)

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["claimDecisionStatus"] == "REJECT"


def test_200_claim_decision_status_is_null_when_no_decision_exists(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    create_claim(session, seeded_application, status_id=ClaimStatus.ACCEPTED)

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["claimDecisionStatus"] is None


def test_200_assessed_false_returns_only_submitted_claims(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    submitted_claim = create_claim(
        session, seeded_application, status_id=ClaimStatus.SUBMITTED
    )
    create_claim(session, seeded_application, status_id=ClaimStatus.ACCEPTED)

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=false",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert [c["claimReference"] for c in response.json()] == [
        submitted_claim.claim_reference
    ]


def test_200_returns_submitted_nil_bill_claim_for_providers(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    create_claim(
        session,
        seeded_application,
        preset=build_nil_bill_claim,
        status_id=ClaimStatus.SUBMITTED,
    )
    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=false",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["statusId"] == "SUBMITTED"


def test_200_returns_pay_in_full_nil_bill_claim_for_providers(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    create_claim(
        session,
        seeded_application,
        preset=build_nil_bill_claim,
        status_id=ClaimStatus.PAY_IN_FULL,
    )
    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["statusId"] == "PAY_IN_FULL"


def test_200_returns_submitted_final_bill_claim_for_providers(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    create_claim(session, seeded_application, status_id=ClaimStatus.SUBMITTED)
    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=false",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["statusId"] == "SUBMITTED"


def test_200_returns_pay_in_full_final_bill_claim_for_providers(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    create_claim(session, seeded_application, status_id=ClaimStatus.PAY_IN_FULL)
    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["statusId"] == "PAY_IN_FULL"


def test_422_when_assessed_query_param_is_missing(client, seeded_application):
    laa_reference = seeded_application.laa_reference

    response = client.get(
        f"/applications/{laa_reference}/claims",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 422


def test_422_when_assessed_query_param_is_not_a_boolean(client, seeded_application):
    laa_reference = seeded_application.laa_reference

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=maybe",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 422


def test_404_when_application_does_not_exist(client):
    response = client.get(
        "/applications/999999/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"
