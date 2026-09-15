from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import select

from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimStatus,
    ClaimType,
    InvoiceTypeCode,
    POAType,
    TaxCode,
)
from app.models.claim.index import Claim, ClaimPaymentExtract


def _pay_in_full_payload(overrides=None):
    payload = {
        "profitCostNet": "1000.00",
        "profitCostGross": "1200.00",
        "profitCostVatZero": None,
        "disbursementNet": "100.00",
        "disbursementGross": "200.00",
        "disbursementVatZero": "50.00",
    }
    if overrides is not None:
        payload.update(overrides)
    return payload


def _application(session) -> Application:
    return session.exec(select(Application)).first()


def _seed_final_bill(
    session,
    application_id: int,
    *,
    gross: Decimal | None = Decimal("420.00"),
    vat_zero: Decimal | None = Decimal("200.00"),
    submission_date: datetime | None = None,
) -> Claim:
    claim = Claim(
        application_id=application_id,
        claim_type_id=ClaimType.FINAL_BILL,
        status_id=ClaimStatus.SUBMITTED,
        submission_date=submission_date or datetime.now(UTC),
        total_profit_cost_net=None,
        total_profit_cost_gross=gross,
        total_profit_cost_vat_zero=vat_zero,
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


def _seed_poa_with_extract(
    session,
    application_id: int,
    *,
    poa_type: POAType,
    status: ClaimStatus,
    invoice_amount: Decimal,
    tax_code: TaxCode,
) -> Claim:
    claim = Claim(
        application_id=application_id,
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        status_id=status,
        submission_date=datetime.now(UTC),
        total_profit_cost_net=Decimal("1000.00"),
        total_profit_cost_gross=Decimal("1200.00"),
        poa_type_id=poa_type,
        claimant_id="claimant-123@provider.co.uk",
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)

    extract = ClaimPaymentExtract(
        claim_id=claim.claim_id,
        sequence_number=1,
        invoice_number=f"{claim.claim_id}_001",
        invoice_amount=invoice_amount,
        invoice_date=claim.submission_date.date(),
        invoice_type=InvoiceTypeCode.POA,
        tax_code=tax_code,
    )
    session.add(extract)
    session.commit()
    return claim


def _pay_in_full(client, auth_token, laa_reference, claim_id, overrides=None):
    return client.patch(
        f"/applications/{laa_reference}/claims/{claim_id}/pay-in-full",
        json=_pay_in_full_payload(overrides),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )


def _extracts_for(session, claim_id: int) -> list[ClaimPaymentExtract]:
    return list(
        session.exec(
            select(ClaimPaymentExtract)
            .where(ClaimPaymentExtract.claim_id == claim_id)
            .order_by(ClaimPaymentExtract.sequence_number.asc())
        ).all()
    )


def test_204_final_bill_mixed_vat_splits_into_two_fee_lines(
    session, client, auth_token
):
    application = _application(session)
    claim = _seed_final_bill(
        session,
        application.application_id,
        gross=Decimal("420.00"),
        vat_zero=Decimal("200.00"),
    )

    response = _pay_in_full(
        client, auth_token, application.laa_reference, claim.claim_id
    )

    assert response.status_code == 204

    extracts = _extracts_for(session, claim.claim_id)
    assert len(extracts) == 2

    assert extracts[0].invoice_number == f"{claim.claim_id}_001"
    assert extracts[0].invoice_amount == Decimal("220.00")
    assert extracts[0].tax_code == TaxCode.GB_VAT_20
    assert extracts[0].invoice_type == InvoiceTypeCode.FINAL_BILL_FEES
    assert extracts[0].invoice_date == claim.submission_date.date()

    assert extracts[1].invoice_number == f"{claim.claim_id}_002"
    assert extracts[1].invoice_amount == Decimal("200.00")
    assert extracts[1].tax_code == TaxCode.ZERO_VAT
    assert extracts[1].invoice_type == InvoiceTypeCode.FINAL_BILL_FEES


def test_204_final_bill_gross_only_creates_single_twenty_percent_line(
    session, client, auth_token
):
    application = _application(session)
    claim = _seed_final_bill(
        session,
        application.application_id,
        gross=Decimal("420.00"),
        vat_zero=None,
    )

    response = _pay_in_full(
        client, auth_token, application.laa_reference, claim.claim_id
    )

    assert response.status_code == 204

    extracts = _extracts_for(session, claim.claim_id)
    assert len(extracts) == 1
    assert extracts[0].invoice_amount == Decimal("420.00")
    assert extracts[0].tax_code == TaxCode.GB_VAT_20
    assert extracts[0].invoice_type == InvoiceTypeCode.FINAL_BILL_FEES


def test_204_final_bill_vat_zero_only_creates_single_zero_vat_line(
    session, client, auth_token
):
    application = _application(session)
    claim = _seed_final_bill(
        session,
        application.application_id,
        gross=None,
        vat_zero=Decimal("200.00"),
    )

    response = _pay_in_full(
        client, auth_token, application.laa_reference, claim.claim_id
    )

    assert response.status_code == 204

    extracts = _extracts_for(session, claim.claim_id)
    assert len(extracts) == 1
    assert extracts[0].invoice_amount == Decimal("200.00")
    assert extracts[0].tax_code == TaxCode.ZERO_VAT


def test_204_final_bill_recoups_profit_cost_pay_in_full_poa_claims_after_fee_lines(
    session, client, auth_token
):
    application = _application(session)

    vat_poa = _seed_poa_with_extract(
        session,
        application.application_id,
        poa_type=POAType.PROFIT_COST,
        status=ClaimStatus.PAY_IN_FULL,
        invoice_amount=Decimal("960.00"),
        tax_code=TaxCode.GB_VAT_20,
    )
    zero_poa = _seed_poa_with_extract(
        session,
        application.application_id,
        poa_type=POAType.PROFIT_COST,
        status=ClaimStatus.PAY_IN_FULL,
        invoice_amount=Decimal("800.00"),
        tax_code=TaxCode.ZERO_VAT,
    )

    claim = _seed_final_bill(
        session,
        application.application_id,
        gross=Decimal("420.00"),
        vat_zero=Decimal("200.00"),
    )

    response = _pay_in_full(
        client, auth_token, application.laa_reference, claim.claim_id
    )

    assert response.status_code == 204

    extracts = _extracts_for(session, claim.claim_id)
    assert [e.invoice_number for e in extracts] == [
        f"{claim.claim_id}_001",
        f"{claim.claim_id}_002",
        f"{claim.claim_id}_003",
        f"{claim.claim_id}_004",
    ]

    # Fee lines first
    assert extracts[0].invoice_type == InvoiceTypeCode.FINAL_BILL_FEES
    assert extracts[1].invoice_type == InvoiceTypeCode.FINAL_BILL_FEES

    # Recoupments after, negative, preserving original tax codes
    assert extracts[2].invoice_type == InvoiceTypeCode.RECOUPED
    assert extracts[2].invoice_amount == Decimal("-960.00")
    assert extracts[2].tax_code == TaxCode.GB_VAT_20
    assert extracts[3].invoice_type == InvoiceTypeCode.RECOUPED
    assert extracts[3].invoice_amount == Decimal("-800.00")
    assert extracts[3].tax_code == TaxCode.ZERO_VAT

    # Recoupment invoice date is the final bill decision date (today)
    assert extracts[2].invoice_date == datetime.now(UTC).date()

    # Original POA extracts remain untouched
    assert len(_extracts_for(session, vat_poa.claim_id)) == 1
    assert len(_extracts_for(session, zero_poa.claim_id)) == 1


def test_204_final_bill_excludes_non_profit_cost_and_unapproved_poa_claims(
    session, client, auth_token
):
    application = _application(session)

    _seed_poa_with_extract(
        session,
        application.application_id,
        poa_type=POAType.PROFIT_COST,
        status=ClaimStatus.PAY_IN_FULL,
        invoice_amount=Decimal("960.00"),
        tax_code=TaxCode.GB_VAT_20,
    )
    # Excluded: profit cost but not pay-in-full
    _seed_poa_with_extract(
        session,
        application.application_id,
        poa_type=POAType.PROFIT_COST,
        status=ClaimStatus.SUBMITTED,
        invoice_amount=Decimal("500.00"),
        tax_code=TaxCode.GB_VAT_20,
    )
    # Excluded: non profit cost POA
    _seed_poa_with_extract(
        session,
        application.application_id,
        poa_type=POAType.EXPERT_COST,
        status=ClaimStatus.PAY_IN_FULL,
        invoice_amount=Decimal("300.00"),
        tax_code=TaxCode.GB_VAT_20,
    )

    claim = _seed_final_bill(
        session,
        application.application_id,
        gross=Decimal("420.00"),
        vat_zero=None,
    )

    response = _pay_in_full(
        client, auth_token, application.laa_reference, claim.claim_id
    )

    assert response.status_code == 204

    extracts = _extracts_for(session, claim.claim_id)
    # 1 fee line + 1 recoupment (only the pay-in-full profit cost POA)
    assert len(extracts) == 2
    assert extracts[0].invoice_type == InvoiceTypeCode.FINAL_BILL_FEES
    assert extracts[1].invoice_type == InvoiceTypeCode.RECOUPED
    assert extracts[1].invoice_amount == Decimal("-960.00")


def test_204_final_bill_with_no_recoupable_poa_creates_only_fee_lines(
    session, client, auth_token
):
    application = _application(session)
    claim = _seed_final_bill(
        session,
        application.application_id,
        gross=Decimal("420.00"),
        vat_zero=Decimal("200.00"),
    )

    response = _pay_in_full(
        client, auth_token, application.laa_reference, claim.claim_id
    )

    assert response.status_code == 204

    extracts = _extracts_for(session, claim.claim_id)
    assert len(extracts) == 2
    assert all(e.invoice_type == InvoiceTypeCode.FINAL_BILL_FEES for e in extracts)


def test_204_re_deciding_final_bill_does_not_duplicate_payment_extract(
    session, client, auth_token
):
    application = _application(session)
    claim = _seed_final_bill(
        session,
        application.application_id,
        gross=Decimal("420.00"),
        vat_zero=Decimal("200.00"),
    )

    for _ in range(2):
        response = _pay_in_full(
            client, auth_token, application.laa_reference, claim.claim_id
        )
        assert response.status_code == 204

    extracts = _extracts_for(session, claim.claim_id)
    assert len(extracts) == 2


def test_204_final_bill_recoups_mixed_poa_combinations_in_order(
    session, client, auth_token
):
    application = _application(session)

    # Two VAT and one zero-VAT profit cost POA, all pay-in-full -> recouped
    _seed_poa_with_extract(
        session,
        application.application_id,
        poa_type=POAType.PROFIT_COST,
        status=ClaimStatus.PAY_IN_FULL,
        invoice_amount=Decimal("960.00"),
        tax_code=TaxCode.GB_VAT_20,
    )
    _seed_poa_with_extract(
        session,
        application.application_id,
        poa_type=POAType.PROFIT_COST,
        status=ClaimStatus.PAY_IN_FULL,
        invoice_amount=Decimal("480.00"),
        tax_code=TaxCode.GB_VAT_20,
    )
    _seed_poa_with_extract(
        session,
        application.application_id,
        poa_type=POAType.PROFIT_COST,
        status=ClaimStatus.PAY_IN_FULL,
        invoice_amount=Decimal("800.00"),
        tax_code=TaxCode.ZERO_VAT,
    )
    # Excluded: non-profit-cost POA (expert + non-expert disbursement)
    _seed_poa_with_extract(
        session,
        application.application_id,
        poa_type=POAType.EXPERT_COST,
        status=ClaimStatus.PAY_IN_FULL,
        invoice_amount=Decimal("300.00"),
        tax_code=TaxCode.GB_VAT_20,
    )
    _seed_poa_with_extract(
        session,
        application.application_id,
        poa_type=POAType.NON_EXPERT_DISBURSEMENT,
        status=ClaimStatus.PAY_IN_FULL,
        invoice_amount=Decimal("150.00"),
        tax_code=TaxCode.ZERO_VAT,
    )
    # Excluded: profit cost POA that was not paid in full
    _seed_poa_with_extract(
        session,
        application.application_id,
        poa_type=POAType.PROFIT_COST,
        status=ClaimStatus.REJECTED,
        invoice_amount=Decimal("500.00"),
        tax_code=TaxCode.GB_VAT_20,
    )

    claim = _seed_final_bill(
        session,
        application.application_id,
        gross=Decimal("420.00"),
        vat_zero=Decimal("200.00"),
    )

    response = _pay_in_full(
        client, auth_token, application.laa_reference, claim.claim_id
    )

    assert response.status_code == 204

    extracts = _extracts_for(session, claim.claim_id)

    # 2 fee lines + 3 recoupments (only pay-in-full profit cost POAs)
    assert [e.invoice_number for e in extracts] == [
        f"{claim.claim_id}_001",
        f"{claim.claim_id}_002",
        f"{claim.claim_id}_003",
        f"{claim.claim_id}_004",
        f"{claim.claim_id}_005",
    ]
    assert [e.invoice_type for e in extracts] == [
        InvoiceTypeCode.FINAL_BILL_FEES,
        InvoiceTypeCode.FINAL_BILL_FEES,
        InvoiceTypeCode.RECOUPED,
        InvoiceTypeCode.RECOUPED,
        InvoiceTypeCode.RECOUPED,
    ]
    assert [e.invoice_amount for e in extracts[2:]] == [
        Decimal("-960.00"),
        Decimal("-480.00"),
        Decimal("-800.00"),
    ]
    assert [e.tax_code for e in extracts[2:]] == [
        TaxCode.GB_VAT_20,
        TaxCode.GB_VAT_20,
        TaxCode.ZERO_VAT,
    ]
