import io
import json
import uuid
from unittest.mock import MagicMock

from app import api
from app.auth.rbac import Permission, Role, get_current_user_permissions
from app.routers.applications import CoronersLetterUploadError, get_sds_port


def is_valid_uuid(val):
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False


class TestUploadCoronersLetter:
    def test_201_upload_coroners_letter_returns_coroners_letter_id(self, client):
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
        body = response.json()
        assert "coronersLetterId" in body
        assert is_valid_uuid(body["coronersLetterId"])

    def test_422_upload_coroners_letter_with_no_file(self, client):
        response = client.post(
            "/applications/upload-coroners-letter",
            headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
        )
        assert response.status_code == 422

    def test_422_upload_coroners_letter_with_failed_virus_check(self, client):
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
            headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
        )
        assert response.status_code == 422

    def test_500_upload_coroners_letter_with_sds_server_error(self, client):
        def get_sds_port_override_with_server_error():
            mock_sds = MagicMock()
            mock_sds.virus_check_coroners_letter.side_effect = (
                CoronersLetterUploadError("SDS server error")
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
            headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
        )
        assert response.status_code == 500


PII_FILE_NAME = "Jane Doe passport.pdf"


class TestUploadCoronersLetterSentryPii:
    def _upload(self, client):
        return client.post(
            "/applications/upload-coroners-letter",
            files={
                "file": (PII_FILE_NAME, io.BytesIO(b"test content"), "application/pdf")
            },
            headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
        )

    def test_500_virus_check_failure_does_not_send_file_name_to_sentry(
        self, client, captured_sentry_events
    ):
        mock_sds = MagicMock()
        mock_sds.virus_check_coroners_letter.side_effect = CoronersLetterUploadError(
            "Failed to perform virus check due to a network error: "
            "https://sds/virus_check_file?file_key=Jane+Doe+passport.pdf"
        )
        api.dependency_overrides[get_sds_port] = lambda: mock_sds

        response = self._upload(client)

        assert response.status_code == 500
        assert len(captured_sentry_events) >= 1
        assert "Jane" not in json.dumps(captured_sentry_events)
        assert "passport" not in json.dumps(captured_sentry_events)

    def test_500_upload_not_successful_does_not_send_file_name_to_sentry(
        self, client, captured_sentry_events
    ):
        mock_sds = MagicMock()
        mock_sds.virus_check_coroners_letter.return_value = True
        mock_sds.save_coroners_letter.return_value.status = "FAILED"
        api.dependency_overrides[get_sds_port] = lambda: mock_sds

        response = self._upload(client)

        assert response.status_code == 500
        assert len(captured_sentry_events) >= 1
        assert "Jane" not in json.dumps(captured_sentry_events)
        assert "passport" not in json.dumps(captured_sentry_events)


class TestUploadCoronersLetterRbac:
    def test_201_upload_coroners_letter_with_provider_application_user_app_role(
        self, client
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

    def test_201_upload_coroners_letter_with_permission_override(self, client):
        def get_current_user_permissions_override():
            return {Permission.APPLICATION_CREATE}

        api.dependency_overrides[get_current_user_permissions] = (
            get_current_user_permissions_override
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
            headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
        )
        assert response.status_code == 201
