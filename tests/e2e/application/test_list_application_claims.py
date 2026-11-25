from decimal import Decimal

import pytest
from sqlmodel import select

from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.claim.enums import (
    ClaimDecisionStatus,
    ClaimStatus,
    ClaimType,
    InquestOutcomeCode,
    POAType,
)
from app.models.claim.index import Claim
from tests.e2e.auth import (
    TEST_PROVIDER_FIRM_CODE,
    TEST_PROVIDER_OFFICE_ID,
    set_token_office_codes,
)
from tests.e2e.factories import (
    create_application_in_db,
    create_claim_decision_in_db,
    create_claim_in_db,
    get_application_id,
)


def _seed_claim(
    session,
    laa_reference: int,
    status: ClaimStatus,
    claim_type: ClaimType = ClaimType.PAYMENT_ON_ACCOUNT,
) -> Claim:
    poa_type = (
        POAType.PROFIT_COST if claim_type == ClaimType.PAYMENT_ON_ACCOUNT else None
    )
    return create_claim_in_db(
        session,
        application_id=get_application_id(session, laa_reference),
        status=status,
        claim_type=claim_type,
        poa_type=poa_type,
        total_profit_cost_net=Decimal("1000.00"),
        total_profit_cost_gross=Decimal("1200.00"),
        total_profit_cost_vat_zero=Decimal("500.00"),
        total_funds_remaining_after_claim=Decimal("8800.00"),
    )


def _seed_final_bill_claim(
    session,
    laa_reference: int,
    status: ClaimStatus,
    claim_type: ClaimType = ClaimType.NIL_BILL,
) -> Claim:
    return create_claim_in_db(
        session,
        application_id=get_application_id(session, laa_reference),
        status=status,
        claim_type=claim_type,
        total_profit_cost_gross=0,
        total_profit_cost_net=None,
        total_profit_cost_vat_zero=None,
        inquest_outcomes=(InquestOutcomeCode.OPEN_CONCLUSION,),
        has_alternative_funding=False,
        has_recovery_costs_awarded=True,
        financial_recovery_previous_pre_certificate_costs=100,
        financial_recovery_cost=200,
        financial_recovery_damages=300,
        financial_recovery_interest=50,
        paying_party="Test Council",
    )


def test_200_returns_empty_list_when_application_has_no_claims(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_200_assessed_true_returns_only_non_submitted_claims(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    _seed_claim(session, laa_reference, ClaimStatus.SUBMITTED)
    assessed_claim = _seed_claim(session, laa_reference, ClaimStatus.ACCEPTED)

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [c["claimReference"] for c in body] == [assessed_claim.claim_reference]
    assert set(body[0].keys()) == {
        "claimReference",
        "claimTypeId",
        "submissionDate",
        "totalProfitCostNet",
        "totalProfitCostGross",
        "totalProfitCostVatZero",
        "totalAmount",
        "totalFundsRemainingAfterClaim",
        "poaTypeId",
        "statusId",
        "claimDecisionStatus",
    }


def test_200_total_amount_uses_vat_zero_when_gross_is_zero(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference, ClaimStatus.ACCEPTED)
    claim.poa_type_id = POAType.EXPERT_COST
    claim.total_profit_cost_net = Decimal("0.00")
    claim.total_profit_cost_gross = Decimal("0.00")
    claim.total_profit_cost_vat_zero = Decimal("150.00")
    session.add(claim)
    session.commit()

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["totalAmount"] == "150.00"


def test_200_total_amount_prefers_gross_when_vat_zero_also_present(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    _seed_claim(session, laa_reference, ClaimStatus.ACCEPTED)

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["totalAmount"] == "1200.00"


def test_200_includes_claim_status_for_each_claim(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    _seed_claim(session, laa_reference, ClaimStatus.ACCEPTED)

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["statusId"] == "ACCEPTED"


def test_200_includes_claim_decision_status_when_a_decision_exists(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    claim = _seed_claim(session, laa_reference, ClaimStatus.REJECTED)
    create_claim_decision_in_db(session, claim.claim_id, ClaimDecisionStatus.REJECT)

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["claimDecisionStatus"] == "REJECT"


def test_200_claim_decision_status_is_null_when_no_decision_exists(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    _seed_claim(session, laa_reference, ClaimStatus.ACCEPTED)

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["claimDecisionStatus"] is None


def test_200_assessed_false_returns_only_submitted_claims(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    submitted_claim = _seed_claim(session, laa_reference, ClaimStatus.SUBMITTED)
    _seed_claim(session, laa_reference, ClaimStatus.ACCEPTED)

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=false",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert [c["claimReference"] for c in response.json()] == [
        submitted_claim.claim_reference
    ]


def test_200_returns_submitted_nil_bill_claim_for_providers(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    _seed_final_bill_claim(session, laa_reference, ClaimStatus.SUBMITTED)
    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=false",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["statusId"] == "SUBMITTED"


def test_200_returns_pay_in_full_nil_bill_claim_for_providers(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    _seed_final_bill_claim(session, laa_reference, ClaimStatus.PAY_IN_FULL)
    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["statusId"] == "PAY_IN_FULL"


def test_200_returns_submitted_final_bill_claim_for_providers(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    _seed_claim(session, laa_reference, ClaimStatus.SUBMITTED, ClaimType.FINAL_BILL)
    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=false",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["statusId"] == "SUBMITTED"


def test_200_returns_pay_in_full_final_bill_claim_for_providers(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference
    _seed_claim(session, laa_reference, ClaimStatus.PAY_IN_FULL, ClaimType.FINAL_BILL)
    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["statusId"] == "PAY_IN_FULL"


def test_422_when_assessed_query_param_is_missing(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.get(
        f"/applications/{laa_reference}/claims",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 422


def test_422_when_assessed_query_param_is_not_a_boolean(session, client):
    laa_reference = session.exec(select(Application)).first().laa_reference

    response = client.get(
        f"/applications/{laa_reference}/claims?assessed=maybe",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 422


def test_404_when_application_does_not_exist(client):
    response = client.get(
        "/applications/999999/claims?assessed=true",
        headers={"Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"


UNKNOWN_LAA_REFERENCE = "999999"


def _list_claims(
    client, laa_reference, role=Role.PROVIDER_CLAIMS_USER, assessed="false"
):
    return client.get(
        f"/applications/{laa_reference}/claims?assessed={assessed}",
        headers={"Authorization": f"Bearer {role.value}"},
    )


def _claim_references(response):
    return [c["claimReference"] for c in response.json()]


class TestListApplicationClaimsOfficeIdCheck:
    @pytest.mark.parametrize(
        ("application_office_id", "token_office_ids"),
        [
            (TEST_PROVIDER_OFFICE_ID, {TEST_PROVIDER_OFFICE_ID}),
            ("1A234B", {TEST_PROVIDER_OFFICE_ID, "1A234B"}),
        ],
        ids=["own-office", "second-office-in-token"],
    )
    def test_200_provider_lists_claims_when_application_office_id_matches_theirs_in_the_token(
        self, session, client, application_office_id, token_office_ids
    ):
        set_token_office_codes(token_office_ids)
        application = create_application_in_db(
            session,
            provider_overrides={
                "office_id": application_office_id,
                "firm_code": TEST_PROVIDER_FIRM_CODE,
            },
        )
        claim = create_claim_in_db(session, application_id=application.application_id)

        response = _list_claims(client, application.laa_reference)

        assert response.status_code == 200
        assert _claim_references(response) == [claim.claim_reference]

    @pytest.mark.parametrize("assessed", ["true", "false"])
    @pytest.mark.parametrize(
        ("firm_code", "application_office_id"),
        [(TEST_PROVIDER_FIRM_CODE, "1A234B"), ("5678", "test-office-id")],
        ids=["same-firm-different-office", "different-firm"],
    )
    def test_404_provider_cannot_list_claims_when_application_office_id_mismatches_with_the_one_in_their_token(
        self, session, client, firm_code, application_office_id, assessed
    ):
        set_token_office_codes({TEST_PROVIDER_OFFICE_ID})
        application = create_application_in_db(
            session,
            provider_overrides={
                "office_id": application_office_id,
                "firm_code": firm_code,
            },
        )
        create_claim_in_db(session, application_id=application.application_id)

        unknown_response = _list_claims(
            client, UNKNOWN_LAA_REFERENCE, assessed=assessed
        )
        response = _list_claims(client, application.laa_reference, assessed=assessed)

        assert response.status_code == unknown_response.status_code == 404
        assert response.json() == unknown_response.json()

    @pytest.mark.parametrize(
        "caseworker_role",
        [Role.CLAIMS_CASEWORKER, Role.CUSTOMER_SERVICE_AGENT, Role.ASSURANCE],
    )
    def test_200_caseworker_can_list_claims_from_any_office(
        self, session, client, caseworker_role
    ):
        application = create_application_in_db(
            session,
            provider_overrides={
                "office_id": TEST_PROVIDER_OFFICE_ID,
                "firm_code": TEST_PROVIDER_FIRM_CODE,
            },
        )
        claim = create_claim_in_db(session, application_id=application.application_id)

        response = _list_claims(client, application.laa_reference, role=caseworker_role)

        assert response.status_code == 200
        assert _claim_references(response) == [claim.claim_reference]
