import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import select

from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimStatus,
    ClaimType,
    InvoiceTypeCode,
    POAType,
    TaxCode,
)
from app.models.claim.index import (
    Claim,
    ClaimDecision,
    ClaimDecisionAmount,
    ClaimPaymentExtract,
)
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from app.models.notifications.enums import NotificationType
from tests.e2e.factories import create_application_in_db


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


def _seed_claim(
    session,
    laa_reference: int,
    status: ClaimStatus = ClaimStatus.SUBMITTED,
    claimant_id: str | None = "claimant-123@provider.co.uk",
    claim_type: ClaimType = ClaimType.FINAL_BILL,
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
        status_id=status,
        submission_date=datetime.now(UTC),
        total_profit_cost_net=Decimal("1000.00"),
        total_profit_cost_gross=Decimal("1200.00"),
        total_profit_cost_vat_zero=Decimal("500.00"),
        poa_type_id=POAType.PROFIT_COST,
        claimant_id=claimant_id,
        claim_reference=f"INQC-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}",
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


def test_204_pay_in_full_claim_creates_decision_amount_and_updates_status(
    session, client
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 204

    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim.claim_id)
    ).one()
    assert decision.decision == "PAY_IN_FULL"

    amount = session.exec(
        select(ClaimDecisionAmount).where(
            ClaimDecisionAmount.claim_decision_id == decision.claim_decision_id
        )
    ).one()
    assert amount.profit_cost_net == Decimal("1000.00")
    assert amount.profit_cost_gross == Decimal("1200.00")
    assert amount.profit_cost_vat_zero is None
    assert amount.disbursement_net == Decimal("100.00")
    assert amount.disbursement_gross == Decimal("200.00")
    assert amount.disbursement_vat_zero == Decimal("50.00")

    session.refresh(claim)
    assert claim.status_id == ClaimStatus.PAY_IN_FULL


def test_204_pay_in_full_claim_creates_history_event(session, client):
    application = session.exec(select(Application)).first()
    claim = _seed_claim(session, application.laa_reference)

    response = client.patch(
        f"/applications/{application.laa_reference}/claims/{claim.claim_reference}/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 204

    history_event = session.exec(
        select(HistoryEvent).where(
            (HistoryEvent.application_id == application.application_id)
            & (
                HistoryEvent.event_reference
                == HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED
            )
        )
    ).one()

    assert (
        history_event.event_reference
        == HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED
    )
    assert history_event.event_data["claim_decision"] == "PAY_IN_FULL"
    assert history_event.event_data["profit_cost_net"] == "1000.00"
    assert history_event.event_data["disbursement_vat_zero"] == "50.00"


def test_204_pay_in_full_claim_persists_partial_amounts_as_null(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}/pay-in-full",
        json=_pay_in_full_payload(
            {
                "profitCostNet": None,
                "profitCostGross": None,
                "profitCostVatZero": "500.00",
                "disbursementNet": None,
                "disbursementGross": None,
                "disbursementVatZero": "50.00",
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 204

    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim.claim_id)
    ).one()
    amount = session.exec(
        select(ClaimDecisionAmount).where(
            ClaimDecisionAmount.claim_decision_id == decision.claim_decision_id
        )
    ).one()
    assert amount.profit_cost_net is None
    assert amount.profit_cost_gross is None
    assert amount.profit_cost_vat_zero == Decimal("500.00")
    assert amount.disbursement_net is None
    assert amount.disbursement_gross is None
    assert amount.disbursement_vat_zero == Decimal("50.00")


def test_204_pay_in_full_claim_creates_single_decision_and_amount(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )
    assert response.status_code == 204

    decisions = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim.claim_id)
    ).all()
    assert len(decisions) == 1

    amounts = session.exec(
        select(ClaimDecisionAmount).where(
            ClaimDecisionAmount.claim_decision_id.in_(
                [d.claim_decision_id for d in decisions]
            )
        )
    ).all()
    assert len(amounts) == 1


def test_404_pay_in_full_claim_when_application_does_not_exist(client):
    response = client.patch(
        "/applications/999999/claims/1/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"


def test_404_pay_in_full_claim_when_claim_does_not_exist(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/claims/999999/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"


def test_404_pay_in_full_claim_when_claim_belongs_to_another_application(
    session, client
):
    existing = session.exec(select(Application)).first()
    other_application = create_application_in_db(session)

    claim = _seed_claim(session, existing.laa_reference)

    response = client.patch(
        f"/applications/{other_application.laa_reference}/claims/{claim.claim_reference}/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"


def _post_pay_in_full(session, client, overrides):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)
    return client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}/pay-in-full",
        json=_pay_in_full_payload(overrides),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )


def test_422_pay_in_full_claim_when_profit_cost_net_without_gross(session, client):
    response = _post_pay_in_full(
        session,
        client,
        {"profitCostGross": None, "profitCostVatZero": None},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["errorCode"] == "MISSING_GROSS_TOTAL_WHEN_NET_ENTERED"
    assert detail["message"] == "Enter the gross total for profit costs including VAT"


def test_422_pay_in_full_claim_when_profit_cost_gross_without_net(session, client):
    response = _post_pay_in_full(
        session,
        client,
        {"profitCostNet": None, "profitCostVatZero": None},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["errorCode"] == "MISSING_NET_TOTAL_WHEN_GROSS_ENTERED"
    assert detail["message"] == "Enter the net total for profit costs excluding VAT"


def test_422_pay_in_full_claim_when_all_profit_cost_totals_missing(session, client):
    response = _post_pay_in_full(
        session,
        client,
        {
            "profitCostNet": None,
            "profitCostGross": None,
            "profitCostVatZero": None,
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["errorCode"] == "MISSING_TOTAL_CLAIM_COST"
    assert detail["message"] == "Complete the total value of the claim to continue"


def test_422_pay_in_full_claim_when_vat_zero_mixed_with_net_and_gross(session, client):
    response = _post_pay_in_full(
        session,
        client,
        {
            "profitCostNet": "1000.00",
            "profitCostGross": "1200.00",
            "profitCostVatZero": "500.00",
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["errorCode"] == "PROFIT_COST_MIXED_VAT"
    assert (
        detail["message"]
        == "You cannot submit a total profit cost claim with both 0% and 20% VAT"
    )


def test_422_pay_in_full_claim_when_net_higher_than_gross(session, client):
    response = _post_pay_in_full(
        session,
        client,
        {
            "profitCostNet": "1300.00",
            "profitCostGross": "1200.00",
            "profitCostVatZero": None,
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["errorCode"] == "NET_TOTAL_HIGHER_THAN_GROSS_TOTAL"
    assert detail["message"] == "Net total cannot be higher than the gross total value"


def test_422_pay_in_full_claim_when_profit_cost_has_more_than_two_decimal_places(
    session, client
):
    response = _post_pay_in_full(
        session,
        client,
        {"profitCostNet": "1000.001", "profitCostVatZero": None},
    )

    assert response.status_code == 422


def test_204_pay_in_full_claim_allows_zero_profit_cost_totals(session, client):
    response = _post_pay_in_full(
        session,
        client,
        {
            "profitCostNet": "0.00",
            "profitCostGross": "0.00",
            "profitCostVatZero": None,
        },
    )

    assert response.status_code == 204


def test_204_pay_in_full_claim_allows_vat_zero_only(session, client):
    response = _post_pay_in_full(
        session,
        client,
        {
            "profitCostNet": None,
            "profitCostGross": None,
            "profitCostVatZero": "500.00",
        },
    )

    assert response.status_code == 204


def test_422_pay_in_full_claim_when_all_disbursement_totals_missing(session, client):
    response = _post_pay_in_full(
        session,
        client,
        {
            "disbursementNet": None,
            "disbursementGross": None,
            "disbursementVatZero": None,
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["errorCode"] == "MISSING_DISBURSEMENT_TOTAL"
    assert detail["message"] == "Enter the total of the claim to continue"


def test_422_pay_in_full_claim_when_disbursement_net_without_gross(session, client):
    response = _post_pay_in_full(
        session,
        client,
        {"disbursementGross": None, "disbursementVatZero": None},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["errorCode"] == "MISSING_DISBURSEMENT_GROSS_WHEN_NET_ENTERED"
    assert detail["message"] == "Enter the gross total of the claim"


def test_422_pay_in_full_claim_when_disbursement_gross_without_net(session, client):
    response = _post_pay_in_full(
        session,
        client,
        {"disbursementNet": None, "disbursementVatZero": None},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["errorCode"] == "MISSING_DISBURSEMENT_NET_WHEN_GROSS_ENTERED"
    assert (
        detail["message"] == "Enter the net total for disbursement costs excluding VAT"
    )


def test_422_pay_in_full_claim_when_disbursement_gross_not_greater_than_total(
    session, client
):
    response = _post_pay_in_full(
        session,
        client,
        {
            "disbursementNet": "100.00",
            "disbursementGross": "120.00",
            "disbursementVatZero": "50.00",
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["errorCode"] == "DISBURSEMENT_GROSS_NOT_GREATER_THAN_TOTAL"
    assert (
        detail["message"]
        == "The gross total must be greater than the 0% VAT and net total combined"
    )


def test_422_pay_in_full_claim_when_disbursement_has_more_than_two_decimal_places(
    session, client
):
    response = _post_pay_in_full(
        session,
        client,
        {"disbursementNet": "100.001"},
    )

    assert response.status_code == 422


def test_204_pay_in_full_claim_allows_disbursement_vat_zero_only(session, client):
    response = _post_pay_in_full(
        session,
        client,
        {
            "disbursementNet": None,
            "disbursementGross": None,
            "disbursementVatZero": "50.00",
        },
    )

    assert response.status_code == 204


def test_204_pay_in_full_claim_allows_disbursement_vat_zero_net_and_gross(
    session, client
):
    response = _post_pay_in_full(
        session,
        client,
        {
            "disbursementNet": "100.00",
            "disbursementGross": "200.00",
            "disbursementVatZero": "50.00",
        },
    )

    assert response.status_code == 204


def test_204_pay_in_full_claim_sends_final_bill_paid_email_to_provider(
    session, client, mock_gov_notify
):
    application = session.exec(select(Application)).first()
    claim = _seed_claim(session, application.laa_reference)

    response = client.patch(
        f"/applications/{application.laa_reference}/claims/{claim.claim_reference}/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 204
    mock_gov_notify.send_claim_final_bill_paid_decision_email.assert_called_once()

    call_kwargs = (
        mock_gov_notify.send_claim_final_bill_paid_decision_email.call_args.kwargs
    )
    assert call_kwargs["claim"].claim_id == claim.claim_id
    assert call_kwargs["application"].laa_reference == application.laa_reference
    assert call_kwargs["recipient_email"] == application.provider.email_address
    assert call_kwargs["firm_name"] == "Test Firm Name"
    assert call_kwargs["decision_amounts"].profit_cost_net == Decimal("1000.00")
    assert call_kwargs["decision_amounts"].profit_cost_gross == Decimal("1200.00")
    assert call_kwargs["decision_amounts"].disbursement_net == Decimal("100.00")
    assert call_kwargs["decision_amounts"].disbursement_gross == Decimal("200.00")
    assert call_kwargs["decision_amounts"].disbursement_vat_zero == Decimal("50.00")


def test_204_pay_in_full_claim_creates_email_history_event(session, client):
    application = session.exec(select(Application)).first()
    claim = _seed_claim(session, application.laa_reference)

    response = client.patch(
        f"/applications/{application.laa_reference}/claims/{claim.claim_reference}/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 204

    history_event = session.exec(
        select(HistoryEvent).where(
            (HistoryEvent.application_id == application.application_id)
            & (
                HistoryEvent.event_reference
                == HistoryEventReference.CLAIM_FINAL_BILL_PAID_EMAIL
            )
        )
    ).one()

    assert (
        history_event.event_reference
        == HistoryEventReference.CLAIM_FINAL_BILL_PAID_EMAIL
    )
    assert history_event.actor == ActorType.SYSTEM
    assert history_event.actor_type == ActorType.SYSTEM
    assert history_event.event_data == {
        "recipient": application.provider.email_address,
        "channel": NotificationType.EMAIL,
    }


def test_500_pay_in_full_claim_fails_when_final_bill_paid_email_fails(
    session, client, mock_gov_notify
):
    application = session.exec(select(Application)).first()
    claim = _seed_claim(session, application.laa_reference)
    mock_gov_notify.send_claim_final_bill_paid_decision_email.side_effect = Exception(
        "Gov Notify unavailable"
    )

    response = client.patch(
        f"/applications/{application.laa_reference}/claims/{claim.claim_reference}/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 500

    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim.claim_id)
    ).one_or_none()
    assert decision is None

    session.refresh(claim)
    assert claim.status_id == ClaimStatus.SUBMITTED


def _seed_paid_poa_claim_with_extract(session, laa_reference: int) -> Claim:
    application_id = (
        session.exec(
            select(Application).where(Application.laa_reference == laa_reference)
        )
        .one()
        .application_id
    )
    poa_claim = Claim(
        application_id=application_id,
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        status_id=ClaimStatus.PAY_IN_FULL,
        submission_date=datetime.now(UTC),
        poa_type_id=POAType.PROFIT_COST,
        claim_reference=f"INQC-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}",
    )
    session.add(poa_claim)
    session.commit()
    session.refresh(poa_claim)

    session.add_all(
        [
            ClaimPaymentExtract(
                claim_id=poa_claim.claim_id,
                sequence_number=1,
                invoice_number=f"{poa_claim.claim_reference}_001",
                invoice_amount=Decimal("800.00"),
                invoice_date=datetime.now(UTC).date(),
                invoice_type=InvoiceTypeCode.POA,
                tax_code=TaxCode.GB_VAT_20,
            ),
            ClaimPaymentExtract(
                claim_id=poa_claim.claim_id,
                sequence_number=2,
                invoice_number=f"{poa_claim.claim_reference}_002",
                invoice_amount=Decimal("200.00"),
                invoice_date=datetime.now(UTC).date(),
                invoice_type=InvoiceTypeCode.POA,
                tax_code=TaxCode.ZERO_VAT,
            ),
        ]
    )
    session.commit()
    return poa_claim


def _extract_lines_for(session, claim_id: int) -> list[ClaimPaymentExtract]:
    return list(
        session.exec(
            select(ClaimPaymentExtract)
            .where(ClaimPaymentExtract.claim_id == claim_id)
            .order_by(ClaimPaymentExtract.sequence_number)
        ).all()
    )


def test_204_pay_in_full_final_bill_creates_payment_extract_in_expected_order(
    session, client
):
    application = session.exec(select(Application)).first()
    poa_claim = _seed_paid_poa_claim_with_extract(session, application.laa_reference)
    claim = _seed_claim(session, application.laa_reference)

    response = client.patch(
        f"/applications/{application.laa_reference}/claims/{claim.claim_reference}/pay-in-full",
        json=_pay_in_full_payload(
            {
                "profitCostNet": "1000.00",
                "profitCostGross": "1200.00",
                "profitCostVatZero": None,
                "disbursementNet": "100.00",
                "disbursementGross": "200.00",
                "disbursementVatZero": "50.00",
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 204

    lines = _extract_lines_for(session, claim.claim_id)
    assert len(lines) == 5

    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim.claim_id)
    ).one()
    decision_date = decision.created_at.date()

    fees, disb_standard, disb_zero, recoup_standard, recoup_zero = lines

    assert fees.invoice_number == f"{claim.claim_reference}_001"
    assert fees.invoice_amount == Decimal("1200.00")
    assert fees.invoice_type == InvoiceTypeCode.FINAL_BILL_FEES
    assert fees.tax_code == TaxCode.GB_VAT_20
    assert fees.invoice_date == claim.submission_date.date()

    assert disb_standard.invoice_number == f"{claim.claim_reference}_002"
    assert disb_standard.invoice_amount == Decimal("150.00")
    assert disb_standard.invoice_type == InvoiceTypeCode.FINAL_BILL_DISBURSEMENT
    assert disb_standard.tax_code == TaxCode.GB_VAT_20

    assert disb_zero.invoice_number == f"{claim.claim_reference}_003"
    assert disb_zero.invoice_amount == Decimal("50.00")
    assert disb_zero.invoice_type == InvoiceTypeCode.FINAL_BILL_DISBURSEMENT
    assert disb_zero.tax_code == TaxCode.ZERO_VAT

    assert recoup_standard.invoice_number == f"{poa_claim.claim_reference}_001-R"
    assert recoup_standard.invoice_amount == Decimal("-800.00")
    assert recoup_standard.invoice_type == InvoiceTypeCode.RECOUPED
    assert recoup_standard.tax_code == TaxCode.GB_VAT_20
    assert recoup_standard.invoice_date == decision_date

    assert recoup_zero.invoice_number == f"{poa_claim.claim_reference}_002-R"
    assert recoup_zero.invoice_amount == Decimal("-200.00")
    assert recoup_zero.invoice_type == InvoiceTypeCode.RECOUPED
    assert recoup_zero.tax_code == TaxCode.ZERO_VAT


def test_204_pay_in_full_fees_line_uses_zero_vat_when_vat_zero_supplied(
    session, client
):
    application = session.exec(select(Application)).first()
    claim = _seed_claim(session, application.laa_reference)

    response = client.patch(
        f"/applications/{application.laa_reference}/claims/{claim.claim_reference}/pay-in-full",
        json=_pay_in_full_payload(
            {
                "profitCostNet": None,
                "profitCostGross": None,
                "profitCostVatZero": "900.00",
                "disbursementNet": None,
                "disbursementGross": None,
                "disbursementVatZero": "50.00",
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 204

    lines = _extract_lines_for(session, claim.claim_id)
    fees = next(
        line for line in lines if line.invoice_type == InvoiceTypeCode.FINAL_BILL_FEES
    )
    assert fees.invoice_amount == Decimal("900.00")
    assert fees.tax_code == TaxCode.ZERO_VAT


def test_204_pay_in_full_final_bill_creates_no_recoupments_without_paid_poa_claims(
    session, client
):
    application = session.exec(select(Application)).first()
    claim = _seed_claim(session, application.laa_reference)

    response = client.patch(
        f"/applications/{application.laa_reference}/claims/{claim.claim_reference}/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 204

    lines = _extract_lines_for(session, claim.claim_id)
    assert all(line.invoice_type != InvoiceTypeCode.RECOUPED for line in lines)
