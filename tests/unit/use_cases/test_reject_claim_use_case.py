from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, call

import pytest

from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    POAType,
    ReasonCode,
)
from app.models.claim.index import Claim, ClaimDecision
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.notifications.enums import NotificationType
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.create_decision_reason_port import CreateDecisionReasonPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.update_claim_status_port import UpdateClaimStatusPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.gov_notify_port import GovNotifyPort
from app.use_cases.exceptions import ApplicationNotFoundError, ClaimNotFoundError
from app.use_cases.reject_claim import RejectClaimCommand, RejectClaimUseCase


def _claim(claim_id: int = 1, laa_reference: int = 1) -> Claim:
    return Claim(
        claim_id=claim_id,
        laa_reference=laa_reference,
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        status_id=ClaimStatus.SUBMITTED,
        submission_date=datetime.now(UTC),
        total_profit_cost_net=Decimal("1000.00"),
        total_profit_cost_gross=Decimal("1200.00"),
        total_profit_cost_vat_zero=Decimal("500.00"),
        poa_type_id=POAType.PROFIT_COST,
        claimant_id="claimant-123@provider.co.uk",
    )


def _application(laa_reference: int = 1):
    application = MagicMock()
    application.laa_reference = laa_reference
    return application


def _build_use_case(claim=None, application=None):
    lookup_port = MagicMock(spec=ApplicationLookupPort)
    lookup_port.get_application_by_laa_reference.return_value = application

    get_claim_port = MagicMock(spec=GetClaimByIdPort)
    get_claim_port.get_claim_by_id.return_value = claim

    create_decision_port = MagicMock(spec=CreateClaimDecisionPort)
    create_decision_port.create_claim_decision.return_value = ClaimDecision(
        claim_decision_id=42,
        claim_id=claim.claim_id if claim is not None else 1,
        decision=ClaimDecisionStatus.REJECT,
    )

    create_reason_port = MagicMock(spec=CreateDecisionReasonPort)
    update_status_port = MagicMock(spec=UpdateClaimStatusPort)
    create_history_event_port = MagicMock(spec=CreateHistoryEventPort)

    create_history_event_port = MagicMock(spec=CreateHistoryEventPort)
    gov_notify_port = MagicMock(spec=GovNotifyPort)

    use_case = RejectClaimUseCase(
        application_lookup_port=lookup_port,
        get_claim_by_id_port=get_claim_port,
        create_claim_decision_port=create_decision_port,
        create_decision_reason_port=create_reason_port,
        update_claim_status_port=update_status_port,
        create_history_event_port=create_history_event_port,
        gov_notify_port=gov_notify_port,
    )
    return (
        use_case,
        create_decision_port,
        create_reason_port,
        update_status_port,
        create_history_event_port,
        gov_notify_port,
    )


def test_raises_application_not_found_when_application_missing():
    use_case, *_ = _build_use_case(claim=_claim(), application=None)

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute(
            RejectClaimCommand("999999", 1, "reason"), caseworker_name="Caseworker"
        )


def test_raises_claim_not_found_when_claim_missing():
    use_case, *_ = _build_use_case(claim=None, application=_application())

    with pytest.raises(ClaimNotFoundError):
        use_case.execute(
            RejectClaimCommand("1", 999999, "reason"), caseworker_name="Caseworker"
        )


def test_raises_claim_not_found_when_claim_belongs_to_another_application():
    use_case, *_ = _build_use_case(
        claim=_claim(claim_id=1, laa_reference=1),
        application=_application(laa_reference=2),
    )

    with pytest.raises(ClaimNotFoundError):
        use_case.execute(
            RejectClaimCommand("2", 1, "reason"), caseworker_name="Caseworker"
        )


def test_creates_reject_decision_reason_updates_status_and_commits():
    application = _application()

    (
        use_case,
        create_decision_port,
        create_reason_port,
        update_status_port,
        create_history_event_port,
        _,
    ) = _build_use_case(claim=_claim(claim_id=5), application=application)

    use_case.execute(
        RejectClaimCommand("1", 5, "Rejected after review."),
        caseworker_name="Caseworker",
    )

    create_decision_port.create_claim_decision.assert_called_once_with(
        claim_id=5,
        decision_status=ClaimDecisionStatus.REJECT,
    )
    create_reason_port.create_decision_reason.assert_called_once_with(
        claim_decision_id=42,
        reason_code=ReasonCode.MANUAL_REJECTION,
        justification="Rejected after review.",
    )
    update_status_port.update_claim_status.assert_called_once_with(
        claim_id=5,
        status=ClaimStatus.REJECTED,
    )

    assert create_history_event_port.create_history_event.call_count == 2
    create_history_event_port.create_history_event.assert_has_calls(
        [
            call(
                event_reference=HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
                actor="Caseworker",
                actor_type=ActorType.CASEWORKER,
                laa_reference=1,
                event_data={
                    "claim_type": ClaimType.PAYMENT_ON_ACCOUNT,
                    "claim_decision": ClaimStatus.REJECTED,
                    "decision_justification": "Rejected after review.",
                },
            ),
            call(
                event_reference=HistoryEventReference.CLAIM_REJECTED_EMAIL,
                actor=ActorType.SYSTEM,
                actor_type=ActorType.SYSTEM,
                laa_reference="1",
                event_data={
                    "recipient": application.provider.email_address,
                    "channel": NotificationType.EMAIL,
                },
            ),
        ]
    )

    update_status_port.commit.assert_called_once()
    update_status_port.rollback.assert_not_called()


def test_history_event_not_created_when_update_claim_status_fails():
    (
        use_case,
        create_decision_port,
        create_reason_port,
        update_status_port,
        create_history_event_port,
        _,
    ) = _build_use_case(claim=_claim(claim_id=5), application=_application())
    update_status_port.update_claim_status.side_effect = RuntimeError(
        "Cannot update claim status"
    )

    with pytest.raises(RuntimeError):
        use_case.execute(
            RejectClaimCommand("1", 5, "Rejected after review."),
            caseworker_name="Caseworker",
        )

    create_decision_port.create_claim_decision.assert_called_once_with(
        claim_id=5,
        decision_status=ClaimDecisionStatus.REJECT,
    )
    create_reason_port.create_decision_reason.assert_called_once_with(
        claim_decision_id=42,
        reason_code=ReasonCode.MANUAL_REJECTION,
        justification="Rejected after review.",
    )
    update_status_port.update_claim_status.assert_called_once_with(
        claim_id=5,
        status=ClaimStatus.REJECTED,
    )
    create_history_event_port.create_history_event.assert_not_called()
    update_status_port.commit.assert_not_called()
    update_status_port.rollback.assert_called_once()


def test_reject_claim_not_committed_when_create_history_event_fails():
    (
        use_case,
        create_decision_port,
        create_reason_port,
        update_status_port,
        create_history_event_port,
        _,
    ) = _build_use_case(claim=_claim(claim_id=5), application=_application())
    create_history_event_port.create_history_event.side_effect = RuntimeError(
        "Cannot create history event"
    )

    with pytest.raises(RuntimeError):
        use_case.execute(
            RejectClaimCommand("1", 5, "Rejected after review."),
            caseworker_name="Caseworker",
        )

    create_decision_port.create_claim_decision.assert_called_once_with(
        claim_id=5,
        decision_status=ClaimDecisionStatus.REJECT,
    )
    create_reason_port.create_decision_reason.assert_called_once_with(
        claim_decision_id=42,
        reason_code=ReasonCode.MANUAL_REJECTION,
        justification="Rejected after review.",
    )
    update_status_port.update_claim_status.assert_called_once_with(
        claim_id=5,
        status=ClaimStatus.REJECTED,
    )
    create_history_event_port.create_history_event.assert_called_once_with(
        event_reference=HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
        actor="Caseworker",
        actor_type=ActorType.CASEWORKER,
        laa_reference=1,
        event_data={
            "claim_type": ClaimType.PAYMENT_ON_ACCOUNT,
            "claim_decision": ClaimStatus.REJECTED,
            "decision_justification": "Rejected after review.",
        },
    )
    update_status_port.commit.assert_not_called()
    update_status_port.rollback.assert_called_once()


def test_rolls_back_when_a_write_fails():
    (
        use_case,
        create_decision_port,
        _,
        update_status_port,
        __,
        _gov_notify_port,
    ) = _build_use_case(claim=_claim(claim_id=5), application=_application())
    create_decision_port.create_claim_decision.side_effect = RuntimeError(
        "Cannot create claim decision"
    )

    with pytest.raises(RuntimeError):
        use_case.execute(
            RejectClaimCommand("1", 5, "reason"), caseworker_name="Caseworker"
        )

    update_status_port.rollback.assert_called_once()
    update_status_port.commit.assert_not_called()


def test_sends_rejection_email_after_commit():
    (
        use_case,
        _,
        _,
        _,
        _,
        gov_notify_port,
    ) = _build_use_case(claim=_claim(claim_id=5), application=_application())

    use_case.execute(
        RejectClaimCommand("1", 5, "Rejected after review."),
        caseworker_name="Caseworker",
    )

    gov_notify_port.send_claim_rejected_decision_email.assert_called_once_with(
        claim=use_case.get_claim_by_id_port.get_claim_by_id.return_value,
        application=use_case.application_lookup_port.get_application_by_laa_reference.return_value,
        reject_reason="Rejected after review.",
        recipient_email="claimant-123@provider.co.uk",
    )


def test_rejection_email_failure_does_not_throw_error():
    (
        use_case,
        _,
        _,
        update_status_port,
        _,
        gov_notify_port,
    ) = _build_use_case(claim=_claim(claim_id=5), application=_application())
    gov_notify_port.send_claim_rejected_decision_email.side_effect = RuntimeError(
        "notify down"
    )

    use_case.execute(
        RejectClaimCommand("1", 5, "Rejected after review."),
        caseworker_name="Caseworker",
    )

    update_status_port.commit.assert_called_once()
    update_status_port.rollback.assert_not_called()
