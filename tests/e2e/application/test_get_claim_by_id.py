import uuid
from decimal import Decimal

import pytest
from sqlmodel import select

from app.auth.rbac import Role
from app.domain.constants.claims import SUBSTANTIVE_CERTIFICATE_AMOUNT
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimType,
    InquestOutcomeCode,
    NumberOfCounselInstructed,
    POAType,
)
from app.models.claim.index import (
    Claim,
    ClaimCostTemplate,
    ClaimDecision,
    ClaimEvidence,
    ClaimInquestOutcome,
)
from tests.e2e.auth import (
    PROVIDER_FIRM_CODE,
    PROVIDER_OFFICE_ID,
    set_token_office_codes,
)
from tests.e2e.factories import (
    create_application_in_db,
    create_claim_decision_amount_in_db,
    create_claim_decision_in_db,
    create_claim_evidence_in_db,
    create_claim_in_db,
    create_decision_reason_in_db,
    get_application_id,
)

UNKNOWN_LAA_REFERENCE = "999999"


def _seed_claim(session, laa_reference: str, **overrides) -> Claim:
    return create_claim_in_db(
        session, application_id=get_application_id(session, laa_reference), **overrides
    )


def _seed_decision(session, claim_id: int) -> ClaimDecision:
    decision = create_claim_decision_in_db(
        session, claim_id, ClaimDecisionStatus.REJECT
    )
    create_decision_reason_in_db(session, decision.claim_decision_id)
    session.refresh(decision)
    return decision


def _seed_pay_in_full_decision(
    session, claim_id: int, **amounts: Decimal | None
) -> ClaimDecision:
    decision = create_claim_decision_in_db(
        session, claim_id, ClaimDecisionStatus.PAY_IN_FULL
    )
    create_claim_decision_amount_in_db(session, decision.claim_decision_id, **amounts)
    return decision


def _get_claim(client, laa_reference, claim_reference, role=Role.PROVIDER_CLAIMS_USER):
    return client.get(
        f"/applications/{laa_reference}/claims/{claim_reference}",
        headers={"Authorization": f"Bearer {role.value}"},
    )


class TestGetClaimBaseProperties:
    def test_200_get_claim_by_id_returns_expected_base_properties(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(
            session,
            laa_reference,
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type=POAType.PROFIT_COST,
            total_profit_cost_net=Decimal("1000.00"),
            total_profit_cost_gross=Decimal("1200.00"),
            total_profit_cost_vat_zero=Decimal("500.00"),
        )

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
        assert body["totalAmount"] == "1200.00"
        assert body["poaTypeId"] == "PROFIT_COST"
        assert isinstance(body["submissionDate"], str)
        assert set(body.keys()) == {
            "claimReference",
            "claimTypeId",
            "submissionDate",
            "totalProfitCostNet",
            "totalProfitCostGross",
            "totalProfitCostVatZero",
            "totalAmount",
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

    @pytest.mark.parametrize(
        ("net", "gross", "vat_zero", "expected_total"),
        [
            ("0.00", "150.00", "150.00", "150.00"),
            ("0.00", "0.00", "150.00", "150.00"),
            ("1000.00", "1320.00", "120.00", "1320.00"),
            ("1000.00", "1200.00", "0.00", "1200.00"),
        ],
    )
    def test_200_get_claim_by_id_returns_total_amount_for_disbursement(
        self, session, client, net, gross, vat_zero, expected_total
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(
            session,
            laa_reference,
            claim_type=ClaimType.PAYMENT_ON_ACCOUNT,
            poa_type=POAType.EXPERT_COST,
            total_profit_cost_net=Decimal(net),
            total_profit_cost_gross=Decimal(gross),
            total_profit_cost_vat_zero=Decimal(vat_zero),
        )

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.json()["totalAmount"] == expected_total

    def test_200_get_claim_by_id_returns_final_bill_details(self, session, client):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(
            session,
            laa_reference,
            claim_type=ClaimType.FINAL_BILL,
            total_profit_cost_net=None,
            total_profit_cost_gross=None,
            total_profit_cost_vat_zero=None,
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
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference)

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.json()["substantiveCostLimitation"] == 10000

    def test_200_get_claim_by_id_returns_stored_total_funds_remaining(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(
            session, laa_reference, total_funds_remaining_after_claim=Decimal("8800.00")
        )

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.json()["totalFundsRemainingAfterClaim"] == "8800.00"

    def test_200_get_claim_by_id_total_funds_remaining_defaults_to_certificate_amount(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference)

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert Decimal(response.json()["totalFundsRemainingAfterClaim"]) == Decimal(
            SUBSTANTIVE_CERTIFICATE_AMOUNT
        )


class TestGetClaimEvidence:
    def test_200_get_claim_by_id_includes_claim_evidence(self, session, client):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference)
        evidence = create_claim_evidence_in_db(
            session, claim_id=claim.claim_id, file_name="evidence.pdf"
        )

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        claim_evidence = response.json()["claimEvidence"]
        assert len(claim_evidence) == 1
        assert claim_evidence[0]["claimEvidenceId"] == str(evidence.claim_evidence_id)
        assert claim_evidence[0]["fileName"] == "evidence.pdf"

    def test_200_get_claim_by_id_includes_claim_evidence_file_size(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference)
        create_claim_evidence_in_db(session, claim_id=claim.claim_id, file_size=104448)

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.json()["claimEvidence"][0]["fileSize"] == 104448

    def test_200_get_claim_by_id_claim_evidence_file_size_is_null_when_not_stored(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference)
        create_claim_evidence_in_db(session, claim_id=claim.claim_id)

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.json()["claimEvidence"][0]["fileSize"] is None

    def test_200_get_claim_by_id_returns_empty_claim_evidence_when_none_linked(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference)

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.json()["claimEvidence"] == []


class TestGetClaimDecision:
    def test_200_get_claim_by_id_includes_claim_decision_when_one_exists(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference)
        decision = _seed_decision(session, claim.claim_id)

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

    def test_200_get_claim_by_id_includes_decision_amount_for_a_pay_in_full_decision(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference, claim_type=ClaimType.FINAL_BILL)
        _seed_pay_in_full_decision(
            session,
            claim.claim_id,
            profit_cost_net=Decimal("1000.00"),
            profit_cost_gross=Decimal("1200.00"),
            disbursement_net=Decimal("100.00"),
            disbursement_gross=Decimal("120.00"),
        )

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.json()["claimDecision"]["decisionAmount"] == {
            "profitCostNet": "1000.00",
            "profitCostGross": "1200.00",
            "profitCostVatZero": None,
            "disbursementNet": "100.00",
            "disbursementGross": "120.00",
            "disbursementVatZero": None,
        }

    def test_200_get_claim_by_id_decision_amount_passes_through_zero_vat_amounts(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference, claim_type=ClaimType.FINAL_BILL)
        _seed_pay_in_full_decision(
            session,
            claim.claim_id,
            profit_cost_vat_zero=Decimal("800.00"),
            disbursement_vat_zero=Decimal("50.00"),
        )

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        decision_amount = response.json()["claimDecision"]["decisionAmount"]
        assert decision_amount["profitCostVatZero"] == "800.00"
        assert decision_amount["profitCostNet"] is None
        assert decision_amount["disbursementVatZero"] == "50.00"

    def test_200_get_claim_by_id_decision_amount_is_null_for_a_rejected_claim(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference)
        _seed_decision(session, claim.claim_id)

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.json()["claimDecision"]["decisionAmount"] is None

    def test_200_get_claim_by_id_claim_decision_is_null_when_none_exists(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference)

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.json()["claimDecision"] is None


class TestGetClaimInquestOutcomes:
    def test_200_get_claim_by_id_includes_inquest_outcomes_as_enum_names(
        self, session, client
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
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert set(response.json()["inquestOutcomes"]) == {
            "NARRATIVE_CONCLUSION",
            "NATURAL_CAUSES",
        }

    def test_200_get_claim_by_id_returns_empty_inquest_outcomes_when_none_linked(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference)

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.json()["inquestOutcomes"] == []


class TestGetClaimCostTemplate:
    def test_200_get_claim_by_id_includes_cost_template_file(self, session, client):
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
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        claim_cost_template_file = response.json()["claimCostTemplateFile"]
        assert claim_cost_template_file["claimCostTemplateFileId"] == str(file_id)
        assert (
            claim_cost_template_file["claimCostTemplateFileName"]
            == "final_bill_costs.xlsx"
        )

    def test_200_get_claim_by_id_includes_cost_template_file_size(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference, claim_type=ClaimType.FINAL_BILL)
        file_id = uuid.uuid4()
        session.add(
            ClaimEvidence(
                claim_evidence_id=file_id,
                sds_file_name="template_abc123.xlsx",
                file_name="final_bill_costs.xlsx",
                office_id="0U651L",
                file_size=20480,
            )
        )
        session.add(
            ClaimCostTemplate(
                claim_id=claim.claim_id,
                claim_cost_template_file_id=file_id,
                claim_cost_template_file_name="final_bill_costs.xlsx",
            )
        )
        session.commit()

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.json()["claimCostTemplateFile"]["fileSize"] == 20480

    def test_200_get_claim_by_id_returns_null_cost_template_file_when_none_linked(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = _seed_claim(session, laa_reference)

        response = client.get(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.json()["claimCostTemplateFile"] is None


class TestGetClaimNotFound:
    def test_404_when_claim_does_not_exist(self, session, client):
        laa_reference = session.exec(select(Application)).first().laa_reference

        response = client.get(
            f"/applications/{laa_reference}/claims/999999",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Claim not found"

    def test_404_when_application_does_not_exist(self, client):
        response = client.get(
            "/applications/999999/claims/1",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Application not found"

    def test_404_when_claim_belongs_to_another_application(self, session, client):
        existing = session.exec(select(Application)).first()
        other_application = create_application_in_db(session)

        claim = _seed_claim(session, existing.laa_reference)

        response = client.get(
            f"/applications/{other_application.laa_reference}/claims/{claim.claim_reference}",
            headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Claim not found"


class TestGetClaimOfficeIdCheck:
    @pytest.mark.parametrize(
        ("application_office_id", "token_office_ids"),
        [
            (PROVIDER_OFFICE_ID, {PROVIDER_OFFICE_ID}),
            ("002", {PROVIDER_OFFICE_ID, "002"}),
        ],
        ids=["own-office", "second-office-in-token"],
    )
    def test_200_provider_gets_claim_when_application_office_id_matches_theirs_in_the_token(
        self, session, client, application_office_id, token_office_ids
    ):
        set_token_office_codes(token_office_ids)
        application = create_application_in_db(
            session,
            provider_overrides={
                "office_id": application_office_id,
                "firm_code": PROVIDER_FIRM_CODE,
            },
        )
        claim = create_claim_in_db(session, application_id=application.application_id)

        response = _get_claim(client, application.laa_reference, claim.claim_reference)

        assert response.status_code == 200
        assert response.json()["claimReference"] == claim.claim_reference

    @pytest.mark.parametrize(
        ("firm_code", "application_office_id"),
        [(PROVIDER_FIRM_CODE, "002"), ("ZZ999Z", "003")],
        ids=["same-firm-different-office", "different-firm"],
    )
    def test_404_provider_cannot_get_claim_when_application_office_id_mismatches_with_the_one_in_the_token(
        self, session, client, firm_code, application_office_id
    ):
        set_token_office_codes({PROVIDER_OFFICE_ID})
        application = create_application_in_db(
            session,
            provider_overrides={
                "office_id": application_office_id,
                "firm_code": firm_code,
            },
        )
        claim = create_claim_in_db(session, application_id=application.application_id)

        unknown_response = _get_claim(
            client, UNKNOWN_LAA_REFERENCE, claim.claim_reference
        )
        response = _get_claim(client, application.laa_reference, claim.claim_reference)

        assert response.status_code == unknown_response.status_code == 404
        assert response.json() == unknown_response.json()

    @pytest.mark.parametrize(
        "caseworker_role",
        [Role.CLAIMS_CASEWORKER, Role.CUSTOMER_SERVICE_AGENT, Role.ASSURANCE],
    )
    def test_200_caseworker_can_get_claim_from_any_office(
        self, session, client, caseworker_role
    ):
        application = create_application_in_db(
            session, provider_overrides={"office_id": "003", "firm_code": "ZZ999Z"}
        )
        claim = create_claim_in_db(session, application_id=application.application_id)

        response = _get_claim(
            client, application.laa_reference, claim.claim_reference, caseworker_role
        )

        assert response.status_code == 200
        assert response.json()["claimReference"] == claim.claim_reference
