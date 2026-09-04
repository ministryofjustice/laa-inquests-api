import io
from unittest.mock import MagicMock

from app import api
from app.routers.applications import get_sds_port


def _upload_coroners_letter_and_get_id(client, auth_token):
    upload_response = client.post(
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
    assert upload_response.status_code == 201
    return upload_response.json()["coronersLetterId"]


def test_204_delete_coroners_letter(client, auth_token):
    coroners_letter_id = _upload_coroners_letter_and_get_id(client, auth_token)

    delete_response = client.delete(
        f"/applications/coroners-letter/{coroners_letter_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert delete_response.status_code == 204


def test_404_delete_coroners_letter_when_unknown_id(client, auth_token):
    delete_response = client.delete(
        "/applications/coroners-letter/00000000-0000-0000-0000-000000000001",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert delete_response.status_code == 404


def test_500_delete_coroners_letter_when_sds_fails(client, auth_token):
    coroners_letter_id = _upload_coroners_letter_and_get_id(client, auth_token)

    def get_sds_port_override_with_delete_error():
        mock_sds = MagicMock()
        mock_sds.delete_coroners_letter.side_effect = Exception("SDS delete failed")
        return mock_sds

    api.dependency_overrides[get_sds_port] = get_sds_port_override_with_delete_error

    delete_response = client.delete(
        f"/applications/coroners-letter/{coroners_letter_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert delete_response.status_code == 500
