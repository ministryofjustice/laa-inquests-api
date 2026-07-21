from unittest.mock import MagicMock
from decimal import Decimal

import pytest

from app.models.application.index import Application
from app.models.claim.enums import ClaimType, POAType
from app.models.claim.index import Claim
from app.ports.application_lookup_port import ApplicationLookupPort
from app.ports.create_claim_port import CreateClaimPort
from app.ports.get_claims_for_application_port import GetClaimsForApplicationPort
from app.use_cases.create_claim import CreateClaimCommand, CreateClaimUseCase
from app.domain.claim_error import ClaimErrorCode
from app.use_cases.exceptions import InvalidClaimError


def _make_command(overrides=None) -> CreateClaimCommand:
    payload = {
        "laa_reference": "12345",
        "claim_type": ClaimType.PAYMENT_ON_ACCOUNT,
        "poa_type": POAType.PROFIT_COST,
        "net": Decimal("1000.00"),
        "gross": Decimal("1200.00"),
        "vat_zero_total": None,
        "claimant_id": "claimant-123@provider.co.uk",
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


def _make_application_lookup_port(application: Application | None = None):
    port = MagicMock(spec=ApplicationLookupPort)
    port.get_application_by_laa_reference.return_value = application
    return port


def _make_get_claims_port(claims: list[Claim] | None = None):
    port = MagicMock(spec=GetClaimsForApplicationPort)
    port.get_claims_by_laa_reference.return_value = claims or []
    return port


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
    application_lookup_port.get_application_by_laa_reference.assert_called_once_with(
        command.laa_reference
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

    assert result is claim


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

    def mark_application_fetched(_laa_reference: str) -> None:
        marker["application_fetched"] = True

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
    application.proceedings = [MagicMock()]
    application.proceedings[0].substantive_cost_limitation = 1000
    application.proceedings[0].certificate_start_date = None

    use_case = CreateClaimUseCase(
        create_claim_port=create_claim_port,
        application_lookup_port=_make_application_lookup_port(application),
        get_claims_for_application_port=_make_get_claims_port([existing_claim]),
    )

    use_case.execute(command)  # should not raise
