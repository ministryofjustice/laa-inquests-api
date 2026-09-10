from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.contexts.user import set_entra_user_context
from app.domain.claim_error import ClaimErrorCode
from app.models.claim.enums import ClaimDecisionStatus, ClaimStatus, ClaimType, POAType
from app.models.claim.index import Claim, ClaimDecision, ClaimDecisionAmount
from app.models.history.enums import ActorType, HistoryEventReference
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.create_claim_decision_amount_port import (
    CreateClaimDecisionAmountPort,
)
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.get_claim_by_id_port import GetClaimByIdPort
from app.ports.claim.update_claim_status_port import UpdateClaimStatusPort
from app.ports.create_history_event_port import CreateHistoryEventPort
from app.use_cases.exceptions import (
    ApplicationNotFoundError,
    ClaimNotFoundError,
    InvalidClaimError,
)
from app.use_cases.pay_in_full_claim import PayInFullClaimCommand, PayInFullClaimUseCase


def _claim(claim_id: int = 1, application_id: int = 1) -> Claim:
    return Claim(
        claim_id=claim_id,
        application_id=application_id,
        claim_type_id=ClaimType.FINAL_BILL,
        status_id=ClaimStatus.SUBMITTED,
        submission_date=datetime.now(UTC),
        total_profit_cost_net=Decimal("1000.00"),
        total_profit_cost_gross=Decimal("1200.00"),
        total_profit_cost_vat_zero=Decimal("500.00"),
        poa_type_id=POAType.PROFIT_COST,
        claimant_id="claimant-123@provider.co.uk",
    )


def _application(application_id: int = 1):
    application = MagicMock()
    application.application_id = application_id
    application.laa_reference = f"INQ-{application_id:03d}-REF"
    application.provider.firm_code = "ABC123"
    return application


@pytest.fixture(autouse=True)
def entra_user_context() -> None:
    set_entra_user_context(None, "Caseworker")


def _build_use_case(claim=None, application=None):
    lookup_port = MagicMock(spec=ApplicationLookupPort)
    lookup_port.get_application_by_laa_reference.return_value = application

    get_claim_port = MagicMock(spec=GetClaimByIdPort)
    get_claim_port.get_claim_by_id.return_value = claim

    create_decision_port = MagicMock(spec=CreateClaimDecisionPort)
    create_decision_port.create_claim_decision.return_value = ClaimDecision(
        claim_decision_id=42,
        claim_id=claim.claim_id if claim is not None else 1,
        decision=ClaimDecisionStatus.PAY_IN_FULL,
    )

    create_decision_amount_port = MagicMock(spec=CreateClaimDecisionAmountPort)
    create_decision_amount_port.create_claim_decision_amount.return_value = (
        ClaimDecisionAmount(
            claim_decision_amount_id=7,
            claim_decision_id=42,
        )
    )

    update_status_port = MagicMock(spec=UpdateClaimStatusPort)
    create_history_event_port = MagicMock(spec=CreateHistoryEventPort)

    use_case = PayInFullClaimUseCase(
        application_lookup_port=lookup_port,
        get_claim_by_id_port=get_claim_port,
        create_claim_decision_port=create_decision_port,
        create_claim_decision_amount_port=create_decision_amount_port,
        update_claim_status_port=update_status_port,
        create_history_event_port=create_history_event_port,
    )
    return (
        use_case,
        create_decision_port,
        create_decision_amount_port,
        update_status_port,
        create_history_event_port,
    )


def test_raises_application_not_found_when_application_missing():
    use_case, *_ = _build_use_case(claim=_claim(), application=None)

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute(PayInFullClaimCommand("999999", 1))


def test_raises_claim_not_found_when_claim_missing():
    use_case, *_ = _build_use_case(claim=None, application=_application())

    with pytest.raises(ClaimNotFoundError):
        use_case.execute(PayInFullClaimCommand("1", 999999))


def test_raises_claim_not_found_when_claim_belongs_to_another_application():
    use_case, *_ = _build_use_case(
        claim=_claim(claim_id=1, application_id=1),
        application=_application(application_id=2),
    )

    with pytest.raises(ClaimNotFoundError):
        use_case.execute(PayInFullClaimCommand("2", 1))


def test_creates_pay_in_full_decision_amount_updates_status_and_commits():
    application = _application()

    (
        use_case,
        create_decision_port,
        create_decision_amount_port,
        update_status_port,
        create_history_event_port,
    ) = _build_use_case(claim=_claim(claim_id=5), application=application)

    use_case.execute(
        PayInFullClaimCommand(
            laa_reference="1",
            claim_id=5,
            profit_cost_net=Decimal("1000.00"),
            profit_cost_gross=Decimal("1200.00"),
            profit_cost_vat_zero=None,
            disbursement_net=Decimal("100.00"),
            disbursement_gross=Decimal("120.00"),
            disbursement_vat_zero=Decimal("50.00"),
        )
    )

    create_decision_port.create_claim_decision.assert_called_once_with(
        claim_id=5,
        decision_status=ClaimDecisionStatus.PAY_IN_FULL,
    )
    create_decision_amount_port.create_claim_decision_amount.assert_called_once_with(
        claim_decision_id=42,
        profit_cost_net=Decimal("1000.00"),
        profit_cost_gross=Decimal("1200.00"),
        profit_cost_vat_zero=None,
        disbursement_net=Decimal("100.00"),
        disbursement_gross=Decimal("120.00"),
        disbursement_vat_zero=Decimal("50.00"),
    )
    update_status_port.update_claim_status.assert_called_once_with(
        claim_id=5,
        status=ClaimStatus.PAY_IN_FULL,
    )

    create_history_event_port.create_history_event.assert_called_once_with(
        event_reference=HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
        actor="Caseworker",
        actor_type=ActorType.CASEWORKER,
        application_id=1,
        event_data={
            "claim_type": ClaimType.FINAL_BILL,
            "claim_decision": ClaimStatus.PAY_IN_FULL,
            "profit_cost_net": "1000.00",
            "profit_cost_gross": "1200.00",
            "profit_cost_vat_zero": None,
            "disbursement_net": "100.00",
            "disbursement_gross": "120.00",
            "disbursement_vat_zero": "50.00",
        },
    )

    update_status_port.commit.assert_called_once()
    update_status_port.rollback.assert_not_called()


def test_history_event_not_created_when_update_claim_status_fails():
    (
        use_case,
        create_decision_port,
        create_decision_amount_port,
        update_status_port,
        create_history_event_port,
    ) = _build_use_case(claim=_claim(claim_id=5), application=_application())
    update_status_port.update_claim_status.side_effect = RuntimeError(
        "Cannot update claim status"
    )

    with pytest.raises(RuntimeError):
        use_case.execute(
            PayInFullClaimCommand(
                "1",
                5,
                profit_cost_net=Decimal("1000.00"),
                profit_cost_gross=Decimal("1200.00"),
            )
        )

    create_decision_port.create_claim_decision.assert_called_once_with(
        claim_id=5,
        decision_status=ClaimDecisionStatus.PAY_IN_FULL,
    )
    create_decision_amount_port.create_claim_decision_amount.assert_called_once()
    update_status_port.update_claim_status.assert_called_once_with(
        claim_id=5,
        status=ClaimStatus.PAY_IN_FULL,
    )
    create_history_event_port.create_history_event.assert_not_called()
    update_status_port.commit.assert_not_called()
    update_status_port.rollback.assert_called_once()


def test_pay_in_full_claim_not_committed_when_create_history_event_fails():
    (
        use_case,
        _,
        _,
        update_status_port,
        create_history_event_port,
    ) = _build_use_case(claim=_claim(claim_id=5), application=_application())
    create_history_event_port.create_history_event.side_effect = RuntimeError(
        "Cannot create history event"
    )

    with pytest.raises(RuntimeError):
        use_case.execute(
            PayInFullClaimCommand(
                "1",
                5,
                profit_cost_net=Decimal("1000.00"),
                profit_cost_gross=Decimal("1200.00"),
            )
        )

    update_status_port.commit.assert_not_called()
    update_status_port.rollback.assert_called_once()


def test_raises_invalid_claim_error_when_profit_cost_totals_invalid():
    (
        use_case,
        create_decision_port,
        _,
        update_status_port,
        _,
    ) = _build_use_case(claim=_claim(claim_id=5), application=_application())

    with pytest.raises(InvalidClaimError) as exc:
        use_case.execute(
            PayInFullClaimCommand(
                "1",
                5,
                profit_cost_net=Decimal("1000.00"),
            )
        )

    assert exc.value.code == ClaimErrorCode.MISSING_GROSS_TOTAL_WHEN_NET_ENTERED
    create_decision_port.create_claim_decision.assert_not_called()
    update_status_port.commit.assert_not_called()
