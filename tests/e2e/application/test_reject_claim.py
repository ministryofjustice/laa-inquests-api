from sqlmodel import select

from app.auth.rbac import Role
from app.models.claim.enums import ClaimStatus
from app.models.claim.index import ClaimDecision, DecisionReason
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from app.models.notifications.enums import NotificationType
from tests.factories.builders import build_poa_claim
from tests.factories.persisted import create_application, create_claim


def _reject_payload(overrides=None):
    payload = {"justification": "Claim rejected following manual assessment."}
    if overrides is not None:
        payload.update(overrides)
    return payload


def test_204_reject_claim_creates_decision_reason_and_updates_status(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application, preset=build_poa_claim)

    response = client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}/reject",
        json=_reject_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
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
    session, client, mock_gov_notify, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application, preset=build_poa_claim)

    response = client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}/reject",
        json=_reject_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
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


def test_204_reject_final_bill_claim_sends_rejection_email(
    session, client, mock_gov_notify, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application)

    response = client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}/reject",
        json=_reject_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 204
    mock_gov_notify.send_claim_rejected_decision_email.assert_called_once_with(
        claim=claim,
        application=claim.application,
        reject_reason=_reject_payload()["justification"],
        recipient_email=claim.claimant_id,
        firm_name="Test Firm Name",
    )


def test_204_reject_claim_allows_re_rejecting_and_creates_new_decision(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application, preset=build_poa_claim)

    for _ in range(2):
        response = client.patch(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}/reject",
            json=_reject_payload(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
            },
        )
        assert response.status_code == 204

    decisions = session.exec(
        select(ClaimDecision).where(ClaimDecision.claim_id == claim.claim_id)
    ).all()
    assert len(decisions) == 2


def test_404_reject_claim_when_application_does_not_exist(client):
    response = client.patch(
        "/applications/999999/claims/1/reject",
        json=_reject_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"


def test_404_reject_claim_when_claim_does_not_exist(client, seeded_application):
    laa_reference = seeded_application.laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/claims/999999/reject",
        json=_reject_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"


def test_404_reject_claim_when_claim_belongs_to_another_application(
    session, client, seeded_application
):
    existing = seeded_application
    other_application = create_application(session)

    claim = create_claim(session, existing, preset=build_poa_claim)

    response = client.patch(
        f"/applications/{other_application.laa_reference}/claims/{claim.claim_reference}/reject",
        json=_reject_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Claim not found"


def test_422_reject_claim_when_justification_missing(
    session, client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    claim = create_claim(session, seeded_application, preset=build_poa_claim)

    response = client.patch(
        f"/applications/{laa_reference}/claims/{claim.claim_reference}/reject",
        json={},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 422


def test_204_reject_claim_creates_history_event(session, client, seeded_application):
    application = seeded_application
    claim = create_claim(session, application, preset=build_poa_claim)

    response = client.patch(
        f"/applications/{application.laa_reference}/claims/{claim.claim_reference}/reject",
        json=_reject_payload(),
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


def test_204_reject_final_bill_claim_creates_history_event(
    session, client, seeded_application
):
    application = seeded_application
    claim = create_claim(session, application)

    response = client.patch(
        f"/applications/{application.laa_reference}/claims/{claim.claim_reference}/reject",
        json=_reject_payload(),
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
