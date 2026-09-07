"""E2E tests for the deferred POA auto-approve grant email batch job."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from sqlmodel import select

from app.adapters.claim_repository_adapter import ClaimRepositoryAdapter
from app.adapters.history_event_repository_adapter import HistoryEventRepositoryAdapter
from app.models.application.enums import MeritsDecision
from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus
from app.models.claim.index import Claim
from app.models.history.enums import HistoryEventReference
from app.models.history.index import HistoryEvent
from app.use_cases.send_auto_approved_poa_claim_emails import (
    SendAutoApprovedPoaClaimEmailsUseCase,
)
from tests.e2e.factories import create_application_in_db

FIRM_NAME = "Test Firm Name"
BATCH_RUN_TIME = datetime(2026, 9, 7, 9, 0, tzinfo=UTC)
FIRM_CODE = "0A123B"


def _make_request_body(overrides=None):
    """Build an eligible payment-on-account claim request body."""
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


def _build_batch_use_case(session):
    """Wire the batch use case with real repositories and mocked outbound ports."""
    claim_repository = ClaimRepositoryAdapter(session=session)
    history_events = HistoryEventRepositoryAdapter(session=session)

    provider_details_port = MagicMock()
    provider_details_port.get_firm_name.return_value = FIRM_NAME

    gov_notify_port = MagicMock()

    use_case = SendAutoApprovedPoaClaimEmailsUseCase(
        list_auto_approved_poa_claims_port=claim_repository,
        get_application_history_port=history_events,
        create_history_event_port=history_events,
        provider_details_port=provider_details_port,
        gov_notify_port=gov_notify_port,
    )
    return use_case, gov_notify_port


def _auto_approve_poa_claim(
    session, client, auth_token, laa_reference, submission_date
):
    """Auto-approve a POA claim via the API, then pin its submission date."""
    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )
    assert response.status_code == 201

    claim = session.get(Claim, response.json()["claimId"])
    assert claim is not None
    assert claim.status_id == ClaimStatus.PAY_IN_FULL

    claim.submission_date = submission_date
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


def _email_sent_events(session, claim_id):
    """Return the CLAIM_APPROVED_EMAIL events recorded for a claim."""
    events = session.exec(
        select(HistoryEvent).where(
            HistoryEvent.event_reference == HistoryEventReference.CLAIM_APPROVED_EMAIL
        )
    ).all()
    return [
        event
        for event in events
        if (event.event_data or {}).get("claim_reference") == claim_id
    ]


def test_single_auto_approved_poa_claim_is_emailed_when_batch_runs(
    session, client, auth_token
):
    """A single POA claim auto-approved within the window is emailed at batch time."""
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _auto_approve_poa_claim(
        session,
        client,
        auth_token,
        laa_reference,
        submission_date=BATCH_RUN_TIME - timedelta(hours=24),
    )

    use_case, gov_notify_port = _build_batch_use_case(session)
    use_case.execute(now=BATCH_RUN_TIME)

    gov_notify_port.send_claim_granted_decision_email.assert_called_once()
    call_kwargs = gov_notify_port.send_claim_granted_decision_email.call_args.kwargs
    assert call_kwargs["claim"].claim_id == claim.claim_id
    assert call_kwargs["recipient_email"] == "test@example.com"
    assert call_kwargs["firm_name"] == FIRM_NAME

    assert len(_email_sent_events(session, claim.claim_id)) == 1


def test_multiple_auto_approved_poa_claims_are_emailed_in_a_single_batch_run(
    session, client, auth_token
):
    """Multiple POA claims within the same window are each emailed once per batch run."""
    submission_date = BATCH_RUN_TIME - timedelta(hours=24)

    first_laa_reference = session.exec(select(Application)).first().laa_reference
    first_claim = _auto_approve_poa_claim(
        session, client, auth_token, first_laa_reference, submission_date
    )

    second_application = create_application_in_db(
        session,
        provider_overrides={
            "firm_code": FIRM_CODE,
            "office_id": "0U777L",
            "email_address": "second@example.com",
        },
        proceeding_overrides={"merits_decision": MeritsDecision.GRANTED},
    )
    second_claim = _auto_approve_poa_claim(
        session,
        client,
        auth_token,
        second_application.laa_reference,
        submission_date,
    )

    use_case, gov_notify_port = _build_batch_use_case(session)
    use_case.execute(now=BATCH_RUN_TIME)

    assert gov_notify_port.send_claim_granted_decision_email.call_count == 2
    recipients = {
        call.kwargs["recipient_email"]
        for call in gov_notify_port.send_claim_granted_decision_email.call_args_list
    }
    assert recipients == {"test@example.com", "second@example.com"}

    assert len(_email_sent_events(session, first_claim.claim_id)) == 1
    assert len(_email_sent_events(session, second_claim.claim_id)) == 1


def test_claim_auto_approved_outside_the_window_is_not_emailed(
    session, client, auth_token
):
    """A claim auto-approved before the 48-hour window is not emailed by the batch."""
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _auto_approve_poa_claim(
        session,
        client,
        auth_token,
        laa_reference,
        submission_date=BATCH_RUN_TIME - timedelta(hours=49),
    )

    use_case, gov_notify_port = _build_batch_use_case(session)
    use_case.execute(now=BATCH_RUN_TIME)

    gov_notify_port.send_claim_granted_decision_email.assert_not_called()
    assert _email_sent_events(session, claim.claim_id) == []
