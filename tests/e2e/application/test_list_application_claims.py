from datetime import UTC, datetime
from decimal import Decimal

from sqlmodel import select

from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus, ClaimType, POAType
from app.models.claim.index import Claim


def _seed_claim(
    session,
    laa_reference: int,
    status: ClaimStatus,
    claim_type: ClaimType = ClaimType.PAYMENT_ON_ACCOUNT,
) -> Claim:
    claim = Claim(
        laa_reference=laa_reference,
        claim_type_id=claim_type,
        status_id=status,
        submission_date=datetime.now(UTC),
        total_profit_cost_net=Decimal("1000.00"),
        total_profit_cost_gross=Decimal("1200.00"),
        total_profit_cost_vat_zero=Decimal("500.00"),
        poa_type_id=POAType.PROFIT_COST,
    )
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


def test_200_returns_empty_list_when_application_has_no_claims(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_200_assessed_true_returns_only_non_submitted_claims(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    _seed_claim(session, laa_reference, ClaimStatus.SUBMITTED)
    assessed_claim = _seed_claim(session, laa_reference, ClaimStatus.ACCEPTED)

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [c["claimId"] for c in body] == [assessed_claim.claim_id]
    assert set(body[0].keys()) == {
        "claimId",
        "claimTypeId",
        "submissionDate",
        "totalProfitCostNet",
        "totalProfitCostGross",
        "totalProfitCostVatZero",
        "poaTypeId",
    }


def test_200_assessed_false_returns_only_submitted_claims(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference
    submitted_claim = _seed_claim(session, laa_reference, ClaimStatus.SUBMITTED)
    _seed_claim(session, laa_reference, ClaimStatus.ACCEPTED)

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=false",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert [c["claimId"] for c in response.json()] == [submitted_claim.claim_id]


def test_422_when_assessed_query_param_is_missing(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.get(
        f"/applications/{laa_reference}/claims",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 422


def test_401_returns_unauthorized_when_no_auth_header(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.get(f"/applications/{laa_reference}/claims?assessed=true")

    assert response.status_code == 401


def test_403_returns_forbidden_when_provider_token(entra_auth_client):
    response = entra_auth_client.get(
        "/applications/1/claims?assessed=true",
        headers={"Authorization": "Bearer valid-provider-entra-token"},
    )

    assert response.status_code == 403
