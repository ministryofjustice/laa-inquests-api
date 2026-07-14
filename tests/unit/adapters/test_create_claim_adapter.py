from sqlmodel import select
from decimal import Decimal

from app.adapters.application_repository_adapter import ApplicationRepositoryAdapter
from app.domain.claim import Claim as DomainClaim
from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus, ClaimType, POAType
from app.models.claim.index import Claim


def _make_domain_claim(overrides=None) -> DomainClaim:
    payload = {
        "claim_type": ClaimType.PAYMENT_ON_ACCOUNT,
        "net": Decimal("1000.00"),
        "gross": Decimal("1200.00"),
        "vat_zero_total": None,
        "poa_type": POAType.PROFIT_COST,
    }
    if overrides is not None:
        payload.update(overrides)
    return DomainClaim(**payload)


def test_create_claim_persists_claim_with_expected_values(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ApplicationRepositoryAdapter(session)

    created_claim = adapter.create_claim(
        str(laa_reference),
        _make_domain_claim(
            {
                "poa_type": POAType.EXPERT_COST,
                "vat_zero_total": Decimal("150.00"),
            }
        ),
        "claimant-123@provider.co.uk",
    )
    stored_claim = session.get(Claim, created_claim.claim_id)

    assert created_claim.claim_id is not None
    assert stored_claim is not None
    assert stored_claim.laa_reference == laa_reference
    assert stored_claim.claim_type_id == ClaimType.PAYMENT_ON_ACCOUNT
    assert stored_claim.total_profit_cost_net == Decimal("1000.00")
    assert stored_claim.total_profit_cost_gross == Decimal("1200.00")
    assert stored_claim.total_profit_cost_vat_zero == Decimal("150.00")


def test_create_claim_defaults_status_to_pending(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ApplicationRepositoryAdapter(session)

    created_claim = adapter.create_claim(
        str(laa_reference),
        _make_domain_claim(),
        "claimant-123@provider.co.uk",
    )

    assert created_claim.status_id == ClaimStatus.PENDING


def test_create_claim_sets_submission_date(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ApplicationRepositoryAdapter(session)

    created_claim = adapter.create_claim(
        str(laa_reference),
        _make_domain_claim(),
        "claimant-123@provider.co.uk",
    )

    assert created_claim.submission_date is not None


def test_create_claim_persists_optional_poa_type_and_claimant(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ApplicationRepositoryAdapter(session)

    created_claim = adapter.create_claim(
        str(laa_reference),
        _make_domain_claim(),
        "claimant-123@provider.co.uk",
    )

    assert created_claim.poa_type_id == POAType.PROFIT_COST
    assert created_claim.claimant_id == "claimant-123@provider.co.uk"


def test_create_claim_defaults_optional_fields_to_none_when_omitted(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = ApplicationRepositoryAdapter(session)

    claim = _make_domain_claim(
        {
            "claim_type": ClaimType.FINAL_BILL,
            "poa_type": None,
        }
    )
    created_claim = adapter.create_claim(str(laa_reference), claim, None)

    assert created_claim.poa_type_id is None
    assert created_claim.claimant_id is None
