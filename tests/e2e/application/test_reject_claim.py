from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import select

from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus, ClaimType, POAType
from app.models.claim.index import Claim, ClaimDecision, DecisionReason
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from app.models.notifications.enums import NotificationType
from tests.e2e.factories import create_application_in_db


def _reject_payload(overrides=None):
    payload = {"justification": "Claim rejected following manual assessment."}
    if overrides is not None:
        payload.update(overrides)
    return payload


def _seed_claim(
    session,
    laa_reference: int,
    status: ClaimStatus = ClaimStatus.SUBMITTED,
    claimant_id: str | None = "claimant-123@provider.co.uk",
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
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
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


def test_204_reject_claim_creates_decision_reason_and_updates_status(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.patch(
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


def test_204_reject_claim_sends_rejection_email_to_claimant(
    session, client, auth_token, mock_gov_notify
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    response = client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_id}/reject",
        json=_reject_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 204
    mock_gov_notify.send_claim_rejected_decision_email.assert_called_once()

    call_kwargs = mock_gov_notify.send_claim_rejected_decision_email.call_args.kwargs
    assert call_kwargs["claim"].claim_id == claim.claim_id
    assert call_kwargs["application"].laa_reference == laa_reference
    assert call_kwargs["reject_reason"] == _reject_payload()["justification"]
    assert call_kwargs["recipient_email"] == claim.claimant_id
    assert call_kwargs["firm_name"] == "Test Firm Name"


def test_204_reject_claim_allows_re_rejecting_and_creates_new_decision(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference)

    for _ in range(2):
        response = client.patch(
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
    response = client.patch(
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

    response = client.patch(
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
    other_application = create_application_in_db(session)

    claim = _seed_claim(session, existing.laa_reference)

    response = client.patch(
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

    response = client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_id}/reject",
        json={},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422


def test_204_reject_claim_creates_history_event(session, client, auth_token):
    application = session.exec(select(Application)).first()
    claim = _seed_claim(session, application.laa_reference)
    application = session.exec(select(Application)).first()

    response = client.patch(
        f"/applications/{application.laa_reference}/claims/{claim.claim_id}/reject",
        json=_reject_payload(),
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
                == HistoryEventReference.CLAIM_REJECTED_EMAIL
            )
        )
    ).one()

    assert history_event.event_reference == HistoryEventReference.CLAIM_REJECTED_EMAIL
    assert history_event.actor == ActorType.SYSTEM
    assert history_event.actor_type == ActorType.SYSTEM
    assert history_event.event_data == {
        "recipient": application.provider.email_address,
        "channel": NotificationType.EMAIL,
    }
