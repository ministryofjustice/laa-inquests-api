import pytest

from app.auth.rbac import Role
from tests.e2e.auth import (
    PROVIDER_FIRM_CODE,
    PROVIDER_OFFICE_ID,
    set_token_office_codes,
)
from tests.e2e.factories import create_application_in_db, create_claim_in_db

UNKNOWN_CLAIM_REFERENCE = "INQC-ZZZZ-ZZZZ"


def _retrieve_application(client, claim_reference, role=Role.PROVIDER_CLAIMS_USER):
    return client.get(
        f"/claims/{claim_reference}/application",
        headers={"Authorization": f"Bearer {role.value}"},
    )


def test_200_retrieve_application_for_claim_returns_application_reference(
    session, client
):
    application = create_application_in_db(session)
    claim = create_claim_in_db(
        session,
        application_id=application.application_id,
    )

    response = client.get(
        f"/claims/{claim.claim_reference}/application",
        headers={
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"laaReference": application.laa_reference}


def test_404_retrieve_application_for_claim_returns_not_found_for_unknown_claim(
    client,
):
    response = client.get(
        "/claims/INQC-ZZZZ-ZZZZ/application",
        headers={
            "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Claim not found"}


class TestRetrieveApplicationForClaimOfficeIdCheck:
    @pytest.mark.parametrize(
        ("application_office_id", "token_office_ids"),
        [
            (PROVIDER_OFFICE_ID, {PROVIDER_OFFICE_ID}),
            ("U68YP1", {PROVIDER_OFFICE_ID, "U68YP1"}),
        ],
        ids=["own-office", "second-office-in-token"],
    )
    def test_200_provider_gets_application_when_application_office_id_matches_theirs_in_the_token(
        self, session, client, application_office_id, token_office_ids
    ):
        set_token_office_codes(token_office_ids)
        application = create_application_in_db(
            session,
            provider_overrides={
                "office_id": application_office_id,
                "firm_code": PROVIDER_FIRM_CODE,
            },
        )
        claim = create_claim_in_db(session, application_id=application.application_id)

        response = _retrieve_application(client, claim.claim_reference)

        assert response.status_code == 200
        assert response.json() == {"laaReference": application.laa_reference}

    @pytest.mark.parametrize(
        ("firm_code", "application_office_id"),
        [(PROVIDER_FIRM_CODE, "U68YP1"), ("ZZ999Z", "P38Y31")],
        ids=["same-firm-different-office", "different-firm"],
    )
    def test_404_provider_cannot_get_application_when_application_office_id_mismatches_with_the_one_in_the_token(
        self, session, client, firm_code, application_office_id
    ):
        set_token_office_codes({PROVIDER_OFFICE_ID})
        application = create_application_in_db(
            session,
            provider_overrides={
                "office_id": application_office_id,
                "firm_code": firm_code,
            },
        )
        claim = create_claim_in_db(session, application_id=application.application_id)

        unknown_response = _retrieve_application(client, UNKNOWN_CLAIM_REFERENCE)
        response = _retrieve_application(client, claim.claim_reference)

        assert response.status_code == unknown_response.status_code == 404
        assert response.json() == unknown_response.json()

    @pytest.mark.parametrize(
        "caseworker_role",
        [Role.CLAIMS_CASEWORKER, Role.CUSTOMER_SERVICE_AGENT, Role.ASSURANCE],
    )
    def test_200_caseworker_gets_application_from_any_office(
        self, session, client, caseworker_role
    ):
        application = create_application_in_db(
            session,
            provider_overrides={
                "office_id": PROVIDER_OFFICE_ID,
                "firm_code": PROVIDER_FIRM_CODE,
            },
        )
        claim = create_claim_in_db(session, application_id=application.application_id)

        response = _retrieve_application(client, claim.claim_reference, caseworker_role)

        assert response.status_code == 200
        assert response.json() == {"laaReference": application.laa_reference}
