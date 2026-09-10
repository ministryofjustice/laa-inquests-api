import io
import uuid

import pytest
from sqlmodel import select

from app.models.application.enums import MeritsDecision
from app.models.application.index import Application, CoronersLetter
from app.models.claim.index import ClaimEvidence
from tests.helpers.application_payloads import create_application_payload
from tests.helpers.entra_auth import (
    override_entra_auth_port_with_provider_no_role_token,
)
from tests.helpers.provider_details import (
    override_provider_details_port_with_provider_offices,
)


def test_200_read_all_applications_returns_200_when_valid_entra_token(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 200


def test_401_read_all_applications_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.get("/applications")

    assert response.status_code == 401


def test_401_read_all_applications_returns_401_when_bearer_token_is_invalid(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "provider_token",
    ["valid-provider-application-user-token", "valid-provider-claims-user-token"],
)
def test_403_read_all_applications_returns_403_when_scope_is_not_caseworker(
    entra_auth_client, provider_token
):
    response = entra_auth_client.get(
        "/applications",
        headers={"Authorization": f"Bearer {provider_token}"},
    )

    assert response.status_code == 403


def test_200_read_application_by_id_returns_200_when_caseworker_token(
    session,
    entra_auth_client,
):
    application = session.exec(select(Application)).first()
    response = entra_auth_client.get(
        f"/applications/{application.laa_reference}",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "provider_token",
    ["valid-provider-application-user-token", "valid-provider-claims-user-token"],
)
def test_403_read_application_by_id_returns_403_when_provider_token(
    entra_auth_client, provider_token
):
    response = entra_auth_client.get(
        "/applications/1",
        headers={"Authorization": f"Bearer {provider_token}"},
    )

    assert response.status_code == 403


def test_201_create_application_returns_201_when_provider_application_user_token(
    entra_auth_client,
):
    response = entra_auth_client.post(
        "/applications",
        json=create_application_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-provider-application-user-token",
        },
    )

    assert response.status_code == 201


def test_403_create_application_returns_403_when_provider_token_missing_permission(
    entra_auth_client,
):
    response = entra_auth_client.post(
        "/applications",
        json=create_application_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-provider-claims-user-token",
        },
    )

    assert response.status_code == 403


def test_403_create_application_returns_403_when_caseworker_token(
    entra_auth_client,
):
    response = entra_auth_client.post(
        "/applications",
        json=create_application_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-caseworker-entra-token",
        },
    )

    assert response.status_code == 403


def test_201_upload_coroners_letter_returns_201_when_provider_application_user_token(
    entra_auth_client,
):
    response = entra_auth_client.post(
        "/applications/upload-coroners-letter",
        files={
            "file": (
                "coroners_letter.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": "Bearer valid-provider-application-user-token"},
    )

    assert response.status_code == 201


def test_403_upload_coroners_letter_returns_403_when_provider_token_missing_permission(
    entra_auth_client,
):
    response = entra_auth_client.post(
        "/applications/upload-coroners-letter",
        files={
            "file": (
                "coroners_letter.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": "Bearer valid-provider-claims-user-token"},
    )

    assert response.status_code == 403


def test_403_upload_coroners_letter_returns_403_when_caseworker_token(
    entra_auth_client,
):
    response = entra_auth_client.post(
        "/applications/upload-coroners-letter",
        files={
            "file": (
                "coroners_letter.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 403


def test_204_refuse_decision_returns_204_when_caseworker_token(
    session,
    entra_auth_client,
):
    application = session.exec(select(Application)).first()
    response = entra_auth_client.patch(
        f"/applications/{application.laa_reference}/refuse-decision",
        json={
            "meritsDecision": MeritsDecision.REFUSED,
            "reasonForRefusal": "NOT_IN_SCOPE",
            "justification": "The matter does not meet scope requirements.",
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-caseworker-entra-token",
        },
    )

    assert response.status_code == 204


@pytest.mark.parametrize(
    "provider_token",
    ["valid-provider-application-user-token", "valid-provider-claims-user-token"],
)
def test_403_refuse_decision_returns_403_when_provider_token(
    entra_auth_client, provider_token
):
    response = entra_auth_client.patch(
        "/applications/1/refuse-decision",
        json={
            "meritsDecision": MeritsDecision.REFUSED,
            "reasonForRefusal": "NOT_IN_SCOPE",
            "justification": "The matter does not meet scope requirements.",
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {provider_token}",
        },
    )

    assert response.status_code == 403


def test_204_grant_decision_returns_204_when_caseworker_token(
    session,
    entra_auth_client,
):
    application = session.exec(select(Application)).first()
    response = entra_auth_client.patch(
        f"/applications/{application.laa_reference}/grant-decision",
        json={"certificateStartDate": "2000-01-01"},
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-caseworker-entra-token",
        },
    )

    assert response.status_code == 204


@pytest.mark.parametrize(
    "provider_token",
    ["valid-provider-application-user-token", "valid-provider-claims-user-token"],
)
def test_403_grant_decision_returns_403_when_provider_token(
    entra_auth_client, provider_token
):
    response = entra_auth_client.patch(
        "/applications/1/grant-decision",
        json={"certificateStartDate": "2000-01-01"},
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {provider_token}",
        },
    )

    assert response.status_code == 403


class TestSearchApplicationAuth:
    def test_200_search_application_returns_200_when_provider_claims_user_token(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.get(
            "/applications/search",
            params={"laa_reference": "1"},
            headers={"Authorization": "Bearer valid-provider-claims-user-token"},
        )

        assert response.status_code == 200

    def test_403_search_application_returns_403_when_provider_application_user_token(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.get(
            "/applications/search",
            params={"laa_reference": "1"},
            headers={"Authorization": "Bearer valid-provider-application-user-token"},
        )

        assert response.status_code == 403

    def test_403_search_application_returns_403_when_provider_token_missing_permission(
        self,
        entra_auth_client,
    ):
        override_entra_auth_port_with_provider_no_role_token()

        response = entra_auth_client.get(
            "/applications/search",
            params={"laa_reference": "1"},
            headers={"Authorization": "Bearer valid-provider-no-role-token"},
        )

        assert response.status_code == 403

    def test_401_search_application_returns_401_when_no_authorization_header(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.get(
            "/applications/search",
            params={"laa_reference": "1"},
        )

        assert response.status_code == 401

    def test_401_search_application_returns_401_when_bearer_token_is_invalid(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.get(
            "/applications/search",
            params={"laa_reference": "1"},
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401

    def test_403_search_application_returns_403_when_caseworker_token(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.get(
            "/applications/search",
            params={"laa_reference": "1"},
            headers={"Authorization": "Bearer valid-caseworker-entra-token"},
        )

        assert response.status_code == 403


class TestUploadClaimEvidenceAuth:
    def test_201_upload_claim_evidence_when_provider_claims_user_token(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.post(
            "/claims/evidence",
            files={
                "file": (
                    "claim_evidence.pdf",
                    io.BytesIO(b"test content"),
                    "application/pdf",
                )
            },
            headers={"Authorization": "Bearer valid-provider-claims-user-token"},
        )

        assert response.status_code == 201

    def test_403_upload_claim_evidence_when_provider_application_user_token(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.post(
            "/claims/evidence",
            files={
                "file": (
                    "claim_evidence.pdf",
                    io.BytesIO(b"test content"),
                    "application/pdf",
                )
            },
            headers={"Authorization": "Bearer valid-provider-application-user-token"},
        )

        assert response.status_code == 403

    def test_403_upload_claim_evidence_when_provider_token_missing_permission(
        self,
        entra_auth_client,
    ):
        override_entra_auth_port_with_provider_no_role_token()

        response = entra_auth_client.post(
            "/claims/evidence",
            files={
                "file": (
                    "claim_evidence.pdf",
                    io.BytesIO(b"test content"),
                    "application/pdf",
                )
            },
            headers={"Authorization": "Bearer valid-provider-no-role-token"},
        )

        assert response.status_code == 403

    def test_403_upload_claim_evidence_when_caseworker_token(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.post(
            "/claims/evidence",
            files={
                "file": (
                    "claim_evidence.pdf",
                    io.BytesIO(b"test content"),
                    "application/pdf",
                )
            },
            headers={"Authorization": "Bearer valid-caseworker-entra-token"},
        )

        assert response.status_code == 403

    def test_401_upload_claim_evidence_when_no_authorization_header(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.post(
            "/claims/evidence",
            files={
                "file": (
                    "claim_evidence.pdf",
                    io.BytesIO(b"test content"),
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 401

    def test_401_upload_claim_evidence_when_bearer_token_is_invalid(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.post(
            "/claims/evidence",
            files={
                "file": (
                    "claim_evidence.pdf",
                    io.BytesIO(b"test content"),
                    "application/pdf",
                )
            },
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401


class TestListProviderOfficesAuth:
    @pytest.mark.parametrize(
        "provider_token",
        ["valid-provider-application-user-token", "valid-provider-claims-user-token"],
    )
    def test_200_list_provider_offices_returns_200_when_provider_token(
        self, entra_auth_client, provider_token
    ):
        override_provider_details_port_with_provider_offices()

        response = entra_auth_client.get(
            "/applications/provider-offices/123",
            headers={"Authorization": f"Bearer {provider_token}"},
        )

        assert response.status_code == 200

    def test_401_list_provider_offices_returns_401_when_no_authorization_header(
        self,
        entra_auth_client,
    ):
        override_provider_details_port_with_provider_offices()

        response = entra_auth_client.get("/applications/provider-offices/123")

        assert response.status_code == 401

    def test_401_list_provider_offices_returns_401_when_bearer_token_is_invalid(
        self,
        entra_auth_client,
    ):
        override_provider_details_port_with_provider_offices()

        response = entra_auth_client.get(
            "/applications/provider-offices/123",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401

    def test_403_list_provider_offices_returns_403_when_caseworker_token(
        self,
        entra_auth_client,
    ):
        override_provider_details_port_with_provider_offices()

        response = entra_auth_client.get(
            "/applications/provider-offices/123",
            headers={"Authorization": "Bearer valid-caseworker-entra-token"},
        )

        assert response.status_code == 403

    def test_403_list_provider_offices_returns_403_when_provider_token_missing_permission(
        self,
        entra_auth_client,
    ):
        override_provider_details_port_with_provider_offices()
        override_entra_auth_port_with_provider_no_role_token()

        response = entra_auth_client.get(
            "/applications/provider-offices/123",
            headers={"Authorization": "Bearer valid-provider-no-role-token"},
        )

        assert response.status_code == 403


class TestDeleteCoronersLetterAuth:
    def test_204_delete_coroners_letter_when_provider_application_user_token(
        self,
        session,
        entra_auth_client,
    ):
        coroners_letter = CoronersLetter(
            sds_file_name="stored-file_abc123.pdf",
            file_name="coroners_letter.pdf",
        )
        session.add(coroners_letter)
        session.commit()
        session.refresh(coroners_letter)

        response = entra_auth_client.delete(
            f"/applications/coroners-letter/{coroners_letter.coroners_letter_id}",
            headers={"Authorization": "Bearer valid-provider-application-user-token"},
        )

        assert response.status_code == 204

    def test_403_delete_coroners_letter_when_provider_token_missing_permission(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.delete(
            f"/applications/coroners-letter/{uuid.uuid4()}",
            headers={"Authorization": "Bearer valid-provider-claims-user-token"},
        )

        assert response.status_code == 403

    def test_403_delete_coroners_letter_when_caseworker_token(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.delete(
            f"/applications/coroners-letter/{uuid.uuid4()}",
            headers={"Authorization": "Bearer valid-caseworker-entra-token"},
        )

        assert response.status_code == 403

    def test_401_delete_coroners_letter_returns_401_when_no_authorization_header(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.delete(
            f"/applications/coroners-letter/{uuid.uuid4()}"
        )

        assert response.status_code == 401

    def test_401_delete_coroners_letter_when_bearer_token_is_invalid(
        self,
        entra_auth_client,
    ):
        response = entra_auth_client.delete(
            f"/applications/coroners-letter/{uuid.uuid4()}",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401


def test_200_retrieve_coroners_letter_returns_200_when_caseworker_token(
    session, entra_auth_client
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

    response = entra_auth_client.get(
        f"/applications/{application.laa_reference}/coroners-letter",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 200


def test_401_retrieve_coroners_letter_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.get("/applications/1/coroners-letter")

    assert response.status_code == 401


def test_401_retrieve_coroners_letter_returns_401_when_bearer_token_is_invalid(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications/1/coroners-letter",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "provider_token",
    ["valid-provider-application-user-token", "valid-provider-claims-user-token"],
)
def test_403_retrieve_coroners_letter_returns_403_when_provider_token(
    entra_auth_client, provider_token
):
    response = entra_auth_client.get(
        "/applications/1/coroners-letter",
        headers={"Authorization": f"Bearer {provider_token}"},
    )

    assert response.status_code == 403


def test_200_list_public_bodies_returns_200_when_caseworker_token(entra_auth_client):
    response = entra_auth_client.get(
        "/applications/public-bodies",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "provider_token",
    ["valid-provider-application-user-token", "valid-provider-claims-user-token"],
)
def test_200_list_public_bodies_returns_200_when_application_provider_token(
    entra_auth_client, provider_token
):
    response = entra_auth_client.get(
        "/applications/public-bodies",
        headers={"Authorization": f"Bearer {provider_token}"},
    )

    assert response.status_code == 200


def test_401_list_public_bodies_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.get("/applications/public-bodies")

    assert response.status_code == 401


def test_401_list_public_bodies_returns_401_when_bearer_token_is_invalid(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications/public-bodies",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_200_retrieve_claim_evidence_returns_200_when_caseworker_token(
    session, entra_auth_client
):
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.pdf",
        file_name="claim_evidence.pdf",
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)

    response = entra_auth_client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 200


def test_200_retrieve_claim_evidence_returns_200_when_provider_claims_token(
    session, entra_auth_client
):
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.pdf",
        file_name="claim_evidence.pdf",
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)

    response = entra_auth_client.get(
        f"/claims/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": "Bearer valid-provider-claims-user-token"},
    )

    assert response.status_code == 200


def test_401_retrieve_claim_evidence_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.get(f"/claims/{uuid.uuid4()}")

    assert response.status_code == 401


def test_401_retrieve_claim_evidence_returns_401_when_bearer_token_is_invalid(
    entra_auth_client,
):
    response = entra_auth_client.get(
        f"/claims/{uuid.uuid4()}",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_401_reject_claim_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.patch(
        "/applications/1/claims/1/reject",
        json={"justification": "Claim rejected following manual assessment."},
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "provider_token",
    ["valid-provider-application-user-token", "valid-provider-claims-user-token"],
)
def test_403_reject_claim_returns_403_when_provider_token(
    entra_auth_client, provider_token
):
    response = entra_auth_client.patch(
        "/applications/1/claims/1/reject",
        json={"justification": "Claim rejected following manual assessment."},
        headers={"Authorization": f"Bearer {provider_token}"},
    )

    assert response.status_code == 403
