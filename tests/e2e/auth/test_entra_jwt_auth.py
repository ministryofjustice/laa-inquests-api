import io

import pytest
from sqlmodel import select

from app import api
from app.auth.rbac import Role, get_current_user_permissions
from app.models.application.enums import MeritsDecision
from app.models.application.index import Application, CoronersLetter
from app.models.claim.index import ClaimEvidence
from tests.e2e.application.test_create_application import (
    _make_request_body as make_application_request_body,
)
from tests.helpers.application_payloads import create_application_payload
from tests.helpers.provider_details import (
    override_provider_details_port_with_provider_offices,
)


# This is our representative test that exercises the FastAPI permission dependency
# It verifies that a request without the required permission is rejected with a 403 status code.
# We do this once, and shouldn't need other 403 tests as we have a unit test that all endpoints
# have the relevant permission check in place as a dependency
def test_403_permission_dependency_rejects_request_without_required_permission(
    client,
):
    api.dependency_overrides[get_current_user_permissions] = lambda: set()

    response = client.post(
        "/applications",
        json=make_application_request_body(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-token",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": ("Forbidden: Missing required permission 'application:create'")
    }


# This is our representative test that exercises the FastAPI verify_entra_token dependency
# It verifies that an unauthorized request to a protected endpoint is rejected with a 401 status code.
def test_401_verify_entra_token_dependency_rejects_unauthorized_request(
    client,
):
    response = client.post(
        "/applications",
        json=make_application_request_body(),
        headers={
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": ("Not authenticated")}


def test_201_create_application_returns_201_when_provider_application_user_token(
    client,
):
    response = client.post(
        "/applications",
        json=create_application_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}",
        },
    )

    assert response.status_code == 201


def test_201_upload_coroners_letter_returns_201_when_provider_application_user_token(
    client,
):
    response = client.post(
        "/applications/upload-coroners-letter",
        files={
            "file": (
                "coroners_letter.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
    )

    assert response.status_code == 201


def test_204_refuse_decision_returns_204_when_caseworker_token(
    session,
    client,
):
    application = session.exec(select(Application)).first()
    response = client.patch(
        f"/applications/{application.laa_reference}/refuse-decision",
        json={
            "meritsDecision": MeritsDecision.REFUSED,
            "reasonForRefusal": "NOT_IN_SCOPE",
            "justification": "The matter does not meet scope requirements.",
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer Caseworker No Role",
        },
    )

    assert response.status_code == 204


def test_204_grant_decision_returns_204_when_caseworker_token(
    session,
    client,
):
    application = session.exec(select(Application)).first()
    response = client.patch(
        f"/applications/{application.laa_reference}/grant-decision",
        json={"certificateStartDate": "2000-01-01"},
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer Caseworker No Role",
        },
    )

    assert response.status_code == 204


class TestSearchApplicationAuth:
    def test_200_search_application_returns_200_when_provider_claims_user_token(
        self,
        client,
    ):
        response = client.get(
            "/applications/search",
            params={"laa_reference": "1"},
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 200


class TestUploadClaimEvidenceAuth:
    def test_201_upload_claim_evidence_when_provider_claims_user_token(
        self,
        client,
    ):
        response = client.post(
            "/claims/evidence",
            files={
                "file": (
                    "claim_evidence.pdf",
                    io.BytesIO(b"test content"),
                    "application/pdf",
                )
            },
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 201


class TestDeleteClaimEvidenceAuth:
    def test_204_delete_claim_evidence_when_provider_claims_user_token(
        self,
        session,
        client,
    ):
        claim_evidence = ClaimEvidence(
            sds_file_name="stored-claim-evidence_abc123.pdf",
            file_name="claim_evidence.pdf",
        )
        session.add(claim_evidence)
        session.commit()
        session.refresh(claim_evidence)

        response = client.delete(
            f"/claims/{claim_evidence.claim_evidence_id}",
            headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
        )

        assert response.status_code == 204


class TestListProviderOfficesAuth:
    @pytest.mark.parametrize(
        "provider_token",
        [Role.PROVIDER_APPLICATION_USER.value, Role.PROVIDER_CLAIMS_USER.value],
    )
    def test_200_list_provider_offices_returns_200_when_provider_token(
        self, client, provider_token
    ):
        override_provider_details_port_with_provider_offices()

        response = client.get(
            "/applications/provider-offices/123",
            headers={"Authorization": f"Bearer {provider_token}"},
        )

        assert response.status_code == 200


class TestDeleteCoronersLetterAuth:
    def test_204_delete_coroners_letter_when_provider_application_user_token(
        self,
        session,
        client,
    ):
        coroners_letter = CoronersLetter(
            sds_file_name="stored-file_abc123.pdf",
            file_name="coroners_letter.pdf",
        )
        session.add(coroners_letter)
        session.commit()
        session.refresh(coroners_letter)

        response = client.delete(
            f"/applications/coroners-letter/{coroners_letter.coroners_letter_id}",
            headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
        )

        assert response.status_code == 204


def test_200_retrieve_coroners_letter_returns_200_when_caseworker_token(
    session, client
):
    application = session.exec(select(Application)).first()
    coroners_letter = CoronersLetter(
        sds_file_name="stored-file_abc123.pdf",
        file_name="coroners_letter.pdf",
    )
    session.add(coroners_letter)
    session.commit()
    session.refresh(coroners_letter)

    application.coroners_letter_id = coroners_letter.coroners_letter_id
    session.add(application)
    session.commit()

    response = client.get(
        f"/applications/{application.laa_reference}/coroners-letter",
        headers={
            "Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"
        },  # TODO: Add E2E tests for get coroners letter endpoint
    )

    assert response.status_code == 200


def test_200_retrieve_claim_evidence_returns_200_when_caseworker_token(session, client):
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.pdf",
        file_name="claim_evidence.pdf",
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": "Bearer Caseworker No Role"},
    )

    assert response.status_code == 200


def test_200_retrieve_claim_evidence_returns_200_when_provider_claims_token(
    session, client
):
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.pdf",
        file_name="claim_evidence.pdf",
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)

    response = client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
