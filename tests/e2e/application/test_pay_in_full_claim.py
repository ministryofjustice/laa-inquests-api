from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import select

from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus, ClaimType, POAType
from app.models.claim.index import Claim, ClaimDecision, ClaimDecisionAmount
from app.models.history.enums import HistoryEventReference
from app.models.history.index import HistoryEvent
from tests.e2e.factories import create_application_in_db


def _pay_in_full_payload(overrides=None):
    payload = {
        "profitCostNet": "1000.00",
        "profitCostGross": "1200.00",
        "profitCostVatZero": None,
        "disbursementNet": "100.00",
        "disbursementGross": "120.00",
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
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


def test_204_pay_in_full_claim_creates_decision_amount_and_updates_status(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_id}/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
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
    assert amount.disbursement_gross == Decimal("120.00")
    assert amount.disbursement_vat_zero == Decimal("50.00")

    session.refresh(claim)
    assert claim.status_id == ClaimStatus.PAY_IN_FULL


def test_204_pay_in_full_claim_creates_history_event(session, client, auth_token):
    application = session.exec(select(Application)).first()
    claim = _seed_claim(session, application.laa_reference)

    response = client.patch(
        f"/applications/{application.laa_reference}/claims/{claim.claim_id}/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
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


def test_204_pay_in_full_claim_persists_partial_amounts_as_null(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_id}/pay-in-full",
        json=_pay_in_full_payload(
            {
                "profitCostNet": None,
                "profitCostGross": None,
                "profitCostVatZero": "500.00",
                "disbursementNet": None,
                "disbursementGross": None,
                "disbursementVatZero": None,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
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
    assert amount.disbursement_vat_zero is None


def test_204_pay_in_full_claim_allows_re_deciding_and_creates_new_decision_and_amount(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    for _ in range(2):
        response = client.patch(
            f"/applications/{laa_reference}/claims/{claim.claim_id}/pay-in-full",
            json=_pay_in_full_payload(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}",
            },
        )
        assert response.status_code == 204

    decisions = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim.claim_id)
    ).all()
    assert len(decisions) == 2

    amounts = session.exec(
        select(ClaimDecisionAmount).where(
            ClaimDecisionAmount.claim_decision_id.in_(
                [d.claim_decision_id for d in decisions]
            )
        )
    ).all()
    assert len(amounts) == 2


def test_404_pay_in_full_claim_when_application_does_not_exist(client, auth_token):
    response = client.patch(
        "/applications/999999/claims/1/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"


def test_404_pay_in_full_claim_when_claim_does_not_exist(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/claims/999999/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"


def test_404_pay_in_full_claim_when_claim_belongs_to_another_application(
    session, client, auth_token
):
    existing = session.exec(select(Application)).first()
    other_application = create_application_in_db(session)

    claim = _seed_claim(session, existing.laa_reference)

    response = client.patch(
        f"/applications/{other_application.laa_reference}/claims/{claim.claim_id}/pay-in-full",
        json=_pay_in_full_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"


def _post_pay_in_full(session, client, auth_token, overrides):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)
    return client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_id}/pay-in-full",
        json=_pay_in_full_payload(overrides),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )


def test_422_pay_in_full_claim_when_profit_cost_net_without_gross(
    session, client, auth_token
):
    response = _post_pay_in_full(
        session,
        client,
        auth_token,
        {"profitCostGross": None, "profitCostVatZero": None},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["errorCode"] == "MISSING_GROSS_TOTAL_WHEN_NET_ENTERED"
    assert detail["message"] == "Enter the gross total for profit costs including VAT"


def test_422_pay_in_full_claim_when_profit_cost_gross_without_net(
    session, client, auth_token
):
    response = _post_pay_in_full(
        session,
        client,
        auth_token,
        {"profitCostNet": None, "profitCostVatZero": None},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["errorCode"] == "MISSING_NET_TOTAL_WHEN_GROSS_ENTERED"
    assert detail["message"] == "Enter the net total for profit costs excluding VAT"


def test_422_pay_in_full_claim_when_all_profit_cost_totals_missing(
    session, client, auth_token
):
    response = _post_pay_in_full(
        session,
        client,
        auth_token,
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


def test_422_pay_in_full_claim_when_vat_zero_mixed_with_net_and_gross(
    session, client, auth_token
):
    response = _post_pay_in_full(
        session,
        client,
        auth_token,
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


def test_422_pay_in_full_claim_when_net_higher_than_gross(session, client, auth_token):
    response = _post_pay_in_full(
        session,
        client,
        auth_token,
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
    session, client, auth_token
):
    response = _post_pay_in_full(
        session,
        client,
        auth_token,
        {"profitCostNet": "1000.001", "profitCostVatZero": None},
    )

    assert response.status_code == 422


def test_204_pay_in_full_claim_allows_zero_profit_cost_totals(
    session, client, auth_token
):
    response = _post_pay_in_full(
        session,
        client,
        auth_token,
        {
            "profitCostNet": "0.00",
            "profitCostGross": "0.00",
            "profitCostVatZero": None,
        },
    )

    assert response.status_code == 204


def test_204_pay_in_full_claim_allows_vat_zero_only(session, client, auth_token):
    response = _post_pay_in_full(
        session,
        client,
        auth_token,
        {
            "profitCostNet": None,
            "profitCostGross": None,
            "profitCostVatZero": "500.00",
        },
    )

    assert response.status_code == 204
