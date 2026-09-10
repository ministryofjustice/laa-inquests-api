import io
import uuid
from unittest.mock import MagicMock

from app import api
from app.auth.rbac import Permission, get_current_user_permissions
from app.ports.entra_auth_port import AuthenticatedUser
from app.routers.applications import CoronersLetterUploadError, get_sds_port
from app.routers.dependencies import get_entra_auth_port


def is_valid_uuid(val):
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False


class TestUploadCoronersLetter:
    def test_201_upload_coroners_letter_returns_coroners_letter_id(
        self, client, auth_token
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 201
        body = response.json()
        assert "coronersLetterId" in body
        assert is_valid_uuid(body["coronersLetterId"])

    def test_422_upload_coroners_letter_with_no_file(self, client, auth_token):
        response = client.post(
            "/applications/upload-coroners-letter",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 422

    def test_422_upload_coroners_letter_with_failed_virus_check(
        self, client, auth_token
    ):
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

    def test_500_upload_coroners_letter_with_sds_server_error(self, client, auth_token):
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
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 500


def _override_entra_auth_app_roles(app_roles):
    def get_entra_auth_port_override():
        mock_auth = MagicMock()
        mock_auth.verify_token.return_value = AuthenticatedUser(
            firm_code="0A123B",
            scopes=frozenset({"User.Provider"}),
            app_roles=frozenset(app_roles),
            name="Test Name",
            entra_object_id="some-entra-object-id",
        )
        return mock_auth

    api.dependency_overrides[get_entra_auth_port] = get_entra_auth_port_override


class TestUploadCoronersLetterRbac:
    def test_201_upload_coroners_letter_with_provider_application_user_app_role(
        self, client, auth_token
    ):
        _override_entra_auth_app_roles({"Inquests - Provider Application User"})

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

    def test_403_upload_coroners_letter_with_app_role_missing_upload_permission(
        self, client, auth_token
    ):
        _override_entra_auth_app_roles({"Inquests - Provider Claims User"})

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
        assert response.status_code == 403

    def test_403_upload_coroners_letter_with_unmapped_app_role(
        self, client, auth_token
    ):
        _override_entra_auth_app_roles({"Some.UnknownRole"})

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
        assert response.status_code == 403

    def test_201_upload_coroners_letter_with_permission_override(
        self, client, auth_token
    ):
        def get_current_user_permissions_override():
            return {Permission.CORONERS_LETTER_UPLOAD}

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
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 201

    def test_403_upload_coroners_letter_with_empty_permission_override(
        self, client, auth_token
    ):
        def get_current_user_permissions_override():
            return set()

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
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 403
