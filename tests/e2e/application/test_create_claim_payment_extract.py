import uuid
from decimal import Decimal

from sqlmodel import select

from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.claim.enums import InvoiceTypeCode, TaxCode
from app.models.claim.index import Claim, ClaimPaymentExtract


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


def _post_claim(session, client, overrides=None):
    laa_reference = session.exec(select(Application)).first().laa_reference
    return client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(overrides),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}",
        },
    )


def _payment_extract(session, claim_id):
    return session.exec(
        select(ClaimPaymentExtract).where(ClaimPaymentExtract.claim_id == claim_id)
    ).one_or_none()


def _payment_extracts(session, claim_id):
    return session.exec(
        select(ClaimPaymentExtract)
        .where(ClaimPaymentExtract.claim_id == claim_id)
        .order_by(ClaimPaymentExtract.sequence_number)
    ).all()


class TestCreateClaimPaymentExtract:
    def test_201_profit_cost_vat_claim_persists_payment_extract(self, session, client):
        response = _post_claim(session, client)

        assert response.status_code == 201
        claim_id = response.json()["claimId"]
        stored_claim = session.get(Claim, claim_id)
        payment_extract = _payment_extract(session, claim_id)

        # 80% of net (1000) plus 20% VAT = 1000 * 0.8 * 1.2 = 960.00
        assert payment_extract is not None
        assert payment_extract.sequence_number == 1
        assert payment_extract.invoice_number == f"{claim_id}_001"
        assert payment_extract.invoice_amount == Decimal("960.00")
        assert payment_extract.invoice_date == stored_claim.submission_date.date()
        assert payment_extract.invoice_type == InvoiceTypeCode.POA
        assert payment_extract.tax_code == TaxCode.GB_VAT_20

    def test_201_profit_cost_zero_vat_claim_persists_payment_extract(
        self, session, client
    ):
        response = _post_claim(
            session,
            client,
            {
                "totalProfitCostNet": None,
                "totalProfitCostGross": None,
                "totalProfitCostVatZero": 1000,
            },
        )

        assert response.status_code == 201
        claim_id = response.json()["claimId"]
        payment_extract = _payment_extract(session, claim_id)

        # 80% of zero-rated value (1000) = 800.00, no VAT added
        assert payment_extract is not None
        assert payment_extract.invoice_number == f"{claim_id}_001"
        assert payment_extract.invoice_amount == Decimal("800.00")
        assert payment_extract.invoice_type == InvoiceTypeCode.POA
        assert payment_extract.tax_code == TaxCode.ZERO_VAT

    def test_201_expert_cost_gross_and_vat_zero_persists_two_payment_extracts(
        self, session, client
    ):
        response = _post_claim(
            session,
            client,
            {
                "poaTypeId": "EXPERT_COST",
                "totalProfitCostNet": None,
                "totalProfitCostGross": 1200,
                "totalProfitCostVatZero": 200,
            },
        )

        assert response.status_code == 201
        claim_id = response.json()["claimId"]
        stored_claim = session.get(Claim, claim_id)
        extracts = _payment_extracts(session, claim_id)

        assert len(extracts) == 2

        # Standard-rated line: gross (1200) minus zero-rated (200) = 1000.00
        net_line = extracts[0]
        assert net_line.sequence_number == 1
        assert net_line.invoice_number == f"{claim_id}_001"
        assert net_line.invoice_amount == Decimal("1000.00")
        assert net_line.invoice_date == stored_claim.submission_date.date()
        assert net_line.invoice_type == InvoiceTypeCode.POA
        assert net_line.tax_code == TaxCode.GB_VAT_20

        # Zero-rated line: 100% of zero-rated value (200) = 200.00
        vat_zero_line = extracts[1]
        assert vat_zero_line.sequence_number == 2
        assert vat_zero_line.invoice_number == f"{claim_id}_002"
        assert vat_zero_line.invoice_amount == Decimal("200.00")
        assert vat_zero_line.invoice_type == InvoiceTypeCode.POA
        assert vat_zero_line.tax_code == TaxCode.ZERO_VAT

    def test_201_expert_cost_gross_only_persists_single_standard_extract(
        self, session, client
    ):
        response = _post_claim(
            session,
            client,
            {
                "poaTypeId": "EXPERT_COST",
                "totalProfitCostNet": None,
                "totalProfitCostGross": 1200,
            },
        )

        assert response.status_code == 201
        claim_id = response.json()["claimId"]
        extracts = _payment_extracts(session, claim_id)

        assert len(extracts) == 1
        assert extracts[0].invoice_number == f"{claim_id}_001"
        assert extracts[0].invoice_amount == Decimal("1200.00")
        assert extracts[0].invoice_type == InvoiceTypeCode.POA
        assert extracts[0].tax_code == TaxCode.GB_VAT_20

    def test_201_non_expert_disbursement_vat_zero_only_persists_single_zero_extract(
        self, session, client
    ):
        response = _post_claim(
            session,
            client,
            {
                "poaTypeId": "NON_EXPERT_DISBURSEMENT",
                "totalProfitCostNet": None,
                "totalProfitCostGross": None,
                "totalProfitCostVatZero": 500,
            },
        )

        assert response.status_code == 201
        claim_id = response.json()["claimId"]
        extracts = _payment_extracts(session, claim_id)

        assert len(extracts) == 1
        assert extracts[0].invoice_number == f"{claim_id}_001"
        assert extracts[0].invoice_amount == Decimal("500.00")
        assert extracts[0].invoice_type == InvoiceTypeCode.POA
        assert extracts[0].tax_code == TaxCode.ZERO_VAT
