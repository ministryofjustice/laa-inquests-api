from sqlmodel import select

from app.models.application.index import Application
from app.models.claim.index import Claim


def _make_request_body(overrides=None):
    body = {
        "claimType": "PAYMENT_ON_ACCOUNT",
        "totalProfitCostNet": 1000,
        "totalProfitCostGross": 1200,
        "poaTypeId": "PROFIT_COST",
        "claimantId": "claimant-123@provider.co.uk",
    }
    if overrides is not None:
        body.update(overrides)
    return body


def test_201_create_claim_response_contains_expected_properties(
    session, client, auth_token
):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert isinstance(claim["claimId"], int)
    assert claim["laaReference"] == laa_reference
    assert claim["claimTypeId"] == "PAYMENT_ON_ACCOUNT"
    assert claim["totalProfitCostNet"] == 1000
    assert claim["totalProfitCostGross"] == 1200
    assert claim["poaTypeId"] == "PROFIT_COST"
    assert claim["claimantId"] == "claimant-123@provider.co.uk"
    assert isinstance(claim["submissionDate"], str)


def test_201_create_claim_defaults_status_to_pending(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.json()["statusId"] == "PENDING"


def test_201_create_claim_without_optional_fields(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"claimType": "FINAL_BILL", "poaTypeId": None, "claimantId": None}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201
    claim = response.json()
    assert claim["poaTypeId"] is None
    assert claim["claimantId"] is None


def test_201_create_claim_persists_claim_to_database(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    claim_id = response.json()["claimId"]
    stored_claim = session.get(Claim, claim_id)
    assert stored_claim is not None
    assert stored_claim.laa_reference == laa_reference


def test_422_payment_on_account_without_poa_type_id(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body({"poaTypeId": None}),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]["errorCode"]
        == "MISSING_POA_TYPE_FOR_PAYMENT_ON_ACCOUNT"
    )


def test_422_non_payment_on_account_with_poa_type_id(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"claimType": "FINAL_BILL", "poaTypeId": "PROFIT_COST"}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]["errorCode"]
        == "POA_TYPE_NOT_ALLOWED_FOR_NON_PAYMENT_ON_ACCOUNT"
    )


def test_422_profit_cost_with_no_cost_fields(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {
                "totalProfitCostNet": None,
                "totalProfitCostGross": None,
                "totalProfitCostVatZero": None,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["errorCode"] == "MISSING_TOTAL_CLAIM_COST"


def test_422_profit_cost_with_net_higher_than_gross(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"totalProfitCostNet": 1200, "totalProfitCostGross": 1000}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["errorCode"] == "NET_TOTAL_HIGHER_THAN_GROSS_TOTAL"


def test_201_profit_cost_with_vat_zero_only(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {
                "totalProfitCostNet": None,
                "totalProfitCostGross": None,
                "totalProfitCostVatZero": 500,
            }
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 201


def test_422_profit_cost_mixing_vat_zero_and_net(session, client, auth_token):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(
            {"totalProfitCostNet": 1000, "totalProfitCostVatZero": 500}
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["errorCode"] == "PROFIT_COST_MIXED_VAT"
