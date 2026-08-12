from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import select

from app.domain.constants.claims import SUBSTANTIVE_CERTIFICATE_AMOUNT
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    POAType,
    ReasonCode,
)
from app.models.claim.index import (
    Claim,
    ClaimDecision,
    ClaimEvidence,
    DecisionReason,
)


def _seed_claim(
    session,
    laa_reference: int,
    claim_type: ClaimType = ClaimType.PAYMENT_ON_ACCOUNT,
    total_funds_remaining: Decimal = Decimal(SUBSTANTIVE_CERTIFICATE_AMOUNT),
) -> Claim:
    claim = Claim(
        laa_reference=laa_reference,
        claim_type_id=claim_type,
        status_id=ClaimStatus.SUBMITTED,
        submission_date=datetime.now(UTC),
        total_profit_cost_net=Decimal("1000.00"),
        total_profit_cost_gross=Decimal("1200.00"),
        total_profit_cost_vat_zero=Decimal("500.00"),
        total_funds_remaining=total_funds_remaining,
        poa_type_id=POAType.PROFIT_COST,
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


def _seed_evidence(session, claim_id: int) -> ClaimEvidence:
    evidence = ClaimEvidence(
        sds_file_name="evidence_abc123.pdf",
        file_name="evidence.pdf",
        claim_id=claim_id,
    )
    session.add(evidence)
    session.commit()
    session.refresh(evidence)
    return evidence


def _seed_decision(session, claim_id: int) -> ClaimDecision:
    decision = ClaimDecision(
        claim_id=claim_id,
        decision=ClaimDecisionStatus.REJECT,
    )
    session.add(decision)
    session.commit()
    session.refresh(decision)
    reason = DecisionReason(
        claim_decision_id=decision.claim_decision_id,
        reason_code=ReasonCode.MAX_POA_CLAIMS_EXCEEDED,
        justification="Too many payment on account claims",
    )
    session.add(reason)
    session.commit()
    session.refresh(decision)
    return decision


def test_200_get_claim_by_id_returns_expected_base_properties(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["claimId"] == claim.claim_id
    assert body["claimTypeId"] == "PAYMENT_ON_ACCOUNT"
    assert body["totalProfitCostNet"] == "1000.00"
    assert body["totalProfitCostGross"] == "1200.00"
    assert body["totalProfitCostVatZero"] == "500.00"
    assert body["poaTypeId"] == "PROFIT_COST"
    assert isinstance(body["submissionDate"], str)
    assert set(body.keys()) == {
        "claimId",
        "claimTypeId",
        "submissionDate",
        "totalProfitCostNet",
        "totalProfitCostGross",
        "totalProfitCostVatZero",
        "poaTypeId",
        "substantiveCostLimitation",
        "totalFundsRemaining",
        "claimEvidence",
        "claimDecision",
    }


def test_200_get_claim_by_id_includes_substantive_cost_limitation(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json()["substantiveCostLimitation"] == 10000


def test_200_get_claim_by_id_returns_stored_total_funds_remaining(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(
        session, laa_reference, total_funds_remaining=Decimal("8800.00")
    )

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json()["totalFundsRemaining"] == "8800.00"


def test_200_get_claim_by_id_total_funds_remaining_defaults_to_certificate_amount(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert Decimal(response.json()["totalFundsRemaining"]) == Decimal(
        SUBSTANTIVE_CERTIFICATE_AMOUNT
    )


def test_200_get_claim_by_id_includes_claim_evidence(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)
    evidence = _seed_evidence(session, claim.claim_id)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    claim_evidence = response.json()["claimEvidence"]
    assert len(claim_evidence) == 1
    assert claim_evidence[0]["claimEvidenceId"] == str(evidence.claim_evidence_id)
    assert claim_evidence[0]["fileName"] == "evidence.pdf"


def test_200_get_claim_by_id_returns_empty_claim_evidence_when_none_linked(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json()["claimEvidence"] == []


def test_200_get_claim_by_id_includes_claim_decision_when_one_exists(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)
    decision = _seed_decision(session, claim.claim_id)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    claim_decision = response.json()["claimDecision"]
    assert claim_decision["claimDecisionId"] == decision.claim_decision_id
    assert claim_decision["decision"] == "REJECT"
    assert claim_decision["decisionReasons"] == [
        {
            "reasonCode": "MAX_POA_CLAIMS_EXCEEDED",
            "justification": "Too many payment on account claims",
        }
    ]


def test_200_get_claim_by_id_claim_decision_is_null_when_none_exists(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json()["claimDecision"] is None


def test_404_when_claim_does_not_exist(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.get(
        f"/applications/{laa_reference}/claims/999999",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"


def test_404_when_application_does_not_exist(client, auth_token):
    response = client.get(
        "/applications/999999/claims/1",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"


def test_404_when_claim_belongs_to_another_application(session, client, auth_token):
    existing = session.exec(select(Application)).first()
    other_application = Application(
        client_id=existing.client_id,
        deceased_id=existing.deceased_id,
        provider_id=existing.provider_id,
    )
    session.add(other_application)
    session.commit()
    session.refresh(other_application)

    claim = _seed_claim(session, existing.laa_reference)

    response = client.get(
        f"/applications/{other_application.laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"


def test_401_returns_unauthorized_when_no_auth_header(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.get(f"/applications/{laa_reference}/claims/{claim.claim_id}")

    assert response.status_code == 401


def test_403_returns_forbidden_when_provider_token(entra_auth_client):
    response = entra_auth_client.get(
        "/applications/1/claims/1",
        headers={"Authorization": "Bearer valid-provider-entra-token"},
    )

    assert response.status_code == 403
