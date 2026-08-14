from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import select

from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus, ClaimType, POAType
from app.models.claim.index import Claim, ClaimDecision, DecisionReason


def _reject_payload(overrides=None):
    payload = {"justification": "Claim rejected following manual assessment."}
    if overrides is not None:
        payload.update(overrides)
    return payload


def _seed_claim(
    session,
    laa_reference: int,
    status: ClaimStatus = ClaimStatus.SUBMITTED,
) -> Claim:
    claim = Claim(
        laa_reference=laa_reference,
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        status_id=status,
        submission_date=datetime.now(UTC),
        total_profit_cost_net=Decimal("1000.00"),
        total_profit_cost_gross=Decimal("1200.00"),
        total_profit_cost_vat_zero=Decimal("500.00"),
        poa_type_id=POAType.PROFIT_COST,
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


def test_204_reject_claim_creates_decision_reason_and_updates_status(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.post(
        f"/applications/{laa_reference}/claims/{claim.claim_id}/reject",
        json=_reject_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 204

    decision = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim.claim_id)
    ).one()
    assert decision.decision == "REJECT"

    reason = session.exec(
        select(DecisionReason).where(
            DecisionReason.claim_decision_id == decision.claim_decision_id
        )
    ).one()
    assert reason.reason_code == "MANUAL_REJECTION"
    assert reason.justification == "Claim rejected following manual assessment."

    session.refresh(claim)
    assert claim.status_id == ClaimStatus.REJECTED


def test_204_reject_claim_allows_re_rejecting_and_creates_new_decision(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    for _ in range(2):
        response = client.post(
            f"/applications/{laa_reference}/claims/{claim.claim_id}/reject",
            json=_reject_payload(),
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


def test_404_reject_claim_when_application_does_not_exist(client, auth_token):
    response = client.post(
        "/applications/999999/claims/1/reject",
        json=_reject_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"


def test_404_reject_claim_when_claim_does_not_exist(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claims/999999/reject",
        json=_reject_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"


def test_404_reject_claim_when_claim_belongs_to_another_application(
    session, client, auth_token
):
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

    response = client.post(
        f"/applications/{other_application.laa_reference}/claims/{claim.claim_id}/reject",
        json=_reject_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"


def test_422_reject_claim_when_justification_missing(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.post(
        f"/applications/{laa_reference}/claims/{claim.claim_id}/reject",
        json={},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
