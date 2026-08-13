import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.domain.claim_error import ClaimErrorCode
from app.models.application.enums import MeritsDecision
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    POAType,
    ReasonCode,
)
from app.models.claim.index import Claim, ClaimDecision
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.claim.create_claim_decision_port import CreateClaimDecisionPort
from app.ports.claim.create_claim_port import CreateClaimPort
from app.ports.claim.create_decision_reason_port import CreateDecisionReasonPort
from app.ports.claim.get_claim_decision_port import GetClaimDecisionPort
from app.ports.claim.get_claims_for_application_port import GetClaimsForApplicationPort
from app.ports.claim.update_claim_status_port import (
    UpdateClaimStatusPort,
)
from app.use_cases.create_claim import CreateClaimCommand, CreateClaimUseCase
from app.use_cases.exceptions import ApplicationNotFoundError, InvalidClaimError

_UNSET = object()


def _make_command(overrides=None) -> CreateClaimCommand:
    payload = {
        "laa_reference": "12345",
        "firm_code": "0A123B",
        "claim_type": ClaimType.PAYMENT_ON_ACCOUNT,
        "poa_type": POAType.PROFIT_COST,
        "net": Decimal("1000.00"),
        "gross": Decimal("1200.00"),
        "vat_zero_total": None,
        "claimant_id": "claimant-123@provider.co.uk",
        "claim_evidence_ids": [uuid.uuid4()],
    }
    if overrides is not None:
        payload.update(overrides)
    return CreateClaimCommand(**payload)


def _make_claim() -> Claim:
    return Claim(
        claim_id=1,
        laa_reference=12345,
        claim_type_id="PAYMENT_ON_ACCOUNT",
        total_profit_cost_net=1000,
        total_profit_cost_gross=1200,
        poa_type_id="PROFIT_COST",
    )


def _make_matching_application(firm_code: str = "0A123B") -> Application:
    application = MagicMock(spec=Application)
    proceeding = MagicMock()
    proceeding.substantive_cost_limitation = 1000
    proceeding.certificate_start_date = None
    application.proceeding = proceeding
    application.provider.firm_code = firm_code
    application.provider.email_address = "provider@example.com"
    application.overall_decision = MeritsDecision.GRANTED
    return application


def _make_application_lookup_port(application: Application | None = _UNSET):
    if application is _UNSET:
        application = _make_matching_application()
    if application is not None:
        application.provider.firm_code = "0A123B"
    port = MagicMock(spec=ApplicationLookupPort)
    port.get_application_by_laa_reference.return_value = application
    return port


def _make_get_claims_port(claims: list[Claim] | None = None):
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_laa_reference.return_value = claims or []
    return port


def _make_create_claim_decision_port(claim_decision_id: int = 10):
    port = MagicMock(spec=CreateClaimDecisionPort)
    port.create_claim_decision.return_value = ClaimDecision(
        claim_decision_id=claim_decision_id,
        claim_id=1,
        decision=ClaimDecisionStatus.REJECT,
    )
    return port


def _make_create_decision_reason_port():
    return MagicMock(spec=CreateDecisionReasonPort)


def _make_update_claim_status_port():
    return MagicMock(spec=UpdateClaimStatusPort)


def _make_get_claim_decision_port(decisions_by_claim_id=None):
    port = MagicMock(spec=GetClaimDecisionPort)
    mapping = decisions_by_claim_id or {}
    port.get_claim_decision_by_claim_id.side_effect = lambda claim_id: mapping.get(
        claim_id
    )
    return port


def test_execute_raises_invalid_claim_error_when_no_evidence_ids_provided():
    command = _make_command({"claim_evidence_ids": []})
    use_case = CreateClaimUseCase(
        create_claim_port=MagicMock(spec=CreateClaimPort),
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute(command)
    assert exc_info.value.code == ClaimErrorCode.MISSING_CLAIM_EVIDENCE


def test_execute_raises_application_not_found_when_firm_code_does_not_match():
    command = _make_command()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    application_lookup_port = MagicMock(spec=ApplicationLookupPort)
    application_lookup_port.get_application_by_laa_reference.return_value = (
        _make_matching_application(firm_code="ZZ999Z")
    )
    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=application_lookup_port,
        get_claims_for_application_port=_make_get_claims_port(),
    )

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute(command)
    create_claim_port.create_claim.assert_not_called()


def test_execute_raises_application_not_found_when_application_missing():
    command = _make_command()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(None),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute(command)
    create_claim_port.create_claim.assert_not_called()


def test_execute_raises_invalid_claim_error_when_application_not_granted():
    command = _make_command()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    application = _make_matching_application()
    application.overall_decision = MeritsDecision.PENDING

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(application),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute(command)
    assert exc_info.value.code == ClaimErrorCode.APPLICATION_NOT_GRANTED
    create_claim_port.create_claim.assert_not_called()


def test_execute_creates_claim_and_commits():
    command = _make_command()
    claim = _make_claim()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim

    application_lookup_port = _make_application_lookup_port()

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=application_lookup_port,
        get_claims_for_application_port=_make_get_claims_port(),
    )
    use_case.execute(command)

    create_claim_port.create_claim.assert_called_once()
    _, kwargs = create_claim_port.create_claim.call_args
    assert kwargs["laa_reference"] == command.laa_reference
    assert kwargs["claimant_id"] == command.claimant_id
    assert kwargs["claim"].claim_type == command.claim_type
    create_claim_port.commit.assert_called_once()


def test_execute_links_claim_evidence_to_created_claim():
    command = _make_command()
    claim = _make_claim()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )
    use_case.execute(command)

    create_claim_port.link_evidence_to_claim.assert_called_once_with(
        claim.claim_id, command.claim_evidence_ids
    )


def test_execute_returns_created_claim():
    command = _make_command()
    claim = _make_claim()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )
    result = use_case.execute(command)

    assert result.claim is claim


def test_execute_sends_claim_submission_email_when_application_exists():
    command = _make_command()
    claim = _make_claim()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim
    application = MagicMock(spec=Application)
    proceeding = MagicMock()
    proceeding.substantive_cost_limitation = 1000
    proceeding.certificate_start_date = None
    application.proceeding = proceeding
    application.provider.firm_code = "0A123B"
    application.provider.email_address = "provider@example.com"
    application.overall_decision = MeritsDecision.GRANTED
    gov_notify_port = MagicMock()

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(application),
        get_claims_for_application_port=_make_get_claims_port(),
        gov_notify_port=gov_notify_port,
    )

    use_case.execute(command)

    gov_notify_port.send_claim_submit_confirmation_email.assert_called_once_with(
        claim=claim,
        application=application,
        recipient_email="provider@example.com",
    )


def test_execute_raises_invalid_claim_error_when_payment_on_account_without_poa_type():
    command = _make_command({"poa_type": None})
    use_case = CreateClaimUseCase(
        create_claim_port=MagicMock(spec=CreateClaimPort),
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute(command)
    assert exc_info.value.code == ClaimErrorCode.MISSING_POA_TYPE_FOR_PAYMENT_ON_ACCOUNT


def test_execute_raises_invalid_claim_error_when_non_payment_on_account_with_poa_type():
    command = _make_command(
        {
            "claim_type": ClaimType.FINAL_BILL,
            "poa_type": POAType.PROFIT_COST,
        }
    )
    use_case = CreateClaimUseCase(
        create_claim_port=MagicMock(spec=CreateClaimPort),
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute(command)
    assert (
        exc_info.value.code
        == ClaimErrorCode.POA_TYPE_NOT_ALLOWED_FOR_NON_PAYMENT_ON_ACCOUNT
    )


def test_execute_raises_invalid_claim_error_when_profit_cost_has_no_costs():
    command = _make_command({"net": None, "gross": None, "vat_zero_total": None})
    use_case = CreateClaimUseCase(
        create_claim_port=MagicMock(spec=CreateClaimPort),
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute(command)
    assert exc_info.value.code == ClaimErrorCode.MISSING_TOTAL_CLAIM_COST


def test_execute_raises_invalid_claim_error_when_net_higher_than_gross():
    command = _make_command({"net": Decimal("1200.00"), "gross": Decimal("1000.00")})
    use_case = CreateClaimUseCase(
        create_claim_port=MagicMock(spec=CreateClaimPort),
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute(command)
    assert exc_info.value.code == ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL


def test_execute_raises_invalid_claim_error_when_non_profit_cost_net_higher_than_gross():
    command = _make_command(
        {
            "poa_type": POAType.EXPERT_COST,
            "net": Decimal("120.00"),
            "gross": Decimal("100.00"),
        }
    )
    use_case = CreateClaimUseCase(
        create_claim_port=MagicMock(spec=CreateClaimPort),
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute(command)

    assert exc_info.value.code == ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL


def test_execute_raises_invalid_claim_error_when_non_profit_cost_has_no_costs():
    command = _make_command(
        {
            "poa_type": POAType.EXPERT_COST,
            "net": None,
            "gross": None,
            "vat_zero_total": None,
        }
    )
    use_case = CreateClaimUseCase(
        create_claim_port=MagicMock(spec=CreateClaimPort),
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute(command)

    assert exc_info.value.code == ClaimErrorCode.MISSING_NON_PROFIT_COST_TOTAL


def test_execute_raises_invalid_claim_error_when_mixing_vat_rates():
    command = _make_command({"vat_zero_total": Decimal("500.00")})
    use_case = CreateClaimUseCase(
        create_claim_port=MagicMock(spec=CreateClaimPort),
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute(command)
    assert exc_info.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_execute_does_not_raise_for_non_profit_cost_without_costs():
    command = _make_command(
        {
            "claim_type": ClaimType.FINAL_BILL,
            "poa_type": None,
            "net": None,
            "gross": None,
            "vat_zero_total": None,
        }
    )
    port = MagicMock(spec=CreateClaimPort)
    port.create_claim.return_value = _make_claim()
    use_case = CreateClaimUseCase(
        create_claim_port=port,
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    use_case.execute(command)  # should not raise


def test_execute_accepts_non_profit_cost_with_vat_zero_only():
    command = _make_command(
        {
            "poa_type": POAType.EXPERT_COST,
            "net": None,
            "gross": None,
            "vat_zero_total": Decimal("150.00"),
        }
    )
    port = MagicMock(spec=CreateClaimPort)
    port.create_claim.return_value = _make_claim()
    use_case = CreateClaimUseCase(
        create_claim_port=port,
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    use_case.execute(command)


def test_execute_uses_validated_domain_values_when_calling_port():
    command = _make_command(
        {
            "poa_type": POAType.EXPERT_COST,
            "net": None,
            "gross": None,
            "vat_zero_total": Decimal("150.00"),
        }
    )
    port = MagicMock(spec=CreateClaimPort)
    port.create_claim.return_value = _make_claim()
    use_case = CreateClaimUseCase(
        create_claim_port=port,
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=_make_get_claims_port(),
    )

    use_case.execute(command)

    _, kwargs = port.create_claim.call_args
    assert kwargs["claim"].net == Decimal("0.00")
    assert kwargs["claim"].gross == Decimal("0.00")
    assert kwargs["claim"].vat_zero_total == Decimal("150.00")


def test_execute_fetches_application_before_creating_claim():
    command = _make_command()
    claim = _make_claim()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim

    application_lookup_port = _make_application_lookup_port()

    marker = {"application_fetched": False}

    def mark_application_fetched(_laa_reference: str) -> Application:
        marker["application_fetched"] = True
        return _make_matching_application()

    def assert_application_fetched_before_create(*_args, **_kwargs) -> MagicMock:
        assert marker["application_fetched"] is True
        return claim

    application_lookup_port.get_application_by_laa_reference.side_effect = (
        mark_application_fetched
    )
    create_claim_port.create_claim.side_effect = (
        assert_application_fetched_before_create
    )

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=application_lookup_port,
        get_claims_for_application_port=_make_get_claims_port(),
    )

    use_case.execute(command)


def test_execute_fetches_existing_claims_with_correct_laa_reference():
    command = _make_command()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = _make_claim()
    get_claims_port = _make_get_claims_port()

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(),
        get_claims_for_application_port=get_claims_port,
    )
    use_case.execute(command)

    get_claims_port.get_claims_by_laa_reference.assert_called_once_with(
        command.laa_reference
    )


def test_execute_does_not_raise_when_application_total_exceeds_limit():
    command = _make_command()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = _make_claim()

    existing_claim = MagicMock(spec=Claim)
    existing_claim.total_profit_cost_gross = Decimal("9000.00")

    application = MagicMock(spec=Application)
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 1000
    application.proceeding.certificate_start_date = None
    application.overall_decision = MeritsDecision.GRANTED

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(application),
        get_claims_for_application_port=_make_get_claims_port([existing_claim]),
    )

    use_case.execute(command)  # should not raise


def test_execute_persists_auto_reject_and_returns_rejection_reasons():
    command = _make_command({"net": Decimal("1.00"), "gross": Decimal("1.00")})
    claim = _make_claim()

    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim
    create_claim_decision_port = _make_create_claim_decision_port()
    create_decision_reason_port = _make_create_decision_reason_port()
    update_claim_status_port = _make_update_claim_status_port()

    application = MagicMock(spec=Application)
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 999999
    application.proceeding.certificate_start_date = None
    application.overall_decision = MeritsDecision.GRANTED

    existing_claims = [
        Claim(
            claim_id=index + 100,
            laa_reference=12345,
            claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
            status_id=ClaimStatus.SUBMITTED,
            poa_type_id=POAType.PROFIT_COST,
            submission_date=datetime.now(UTC),
            total_profit_cost_net=Decimal("1.00"),
            total_profit_cost_gross=Decimal("1.00"),
        )
        for index in range(4)
    ]

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(application),
        get_claims_for_application_port=_make_get_claims_port(existing_claims),
        create_claim_decision_port=create_claim_decision_port,
        create_decision_reason_port=create_decision_reason_port,
        update_claim_status_port=update_claim_status_port,
    )

    result = use_case.execute(command)

    assert result.claim.status_id == ClaimStatus.REJECTED
    assert result.rejection_reasons == [ReasonCode.MAX_POA_CLAIMS_EXCEEDED]
    create_claim_decision_port.create_claim_decision.assert_called_once_with(
        claim_id=1,
        decision_status=ClaimDecisionStatus.REJECT,
    )
    create_decision_reason_port.create_decision_reason.assert_called_once_with(
        claim_decision_id=10,
        reason_code=ReasonCode.MAX_POA_CLAIMS_EXCEEDED,
        justification=None,
    )
    update_claim_status_port.update_claim_status.assert_called_once_with(
        claim_id=1,
        status=ClaimStatus.REJECTED,
    )
    assert create_claim_port.commit.call_count == 2


def test_execute_returns_submitted_claim_when_auto_reject_persistence_fails():
    command = _make_command({"net": Decimal("1.00"), "gross": Decimal("1.00")})
    claim = _make_claim()

    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim
    create_claim_decision_port = _make_create_claim_decision_port()
    create_decision_reason_port = _make_create_decision_reason_port()
    create_decision_reason_port.create_decision_reason.side_effect = Exception("boom")
    update_claim_status_port = _make_update_claim_status_port()

    application = MagicMock(spec=Application)
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 999999
    application.proceeding.certificate_start_date = None
    application.overall_decision = MeritsDecision.GRANTED

    existing_claims = [
        Claim(
            claim_id=index + 200,
            laa_reference=12345,
            claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
            status_id=ClaimStatus.SUBMITTED,
            poa_type_id=POAType.PROFIT_COST,
            submission_date=datetime.now(UTC),
            total_profit_cost_net=Decimal("1.00"),
            total_profit_cost_gross=Decimal("1.00"),
        )
        for index in range(4)
    ]

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(application),
        get_claims_for_application_port=_make_get_claims_port(existing_claims),
        create_claim_decision_port=create_claim_decision_port,
        create_decision_reason_port=create_decision_reason_port,
        update_claim_status_port=update_claim_status_port,
    )

    result = use_case.execute(command)

    assert result.claim.status_id == ClaimStatus.SUBMITTED
    assert result.rejection_reasons is None
    create_claim_port.rollback.assert_called_once()
    assert create_claim_port.commit.call_count == 1


def test_execute_auto_approves_eligible_payment_on_account_claim():
    command = _make_command({"net": Decimal("50000.00"), "gross": Decimal("50000.00")})
    claim = _make_claim()

    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim
    create_claim_decision_port = _make_create_claim_decision_port()
    update_claim_status_port = _make_update_claim_status_port()

    application = MagicMock(spec=Application)
    application.status = "LIVE"
    application.overall_decision = "GRANTED"
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 999999
    application.proceeding.certificate_start_date = None

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(application),
        get_claims_for_application_port=_make_get_claims_port(),
        create_claim_decision_port=create_claim_decision_port,
        update_claim_status_port=update_claim_status_port,
    )

    result = use_case.execute(command)

    assert result.claim.status_id == ClaimStatus.PAY_IN_FULL
    assert result.rejection_reasons is None
    create_claim_decision_port.create_claim_decision.assert_called_once_with(
        claim_id=1,
        decision_status=ClaimDecisionStatus.PAY_IN_FULL,
    )
    update_claim_status_port.update_claim_status.assert_called_once_with(
        claim_id=1,
        status=ClaimStatus.PAY_IN_FULL,
    )
    assert create_claim_port.commit.call_count == 2


def test_execute_does_not_auto_approve_when_amount_exceeds_threshold():
    command = _make_command({"net": Decimal("50000.01"), "gross": Decimal("50000.01")})
    claim = _make_claim()

    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim
    create_claim_decision_port = _make_create_claim_decision_port()
    update_claim_status_port = _make_update_claim_status_port()

    application = MagicMock(spec=Application)
    application.status = "LIVE"
    application.overall_decision = "GRANTED"
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 999999
    application.proceeding.certificate_start_date = None

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(application),
        get_claims_for_application_port=_make_get_claims_port(),
        create_claim_decision_port=create_claim_decision_port,
        update_claim_status_port=update_claim_status_port,
    )

    result = use_case.execute(command)

    assert result.claim.status_id != ClaimStatus.PAY_IN_FULL
    assert result.rejection_reasons is None
    create_claim_decision_port.create_claim_decision.assert_not_called()
    update_claim_status_port.update_claim_status.assert_not_called()
    assert create_claim_port.commit.call_count == 1


def test_execute_does_not_auto_approve_non_payment_on_account_claim():
    command = _make_command(
        {
            "claim_type": ClaimType.FINAL_BILL,
            "poa_type": None,
            "net": Decimal("50000.00"),
            "gross": Decimal("50000.00"),
        }
    )
    claim = _make_claim()

    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim
    create_claim_decision_port = _make_create_claim_decision_port()
    update_claim_status_port = _make_update_claim_status_port()

    application = MagicMock(spec=Application)
    application.status = "LIVE"
    application.overall_decision = "GRANTED"
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 999999
    application.proceeding.certificate_start_date = None

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(application),
        get_claims_for_application_port=_make_get_claims_port(),
        create_claim_decision_port=create_claim_decision_port,
        update_claim_status_port=update_claim_status_port,
    )

    result = use_case.execute(command)

    assert result.claim.status_id != ClaimStatus.PAY_IN_FULL
    create_claim_decision_port.create_claim_decision.assert_not_called()
    update_claim_status_port.update_claim_status.assert_not_called()


def test_execute_sets_funds_from_cumulative_approved_claims_and_new_amount():
    command = _make_command({"net": Decimal("800.00"), "gross": Decimal("1000.00")})
    claim = _make_claim()

    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim

    application = MagicMock(spec=Application)
    application.status = "LIVE"
    application.overall_decision = "GRANTED"
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 10000
    application.proceeding.certificate_start_date = None

    def _existing_claim(claim_id, gross=None, vat_zero=None):
        return Claim(
            claim_id=claim_id,
            laa_reference=12345,
            claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
            status_id=ClaimStatus.PAY_IN_FULL,
            poa_type_id=POAType.PROFIT_COST,
            submission_date=datetime.now(UTC),
            total_profit_cost_gross=gross,
            total_profit_cost_vat_zero=vat_zero,
        )

    granted = _existing_claim(2, gross=Decimal("2000.00"))
    paid_in_full = _existing_claim(3, vat_zero=Decimal("1500.00"))
    rejected = _existing_claim(4, gross=Decimal("5000.00"))
    pending = _existing_claim(5, gross=Decimal("3000.00"))

    get_claim_decision_port = _make_get_claim_decision_port(
        {
            2: ClaimDecision(
                claim_decision_id=2, claim_id=2, decision=ClaimDecisionStatus.GRANT
            ),
            3: ClaimDecision(
                claim_decision_id=3,
                claim_id=3,
                decision=ClaimDecisionStatus.PAY_IN_FULL,
            ),
            4: ClaimDecision(
                claim_decision_id=4, claim_id=4, decision=ClaimDecisionStatus.REJECT
            ),
            5: ClaimDecision(
                claim_decision_id=5, claim_id=5, decision=ClaimDecisionStatus.PENDING
            ),
        }
    )

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(application),
        get_claims_for_application_port=_make_get_claims_port(
            [granted, paid_in_full, rejected, pending]
        ),
        get_claim_decision_port=get_claim_decision_port,
    )

    use_case.execute(command)

    # 10000 limit - (2000 + 1500 approved) - 1000 new claim requested = 5500
    funds_arg = create_claim_port.create_claim.call_args.kwargs[
        "total_funds_remaining_after_claim"
    ]
    assert funds_arg == Decimal("5500.00")


def test_execute_sets_funds_deducting_new_amount_even_when_auto_approved():
    command = _make_command({"net": Decimal("2000.00"), "gross": Decimal("2000.00")})
    claim = _make_claim()

    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim
    create_claim_decision_port = _make_create_claim_decision_port()
    update_claim_status_port = _make_update_claim_status_port()

    application = MagicMock(spec=Application)
    application.status = "LIVE"
    application.overall_decision = "GRANTED"
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 10000
    application.proceeding.certificate_start_date = None

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(application),
        get_claims_for_application_port=_make_get_claims_port([]),
        create_claim_decision_port=create_claim_decision_port,
        update_claim_status_port=update_claim_status_port,
        get_claim_decision_port=_make_get_claim_decision_port(),
    )

    use_case.execute(command)

    # No existing claims, so 10000 - 2000 (this claim's requested amount) = 8000
    funds_arg = create_claim_port.create_claim.call_args.kwargs[
        "total_funds_remaining_after_claim"
    ]
    assert funds_arg == Decimal("8000.00")


def test_execute_sets_funds_without_decision_port_treats_existing_as_unapproved():
    command = _make_command({"net": Decimal("500.00"), "gross": Decimal("500.00")})
    claim = _make_claim()

    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim

    application = MagicMock(spec=Application)
    application.status = "LIVE"
    application.overall_decision = "GRANTED"
    application.proceeding = MagicMock()
    application.proceeding.substantive_cost_limitation = 10000
    application.proceeding.certificate_start_date = None

    existing_claim = Claim(
        claim_id=2,
        laa_reference=12345,
        claim_type_id=ClaimType.PAYMENT_ON_ACCOUNT,
        status_id=ClaimStatus.PAY_IN_FULL,
        poa_type_id=POAType.PROFIT_COST,
        submission_date=datetime.now(UTC),
        total_profit_cost_gross=Decimal("2000.00"),
    )

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(application),
        get_claims_for_application_port=_make_get_claims_port([existing_claim]),
    )

    use_case.execute(command)

    # Without a decision port the existing claim is not treated as approved:
    # 10000 - 500 (new claim requested amount) = 9500
    funds_arg = create_claim_port.create_claim.call_args.kwargs[
        "total_funds_remaining_after_claim"
    ]
    assert funds_arg == Decimal("9500.00")
