import uuid
from decimal import Decimal

from sqlmodel import select

from app.models.application.index import Application
from app.models.claim.enums import InvoiceTypeCode, TaxCode
from app.models.claim.index import Claim, ClaimDecision, ClaimDecisionAmount


def _make_request_body(overrides=None):
    body = {
        "claimType": "PAYMENT_ON_ACCOUNT",
        "totalProfitCostNet": 1000,
        "totalProfitCostGross": 1200,
        "poaTypeId": "PROFIT_COST",
        "claimantId": "claimant-123@provider.co.uk",
        "claimEvidenceIds": [str(uuid.uuid4())],
    }
    if overrides is not None:
        body.update(overrides)
    return body


def _post_claim(session, client, auth_token, overrides=None):
    laa_reference = session.exec(select(Application)).first().laa_reference
    return client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(overrides),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )


def _decision_amount(session, claim_id):
    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim_id)
    ).one()
    return session.exec(
        select(ClaimDecisionAmount).where(
            ClaimDecisionAmount.claim_decision_id == decision.claim_decision_id
        )
    ).one()


class TestCreateClaimPaymentExtract:
    def test_201_profit_cost_vat_claim_persists_payment_extract(
        self, session, client, auth_token
    ):
        response = _post_claim(session, client, auth_token)

        assert response.status_code == 201
        claim_id = response.json()["claimId"]
        stored_claim = session.get(Claim, claim_id)
        decision_amount = _decision_amount(session, claim_id)

        # 80% of net (1000) plus 20% VAT = 1000 * 0.8 * 1.2 = 960.00
        assert decision_amount.invoice_number == f"{claim_id}_001"
        assert decision_amount.invoice_amount == Decimal("960.00")
        assert decision_amount.invoice_date == stored_claim.submission_date.date()
        assert decision_amount.invoice_type == InvoiceTypeCode.POA
        assert decision_amount.tax_code == TaxCode.GB_VAT_20

    def test_201_profit_cost_zero_vat_claim_persists_payment_extract(
        self, session, client, auth_token
    ):
        response = _post_claim(
            session,
            client,
            auth_token,
            {
                "totalProfitCostNet": None,
                "totalProfitCostGross": None,
                "totalProfitCostVatZero": 1000,
            },
        )

        assert response.status_code == 201
        claim_id = response.json()["claimId"]
        decision_amount = _decision_amount(session, claim_id)

        # 80% of zero-rated value (1000) = 800.00, no VAT added
        assert decision_amount.invoice_number == f"{claim_id}_001"
        assert decision_amount.invoice_amount == Decimal("800.00")
        assert decision_amount.invoice_type == InvoiceTypeCode.POA
        assert decision_amount.tax_code == TaxCode.ZERO_VAT

    def test_201_non_profit_cost_poa_claim_has_no_payment_extract(
        self, session, client, auth_token
    ):
        response = _post_claim(
            session,
            client,
            auth_token,
            {"poaTypeId": "EXPERT_COST"},
        )

        assert response.status_code == 201
        claim_id = response.json()["claimId"]
        decision_amount = _decision_amount(session, claim_id)

        assert decision_amount.invoice_number is None
        assert decision_amount.invoice_amount is None
        assert decision_amount.invoice_date is None
        assert decision_amount.invoice_type is None
        assert decision_amount.tax_code is None
