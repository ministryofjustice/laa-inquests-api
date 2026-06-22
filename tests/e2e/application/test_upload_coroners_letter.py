import io


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
    assert "fileId" in body
    assert isinstance(body["fileId"], str)


def test_422_upload_coroners_letter_with_no_file(client, auth_token):
    response = client.post(
        "/applications/upload-coroners-letter",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 422
