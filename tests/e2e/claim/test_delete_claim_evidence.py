import io
from unittest.mock import MagicMock

from app import api
from app.routers.claims import get_sds_port


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
