from unittest.mock import MagicMock

from app.models.claim.index import Claim, ClaimCreate
from app.ports.create_claim_port import CreateClaimPort
from app.use_cases.create_claim import CreateClaimUseCase


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
