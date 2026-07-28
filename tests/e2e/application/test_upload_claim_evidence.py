import io
import uuid
from unittest.mock import MagicMock

from app import api
from app.routers.applications import get_sds_port


def is_valid_uuid(val):
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False


def test_201_upload_claim_evidence_returns_claim_evidence_id(client, auth_token):
    response = client.post(
        "/applications/1000/claim/upload-evidence",
        files={
            "file": (
                "claim_evidence.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "claimEvidenceId" in body
    assert is_valid_uuid(body["claimEvidenceId"])


def test_422_upload_claim_evidence_with_no_file(client, auth_token):
    response = client.post(
        "/applications/1000/claim/upload-evidence",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 422


def test_422_upload_claim_evidence_with_failed_virus_check(client, auth_token):
    def get_sds_port_override_with_failed_virus_check():
        mock_sds = MagicMock()
        mock_sds.virus_check_claim_evidence.return_value = False
        return mock_sds

    api.dependency_overrides[get_sds_port] = (
        get_sds_port_override_with_failed_virus_check
    )

    response = client.post(
        "/applications/1000/claim/upload-evidence",
        files={
            "file": (
                "claim_evidence.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 422


def test_500_upload_claim_evidence_with_sds_server_error(client, auth_token):
    def get_sds_port_override_with_server_error():
        mock_sds = MagicMock()
        mock_sds.virus_check_claim_evidence.side_effect = Exception("SDS server error")
        return mock_sds

    api.dependency_overrides[get_sds_port] = get_sds_port_override_with_server_error

    response = client.post(
        "/applications/1000/claim/upload-evidence",
        files={
            "file": (
                "claim_evidence.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 500


def test_201_upload_claim_evidence_allows_multiple_uploads(client, auth_token):
    first = client.post(
        "/applications/1000/claim/upload-evidence",
        files={
            "file": (
                "claim_evidence_1.pdf",
                io.BytesIO(b"test content 1"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    second = client.post(
        "/applications/1000/claim/upload-evidence",
        files={
            "file": (
                "claim_evidence_2.pdf",
                io.BytesIO(b"test content 2"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert first.status_code == 201
    assert second.status_code == 201

    first_body = first.json()
    second_body = second.json()

    assert "claimEvidenceId" in first_body
    assert "claimEvidenceId" in second_body
    assert first_body["claimEvidenceId"] != second_body["claimEvidenceId"]
