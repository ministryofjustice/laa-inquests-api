import io
import uuid
from unittest.mock import MagicMock

from app import api
from app.models.claim.index import ClaimEvidence
from app.routers.claims import get_sds_port
from tests.helpers.entra_auth import override_entra_auth_app_roles


def _upload_evidence_and_get_id(client, auth_token):
    upload_response = client.post(
        "/claims/evidence",
        files={
            "file": (
                "claim_evidence.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert upload_response.status_code == 201
    return upload_response.json()["claimEvidenceId"]


def test_204_delete_claim_evidence(client, auth_token):
    claim_evidence_id = _upload_evidence_and_get_id(client, auth_token)

    delete_response = client.delete(
        f"/claims/{claim_evidence_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert delete_response.status_code == 204


def test_404_delete_claim_evidence_when_unknown_id(client, auth_token):
    delete_response = client.delete(
        "/claims/00000000-0000-0000-0000-000000000001",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert delete_response.status_code == 404


def test_500_delete_claim_evidence_when_sds_fails(client, auth_token):
    claim_evidence_id = _upload_evidence_and_get_id(client, auth_token)

    def get_sds_port_override_with_delete_error():
        mock_sds = MagicMock()
        mock_sds.delete_claim_evidence.side_effect = Exception("SDS delete failed")
        return mock_sds

    api.dependency_overrides[get_sds_port] = get_sds_port_override_with_delete_error

    delete_response = client.delete(
        f"/claims/{claim_evidence_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert delete_response.status_code == 500


class TestDeleteClaimEvidenceRbac:
    def test_204_delete_claim_evidence_with_provider_claims_user_app_role(
        self, session, client, auth_token
    ):
        override_entra_auth_app_roles({"Inquests - Provider Claims User"})
        claim_evidence = ClaimEvidence(
            sds_file_name="stored-claim-evidence_abc123.pdf",
            file_name="claim_evidence.pdf",
        )
        session.add(claim_evidence)
        session.commit()
        session.refresh(claim_evidence)

        response = client.delete(
            f"/claims/{claim_evidence.claim_evidence_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 204

    def test_403_delete_claim_evidence_with_app_role_missing_delete_permission(
        self, client, auth_token
    ):
        override_entra_auth_app_roles({"Inquests - Provider Application User"})

        response = client.delete(
            f"/claims/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 403

    def test_403_delete_claim_evidence_with_unmapped_app_role(self, client, auth_token):
        override_entra_auth_app_roles({"Some Unknown Role"})

        response = client.delete(
            f"/claims/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 403
