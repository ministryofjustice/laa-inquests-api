from unittest.mock import MagicMock
from decimal import Decimal

import pytest

from app.models.claim.enums import ClaimType, POAType
from app.models.claim.index import Claim
from app.ports.create_claim_port import CreateClaimPort
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


def test_execute_creates_claim_and_commits():
    command = _make_command()
    claim = _make_claim()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim

    use_case = CreateClaimUseCase(create_claim_port=create_claim_port)
    use_case.execute(command)

    create_claim_port.create_claim.assert_called_once()
    _, kwargs = create_claim_port.create_claim.call_args
    assert kwargs["laa_reference"] == command.laa_reference
    assert kwargs["claimant_id"] == command.claimant_id
    assert kwargs["claim"].claim_type == command.claim_type
    create_claim_port.commit.assert_called_once()


def test_execute_returns_created_claim():
    command = _make_command()
    claim = _make_claim()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim

    use_case = CreateClaimUseCase(create_claim_port=create_claim_port)
    result = use_case.execute(command)

    assert result is claim


def test_execute_raises_invalid_claim_error_when_payment_on_account_without_poa_type():
    command = _make_command({"poa_type": None})
    use_case = CreateClaimUseCase(create_claim_port=MagicMock(spec=CreateClaimPort))

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
    use_case = CreateClaimUseCase(create_claim_port=MagicMock(spec=CreateClaimPort))

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute(command)
    assert (
        exc_info.value.code
        == ClaimErrorCode.POA_TYPE_NOT_ALLOWED_FOR_NON_PAYMENT_ON_ACCOUNT
    )


def test_execute_raises_invalid_claim_error_when_profit_cost_has_no_costs():
    command = _make_command({"net": None, "gross": None, "vat_zero_total": None})
    use_case = CreateClaimUseCase(create_claim_port=MagicMock(spec=CreateClaimPort))

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute(command)
    assert exc_info.value.code == ClaimErrorCode.MISSING_TOTAL_CLAIM_COST


def test_execute_raises_invalid_claim_error_when_net_higher_than_gross():
    command = _make_command({"net": Decimal("1200.00"), "gross": Decimal("1000.00")})
    use_case = CreateClaimUseCase(create_claim_port=MagicMock(spec=CreateClaimPort))

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
    use_case = CreateClaimUseCase(create_claim_port=MagicMock(spec=CreateClaimPort))

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute(command)

    assert exc_info.value.code == ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL


def test_execute_raises_invalid_claim_error_when_mixing_vat_rates():
    command = _make_command({"vat_zero_total": Decimal("500.00")})
    use_case = CreateClaimUseCase(create_claim_port=MagicMock(spec=CreateClaimPort))

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
    use_case = CreateClaimUseCase(create_claim_port=port)

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
    use_case = CreateClaimUseCase(create_claim_port=port)

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
    use_case = CreateClaimUseCase(create_claim_port=port)

    use_case.execute(command)

    _, kwargs = port.create_claim.call_args
    assert kwargs["claim"].net == Decimal("0.00")
    assert kwargs["claim"].gross == Decimal("0.00")
    assert kwargs["claim"].vat_zero_total == Decimal("150.00")
