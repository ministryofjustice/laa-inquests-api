from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.models.claim.index import Claim, ClaimCreate
from app.ports.create_claim_port import CreateClaimPort
from app.use_cases.create_claim import CreateClaimUseCase
from app.domain.claim_error import ClaimErrorCode
from app.use_cases.exceptions import InvalidClaimError


def _make_request() -> ClaimCreate:
    return ClaimCreate.model_validate(
        {
            "claimType": "PAYMENT_ON_ACCOUNT",
            "totalProfitCostNet": 1000,
            "totalProfitCostGross": 1200,
            "poaTypeId": "PROFIT_COST",
            "claimantId": "claimant-123@provider.co.uk",
        }
    )


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
    request = _make_request()
    claim = _make_claim()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim

    use_case = CreateClaimUseCase(create_claim_port=create_claim_port)
    use_case.execute("12345", request)

    create_claim_port.create_claim.assert_called_once_with("12345", request)
    create_claim_port.commit.assert_called_once()


def test_execute_returns_created_claim():
    request = _make_request()
    claim = _make_claim()
    create_claim_port = MagicMock(spec=CreateClaimPort)
    create_claim_port.create_claim.return_value = claim

    use_case = CreateClaimUseCase(create_claim_port=create_claim_port)
    result = use_case.execute("12345", request)

    assert result is claim


def test_claim_create_rejects_payment_on_account_without_poa_type():
    with pytest.raises(ValidationError):
        ClaimCreate.model_validate(
            {
                "claimType": "PAYMENT_ON_ACCOUNT",
                "totalProfitCostNet": 1000,
                "totalProfitCostGross": 1200,
                "poaTypeId": None,
            }
        )


def test_claim_create_rejects_non_payment_on_account_with_poa_type():
    with pytest.raises(ValidationError):
        ClaimCreate.model_validate(
            {
                "claimType": "FINAL_BILL",
                "totalProfitCostNet": 1000,
                "totalProfitCostGross": 1200,
                "poaTypeId": "PROFIT_COST",
            }
        )


def test_execute_raises_invalid_claim_error_when_profit_cost_has_no_costs():
    request = ClaimCreate.model_validate(
        {
            "claimType": "PAYMENT_ON_ACCOUNT",
            "poaTypeId": "PROFIT_COST",
        }
    )
    use_case = CreateClaimUseCase(create_claim_port=MagicMock(spec=CreateClaimPort))

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute("12345", request)
    assert exc_info.value.code == ClaimErrorCode.MISSING_TOTAL_CLAIM_COST


def test_execute_raises_invalid_claim_error_when_net_higher_than_gross():
    request = ClaimCreate.model_validate(
        {
            "claimType": "PAYMENT_ON_ACCOUNT",
            "poaTypeId": "PROFIT_COST",
            "totalProfitCostNet": 1200,
            "totalProfitCostGross": 1000,
        }
    )
    use_case = CreateClaimUseCase(create_claim_port=MagicMock(spec=CreateClaimPort))

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute("12345", request)
    assert exc_info.value.code == ClaimErrorCode.NET_TOTAL_HIGHER_THAN_GROSS_TOTAL


def test_execute_raises_invalid_claim_error_when_mixing_vat_rates():
    request = ClaimCreate.model_validate(
        {
            "claimType": "PAYMENT_ON_ACCOUNT",
            "poaTypeId": "PROFIT_COST",
            "totalProfitCostNet": 1000,
            "totalProfitCostVatZero": 500,
        }
    )
    use_case = CreateClaimUseCase(create_claim_port=MagicMock(spec=CreateClaimPort))

    with pytest.raises(InvalidClaimError) as exc_info:
        use_case.execute("12345", request)
    assert exc_info.value.code == ClaimErrorCode.PROFIT_COST_MIXED_VAT


def test_execute_does_not_raise_for_non_profit_cost_without_costs():
    request = ClaimCreate.model_validate(
        {"claimType": "FINAL_BILL"}
    )
    port = MagicMock(spec=CreateClaimPort)
    port.create_claim.return_value = _make_claim()
    use_case = CreateClaimUseCase(create_claim_port=port)

    use_case.execute("12345", request)  # should not raise


def test_claim_create_accepts_payment_on_account_with_poa_type():
    request = ClaimCreate.model_validate(
        {
            "claimType": "PAYMENT_ON_ACCOUNT",
            "totalProfitCostNet": 1000,
            "totalProfitCostGross": 1200,
            "poaTypeId": "PROFIT_COST",
        }
    )

    assert request.poa_type_id is not None


def test_claim_create_accepts_non_payment_on_account_without_poa_type():
    request = ClaimCreate.model_validate(
        {
            "claimType": "FINAL_BILL",
            "totalProfitCostNet": 1000,
            "totalProfitCostGross": 1200,
            "poaTypeId": None,
        }
    )

    assert request.poa_type_id is None
