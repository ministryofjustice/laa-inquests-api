import io
import uuid
from unittest.mock import MagicMock

from app import api
from app.routers.applications import CoronersLetterUploadError, get_sds_port


def is_valid_uuid(val):
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False


def test_201_upload_coroners_letter_returns_coroners_letter_id(client, auth_token):
    response = client.post(
        "/applications/upload-coroners-letter",
        files={
            "file": (
                "coroners_letter.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "coronersLetterId" in body
    assert is_valid_uuid(body["coronersLetterId"])


def test_422_upload_coroners_letter_with_no_file(client, auth_token):
    response = client.post(
        "/applications/upload-coroners-letter",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 422


def test_422_upload_coroners_letter_with_failed_virus_check(client, auth_token):
    def get_sds_port_override_with_failed_virus_check():
        mock_sds = MagicMock()
        mock_sds.virus_check_coroners_letter.return_value = False
        return mock_sds

    api.dependency_overrides[get_sds_port] = (
        get_sds_port_override_with_failed_virus_check
    )

    response = client.post(
        "/applications/upload-coroners-letter",
        files={
            "file": (
                "coroners_letter.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 422


def test_500_upload_coroners_letter_with_sds_server_error(client, auth_token):
    def get_sds_port_override_with_server_error():
        mock_sds = MagicMock()
        mock_sds.virus_check_coroners_letter.side_effect = CoronersLetterUploadError(
            "SDS server error"
        )
        return mock_sds

    api.dependency_overrides[get_sds_port] = get_sds_port_override_with_server_error

    response = client.post(
        "/applications/upload-coroners-letter",
        files={
            "file": (
                "coroners_letter.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 500
