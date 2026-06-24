import io
import uuid


def is_valid_uuid(val):
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False


def test_201_upload_coroners_letter_returns_file_id(client, auth_token):
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
