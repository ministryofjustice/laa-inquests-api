from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.models.claim.index import Claim
from app.models.history.enums import HistoryEventReference
from app.ports.claim.list_auto_approved_poa_claims_port import (
    ListAutoApprovedPoaClaimsPort,
)
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.ports.get_application_history_port import GetApplicationHistoryPort
from app.ports.gov_notify_port import GovNotifyPort
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.send_auto_approved_poa_claim_emails import (
    SendAutoApprovedPoaClaimEmailsUseCase,
)


def _event(reference: HistoryEventReference, claim_id: int) -> SimpleNamespace:
    return SimpleNamespace(
        event_reference=reference, event_data={"claim_reference": claim_id}
    )


def _claim(claim_id: int = 7) -> MagicMock:
    claim = MagicMock(spec=Claim)
    claim.claim_id = claim_id
    application = SimpleNamespace(
        application_id=12345,
        provider=SimpleNamespace(
            firm_code="ABC123", email_address="provider@example.com"
        ),
    )
    claim.application = application
    return claim


@pytest.fixture
def list_port() -> MagicMock:
    return MagicMock(spec=ListAutoApprovedPoaClaimsPort)


@pytest.fixture
def history_port() -> MagicMock:
    return MagicMock(spec=GetApplicationHistoryPort)


@pytest.fixture
def create_history_port() -> MagicMock:
    return MagicMock(spec=CreateHistoryEventPort)


@pytest.fixture
def provider_details_port() -> MagicMock:
    port = MagicMock(spec=ProviderDetailsPort)
    port.get_firm_name.return_value = "Test Solicitors"
    return port


@pytest.fixture
def gov_notify_port() -> MagicMock:
    return MagicMock(spec=GovNotifyPort)


@pytest.fixture
def use_case(
    list_port, history_port, create_history_port, provider_details_port, gov_notify_port
) -> SendAutoApprovedPoaClaimEmailsUseCase:
    return SendAutoApprovedPoaClaimEmailsUseCase(
        list_auto_approved_poa_claims_port=list_port,
        get_application_history_port=history_port,
        create_history_event_port=create_history_port,
        provider_details_port=provider_details_port,
        gov_notify_port=gov_notify_port,
    )


def test_sends_grant_email_for_auto_approved_claim(
    use_case, list_port, history_port, create_history_port, gov_notify_port
):
    claim = _claim()
    list_port.list_auto_approved_poa_claims.return_value = [claim]
    history_port.get_application_history.return_value = [
        _event(HistoryEventReference.POA_AUTO_APPROVED, claim.claim_id)
    ]

    use_case.execute()

    gov_notify_port.send_claim_granted_decision_email.assert_called_once_with(
        claim=claim,
        application=claim.application,
        recipient_email="provider@example.com",
        firm_name="Test Solicitors",
    )
    create_history_port.create_history_event.assert_called_once()
    assert (
        create_history_port.create_history_event.call_args.kwargs["event_reference"]
        == HistoryEventReference.CLAIM_APPROVED_EMAIL
    )
    create_history_port.commit.assert_called_once()


def test_skips_claim_without_auto_approved_event(
    use_case, list_port, history_port, gov_notify_port, create_history_port
):
    claim = _claim()
    list_port.list_auto_approved_poa_claims.return_value = [claim]
    history_port.get_application_history.return_value = []

    use_case.execute()

    gov_notify_port.send_claim_granted_decision_email.assert_not_called()
    create_history_port.create_history_event.assert_not_called()


def test_skips_claim_when_email_already_sent(
    use_case, list_port, history_port, gov_notify_port, create_history_port
):
    claim = _claim()
    list_port.list_auto_approved_poa_claims.return_value = [claim]
    history_port.get_application_history.return_value = [
        _event(HistoryEventReference.POA_AUTO_APPROVED, claim.claim_id),
        _event(HistoryEventReference.CLAIM_APPROVED_EMAIL, claim.claim_id),
    ]

    use_case.execute()

    gov_notify_port.send_claim_granted_decision_email.assert_not_called()
    create_history_port.create_history_event.assert_not_called()


def test_one_claim_failure_does_not_block_others(
    use_case, list_port, history_port, gov_notify_port, create_history_port
):
    failing = _claim(claim_id=1)
    succeeding = _claim(claim_id=2)
    list_port.list_auto_approved_poa_claims.return_value = [failing, succeeding]
    history_port.get_application_history.side_effect = lambda _app_id: [
        _event(HistoryEventReference.POA_AUTO_APPROVED, 1),
        _event(HistoryEventReference.POA_AUTO_APPROVED, 2),
    ]
    gov_notify_port.send_claim_granted_decision_email.side_effect = [
        Exception("boom"),
        None,
    ]

    use_case.execute()

    assert gov_notify_port.send_claim_granted_decision_email.call_count == 2
    create_history_port.commit.assert_called_once()


def test_queries_previous_48_hour_window(use_case, list_port):
    list_port.list_auto_approved_poa_claims.return_value = []

    use_case.execute(now=datetime(2026, 9, 7, 9, 0, tzinfo=UTC))

    list_port.list_auto_approved_poa_claims.assert_called_once_with(
        datetime(2026, 9, 5, 9, 0, tzinfo=UTC),
        datetime(2026, 9, 7, 9, 0, tzinfo=UTC),
    )
