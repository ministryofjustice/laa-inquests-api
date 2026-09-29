import uuid
from decimal import Decimal

from app.auth.rbac import Role
from app.domain.constants.claims import SUBSTANTIVE_CERTIFICATE_AMOUNT
from app.models.claim.enums import InquestOutcomeCode, NumberOfCounselInstructed
from tests.factories.builders import build_poa_claim
from tests.factories.persisted import (
    create_application,
    create_claim,
    create_claim_cost_template,
    create_claim_decision,
    create_claim_evidence,
    create_claim_inquest_outcomes,
)


def test_200_get_claim_by_id_returns_expected_base_properties(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application, preset=build_poa_claim)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["claimReference"] == claim.claim_reference
    assert body["claimTypeId"] == "PAYMENT_ON_ACCOUNT"
    assert body["totalProfitCostNet"] == "1000.00"
    assert body["totalProfitCostGross"] == "1200.00"
    assert body["totalProfitCostVatZero"] == "500.00"
    assert body["poaTypeId"] == "PROFIT_COST"
    assert isinstance(body["submissionDate"], str)
    assert set(body.keys()) == {
        "claimReference",
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


def test_200_get_claim_by_id_returns_final_bill_details(
    session, client, seeded_application
):
    application = seeded_application
    laa_reference = application.laa_reference
    claim = create_claim(
        session,
        application,
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

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
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
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()["substantiveCostLimitation"] == 10000


def test_200_get_claim_by_id_returns_stored_total_funds_remaining(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(
        session,
        seeded_application,
        total_funds_remaining_after_claim=Decimal("8800.00"),
    )

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()["totalFundsRemainingAfterClaim"] == "8800.00"


def test_200_get_claim_by_id_total_funds_remaining_defaults_to_certificate_amount(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert Decimal(response.json()["totalFundsRemainingAfterClaim"]) == Decimal(
        SUBSTANTIVE_CERTIFICATE_AMOUNT
    )


def test_200_get_claim_by_id_includes_claim_evidence(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application)
    evidence = create_claim_evidence(session, claim)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    claim_evidence = response.json()["claimEvidence"]
    assert len(claim_evidence) == 1
    assert claim_evidence[0]["claimEvidenceId"] == str(evidence.claim_evidence_id)
    assert claim_evidence[0]["fileName"] == "evidence.pdf"


def test_200_get_claim_by_id_returns_empty_claim_evidence_when_none_linked(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()["claimEvidence"] == []


def test_200_get_claim_by_id_includes_claim_decision_when_one_exists(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application)
    decision = create_claim_decision(session, claim, reasons=[{}])

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
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
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()["claimDecision"] is None


def test_200_get_claim_by_id_includes_inquest_outcomes_as_enum_names(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application)
    create_claim_inquest_outcomes(
        session,
        claim,
        [InquestOutcomeCode.NARRATIVE_CONCLUSION, InquestOutcomeCode.NATURAL_CAUSES],
    )

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert set(response.json()["inquestOutcomes"]) == {
        "NARRATIVE_CONCLUSION",
        "NATURAL_CAUSES",
    }


def test_200_get_claim_by_id_returns_empty_inquest_outcomes_when_none_linked(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()["inquestOutcomes"] == []


def test_200_get_claim_by_id_includes_cost_template_file(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application)
    file_id = uuid.uuid4()
    create_claim_cost_template(
        session,
        claim,
        claim_cost_template_file_id=file_id,
        claim_cost_template_file_name="final_bill_costs.xlsx",
    )

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    claim_cost_template_file = response.json()["claimCostTemplateFile"]
    assert claim_cost_template_file["claimCostTemplateFileId"] == str(file_id)
    assert (
        claim_cost_template_file["claimCostTemplateFileName"] == "final_bill_costs.xlsx"
    )


def test_200_get_claim_by_id_returns_null_cost_template_file_when_none_linked(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application)

    response = client.get(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()["claimCostTemplateFile"] is None


def test_404_when_claim_does_not_exist(client, seeded_application):
    laa_reference = seeded_application.laa_reference

    response = client.get(
        f"/applications/{laa_reference}/claims/999999",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"


def test_404_when_application_does_not_exist(client):
    response = client.get(
        "/applications/999999/claims/1",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"


def test_404_when_claim_belongs_to_another_application(
    session, client, seeded_application
):
    existing = seeded_application
    other_application = create_application(session)

    claim = create_claim(session, existing)

    response = client.get(
        f"/applications/{other_application.laa_reference}/claims/{claim.claim_reference}",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"
