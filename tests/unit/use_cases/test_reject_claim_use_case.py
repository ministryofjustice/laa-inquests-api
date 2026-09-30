from datetime import UTC, datetime
from unittest.mock import MagicMock, call

import pytest

from app.contexts.user import set_entra_user_context
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    ReasonCode,
)
from app.models.claim.index import Claim
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.notifications.enums import NotificationType
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.create_decision_reason_port import CreateDecisionReasonPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.update_claim_status_port import UpdateClaimStatusPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ApplicationNotFoundError, ClaimNotFoundError
from app.use_cases.reject_claim import RejectClaimCommand, RejectClaimUseCase
from tests.factories.builders import (
    build_application,
    build_claim_decision,
    build_poa_claim,
)


def _claim(application: Application) -> Claim:
    return build_poa_claim(
        application_id=application.application_id,
        claim_reference="INQC-0000-0001",
        submission_date=datetime.now(UTC),
        claimant_id="claimant-123@provider.co.uk",
    )


@pytest.fixture(autouse=True)
def entra_user_context() -> None:
    set_entra_user_context(None, "Caseworker")


def _build_use_case(claim=None, application=None):
    lookup_port = MagicMock(spec=ApplicationLookupPort)
    lookup_port.get_application_by_laa_reference.return_value = application

    get_claim_port = MagicMock(spec=GetClaimByIdPort)
    get_claim_port.get_claim_by_reference.return_value = claim

    create_decision_port = MagicMock(spec=CreateClaimDecisionPort)
    create_decision_port.create_claim_decision.return_value = build_claim_decision(
        claim_decision_id=42,
        claim_id=claim.claim_id if claim is not None else None,
        decision=ClaimDecisionStatus.REJECT,
    )

    create_reason_port = MagicMock(spec=CreateDecisionReasonPort)
    update_status_port = MagicMock(spec=UpdateClaimStatusPort)

    create_history_event_port = MagicMock(spec=CreateHistoryEventPort)
    provider_details_port = MagicMock(spec=ProviderDetailsPort)
    provider_details_port.get_firm_name.return_value = "Test Firm"
    gov_notify_port = MagicMock(spec=GovNotifyPort)

    use_case = RejectClaimUseCase(
        application_lookup_port=lookup_port,
        get_claim_by_id_port=get_claim_port,
        create_claim_decision_port=create_decision_port,
        create_decision_reason_port=create_reason_port,
        update_claim_status_port=update_status_port,
        create_history_event_port=create_history_event_port,
        provider_details_port=provider_details_port,
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
    use_case, *_ = _build_use_case(claim=_claim(build_application()), application=None)

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute(RejectClaimCommand("999999", "INQC-0000-0001", "reason"))


def test_raises_claim_not_found_when_claim_missing():
    use_case, *_ = _build_use_case(claim=None, application=build_application())

    with pytest.raises(ClaimNotFoundError):
        use_case.execute(RejectClaimCommand("1", "INQC-9999-9999", "reason"))


def test_raises_claim_not_found_when_claim_belongs_to_another_application():
    use_case, *_ = _build_use_case(
        claim=_claim(build_application()),
        application=build_application(),
    )

    with pytest.raises(ClaimNotFoundError):
        use_case.execute(RejectClaimCommand("2", "INQC-0000-0001", "reason"))


def test_creates_reject_decision_reason_updates_status_and_commits():
    application = build_application()
    claim = _claim(application)

    (
        use_case,
        create_decision_port,
        create_reason_port,
        update_status_port,
        create_history_event_port,
        _,
    ) = _build_use_case(claim=claim, application=application)

    use_case.execute(
        RejectClaimCommand("1", claim.claim_reference, "Rejected after review.")
    )

    create_decision_port.create_claim_decision.assert_called_once_with(
        claim_id=claim.claim_id,
        decision_status=ClaimDecisionStatus.REJECT,
    )
    create_reason_port.create_decision_reason.assert_called_once_with(
        claim_decision_id=42,
        reason_code=ReasonCode.MANUAL_REJECTION,
        justification="Rejected after review.",
    )
    update_status_port.update_claim_status.assert_called_once_with(
        claim_id=claim.claim_id,
        status=ClaimStatus.REJECTED,
    )

    assert create_history_event_port.create_history_event.call_count == 2
    create_history_event_port.create_history_event.assert_has_calls(
        [
            call(
                event_reference=HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
                actor="Caseworker",
                actor_type=ActorType.CASEWORKER,
                application_id=application.application_id,
                event_data={
                    "claim_type": ClaimType.PAYMENT_ON_ACCOUNT,
                    "claim_reference": "INQC-0000-0001",
                    "claim_decision": ClaimStatus.REJECTED,
                    "decision_justification": "Rejected after review.",
                },
            ),
            call(
                event_reference=HistoryEventReference.CLAIM_REJECTED_EMAIL,
                actor=ActorType.SYSTEM,
                actor_type=ActorType.SYSTEM,
                application_id=application.application_id,
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
    application = build_application()
    claim = _claim(application)
    (
        use_case,
        create_decision_port,
        create_reason_port,
        update_status_port,
        create_history_event_port,
        _,
    ) = _build_use_case(claim=claim, application=application)
    update_status_port.update_claim_status.side_effect = RuntimeError(
        "Cannot update claim status"
    )

    with pytest.raises(RuntimeError):
        use_case.execute(
            RejectClaimCommand("1", claim.claim_reference, "Rejected after review.")
        )

    create_decision_port.create_claim_decision.assert_called_once_with(
        claim_id=claim.claim_id,
        decision_status=ClaimDecisionStatus.REJECT,
    )
    create_reason_port.create_decision_reason.assert_called_once_with(
        claim_decision_id=42,
        reason_code=ReasonCode.MANUAL_REJECTION,
        justification="Rejected after review.",
    )
    update_status_port.update_claim_status.assert_called_once_with(
        claim_id=claim.claim_id,
        status=ClaimStatus.REJECTED,
    )
    create_history_event_port.create_history_event.assert_not_called()
    update_status_port.commit.assert_not_called()
    update_status_port.rollback.assert_called_once()


def test_reject_claim_not_committed_when_create_history_event_fails():
    application = build_application()
    claim = _claim(application)
    (
        use_case,
        create_decision_port,
        create_reason_port,
        update_status_port,
        create_history_event_port,
        _,
    ) = _build_use_case(claim=claim, application=application)
    create_history_event_port.create_history_event.side_effect = RuntimeError(
        "Cannot create history event"
    )

    with pytest.raises(RuntimeError):
        use_case.execute(
            RejectClaimCommand("1", claim.claim_reference, "Rejected after review.")
        )

    create_decision_port.create_claim_decision.assert_called_once_with(
        claim_id=claim.claim_id,
        decision_status=ClaimDecisionStatus.REJECT,
    )
    create_reason_port.create_decision_reason.assert_called_once_with(
        claim_decision_id=42,
        reason_code=ReasonCode.MANUAL_REJECTION,
        justification="Rejected after review.",
    )
    update_status_port.update_claim_status.assert_called_once_with(
        claim_id=claim.claim_id,
        status=ClaimStatus.REJECTED,
    )
    create_history_event_port.create_history_event.assert_called_once_with(
        event_reference=HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
        actor="Caseworker",
        actor_type=ActorType.CASEWORKER,
        application_id=application.application_id,
        event_data={
            "claim_type": ClaimType.PAYMENT_ON_ACCOUNT,
            "claim_reference": "INQC-0000-0001",
            "claim_decision": ClaimStatus.REJECTED,
            "decision_justification": "Rejected after review.",
        },
    )
    update_status_port.commit.assert_not_called()
    update_status_port.rollback.assert_called_once()


def test_rolls_back_when_a_write_fails():
    application = build_application()
    claim = _claim(application)
    (
        use_case,
        create_decision_port,
        _,
        update_status_port,
        __,
        _gov_notify_port,
    ) = _build_use_case(claim=claim, application=application)
    create_decision_port.create_claim_decision.side_effect = RuntimeError(
        "Cannot create claim decision"
    )

    with pytest.raises(RuntimeError):
        use_case.execute(RejectClaimCommand("1", claim.claim_reference, "reason"))

    update_status_port.rollback.assert_called_once()
    update_status_port.commit.assert_not_called()


def test_sends_rejection_email_after_commit():
    application = build_application()
    claim = _claim(application)
    (
        use_case,
        _,
        _,
        _,
        _,
        gov_notify_port,
    ) = _build_use_case(claim=claim, application=application)

    use_case.execute(
        RejectClaimCommand("1", claim.claim_reference, "Rejected after review.")
    )

    gov_notify_port.send_claim_rejected_decision_email.assert_called_once_with(
        claim=use_case.get_claim_by_id_port.get_claim_by_reference.return_value,
        application=use_case.application_lookup_port.get_application_by_laa_reference.return_value,
        reject_reason="Rejected after review.",
        recipient_email="claimant-123@provider.co.uk",
        firm_name="Test Firm",
    )


def test_rejection_email_failure_does_not_throw_error():
    application = build_application()
    claim = _claim(application)
    (
        use_case,
        _,
        _,
        update_status_port,
        _,
        gov_notify_port,
    ) = _build_use_case(claim=claim, application=application)
    gov_notify_port.send_claim_rejected_decision_email.side_effect = RuntimeError(
        "notify down"
    )

    use_case.execute(
        RejectClaimCommand("1", claim.claim_reference, "Rejected after review.")
    )

    update_status_port.commit.assert_called_once()
    update_status_port.rollback.assert_not_called()
