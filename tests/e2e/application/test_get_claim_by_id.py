import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import select

from app.domain.constants.claims import SUBSTANTIVE_CERTIFICATE_AMOUNT
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    InquestOutcomeCode,
    NumberOfCounselInstructed,
    POAType,
    ReasonCode,
)
from app.models.claim.index import (
    Claim,
    ClaimCostTemplate,
    ClaimDecision,
    ClaimEvidence,
    ClaimInquestOutcome,
    DecisionReason,
)
from tests.e2e.factories import create_application_in_db


def _seed_claim(
    session,
    laa_reference: int,
    claim_type: ClaimType = ClaimType.PAYMENT_ON_ACCOUNT,
    total_funds_remaining_after_claim: Decimal = Decimal(
        SUBSTANTIVE_CERTIFICATE_AMOUNT
    ),
) -> Claim:
    application_id = (
        session.exec(
            select(Application).where(Application.laa_reference == laa_reference)
        )
        .one()
        .application_id
    )
    claim = Claim(
        application_id=application_id,
        claim_type_id=claim_type,
        status_id=ClaimStatus.SUBMITTED,
        submission_date=datetime.now(UTC),
        total_profit_cost_net=Decimal("1000.00"),
        total_profit_cost_gross=Decimal("1200.00"),
        total_profit_cost_vat_zero=Decimal("500.00"),
        total_funds_remaining_after_claim=total_funds_remaining_after_claim,
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
        "totalFundsRemainingAfterClaim",
        "claimEvidence",
        "claimDecision",
        "inquestOutcomes",
        "claimCostTemplateFile",
        "hasCounselBeenPaid",
        "hasAlternativeFunding",
        "hasRecoveryCostsAwarded",
        "financialRecoveryPreviousPreCertificateCosts",
        "financialRecoveryCost",
        "financialRecoveryDamages",
        "financialRecoveryInterest",
        "payingParty",
        "numberOfCounselInstructed",
    }


def test_200_get_claim_by_id_returns_final_bill_details(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = Claim(
        application_id=session.exec(
            select(Application).where(Application.laa_reference == laa_reference)
        )
        .one()
        .application_id,
        claim_type_id=ClaimType.FINAL_BILL,
        status_id=ClaimStatus.SUBMITTED,
        submission_date=datetime.now(UTC),
        has_counsel_been_paid=True,
        has_alternative_funding=False,
        has_recovery_costs_awarded=True,
        financial_recovery_previous_pre_certificate_costs=Decimal("100.00"),
        financial_recovery_cost=Decimal("200.00"),
        financial_recovery_damages=Decimal("300.00"),
        financial_recovery_interest=Decimal("50.00"),
        paying_party="Test Council",
        number_of_counsel_instructed=NumberOfCounselInstructed.TWO,
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["hasCounselBeenPaid"] is True
    assert body["hasAlternativeFunding"] is False
    assert body["hasRecoveryCostsAwarded"] is True
    assert body["financialRecoveryPreviousPreCertificateCosts"] == "100.00"
    assert body["financialRecoveryCost"] == "200.00"
    assert body["financialRecoveryDamages"] == "300.00"
    assert body["financialRecoveryInterest"] == "50.00"
    assert body["payingParty"] == "Test Council"
    assert body["numberOfCounselInstructed"] == "2"


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
        session, laa_reference, total_funds_remaining_after_claim=Decimal("8800.00")
    )

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json()["totalFundsRemainingAfterClaim"] == "8800.00"


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
    assert Decimal(response.json()["totalFundsRemainingAfterClaim"]) == Decimal(
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


def test_200_get_claim_by_id_includes_inquest_outcomes_as_enum_names(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference, claim_type=ClaimType.FINAL_BILL)
    session.add_all(
        [
            ClaimInquestOutcome(
                claim_id=claim.claim_id,
                inquest_outcome_id=InquestOutcomeCode.NARRATIVE_CONCLUSION,
            ),
            ClaimInquestOutcome(
                claim_id=claim.claim_id,
                inquest_outcome_id=InquestOutcomeCode.NATURAL_CAUSES,
            ),
        ]
    )
    session.commit()

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert set(response.json()["inquestOutcomes"]) == {
        "NARRATIVE_CONCLUSION",
        "NATURAL_CAUSES",
    }


def test_200_get_claim_by_id_returns_empty_inquest_outcomes_when_none_linked(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json()["inquestOutcomes"] == []


def test_200_get_claim_by_id_includes_cost_template_file(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference, claim_type=ClaimType.FINAL_BILL)
    file_id = uuid.uuid4()
    session.add(
        ClaimCostTemplate(
            claim_id=claim.claim_id,
            claim_cost_template_file_id=file_id,
            claim_cost_template_file_name="final_bill_costs.xlsx",
        )
    )
    session.commit()

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    claim_cost_template_file = response.json()["claimCostTemplateFile"]
    assert claim_cost_template_file["claimCostTemplateFileId"] == str(file_id)
    assert (
        claim_cost_template_file["claimCostTemplateFileName"] == "final_bill_costs.xlsx"
    )


def test_200_get_claim_by_id_returns_null_cost_template_file_when_none_linked(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json()["claimCostTemplateFile"] is None


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
    other_application = create_application_in_db(session)

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
