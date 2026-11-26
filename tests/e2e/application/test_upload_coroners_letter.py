import io
import json
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import api
from app.auth.rbac import Permission, Role, get_current_user_permissions
from app.models.application.index import CoronersLetter
from app.ports.sds_port import SdsPort
from app.routers.applications import CoronersLetterUploadError, get_sds_port
from app.routers.dependencies import get_current_provider_office_codes
from tests.helpers.multipart import UNSAFE_FILE_NAMES, raw_file_upload


def is_valid_uuid(val):
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False


class TestUploadCoronersLetter:
    def test_201_upload_coroners_letter_returns_coroners_letter_id(
        self, client: TestClient, session: Session
    ) -> None:
        api.dependency_overrides[get_current_provider_office_codes] = lambda: frozenset(
            {"0U651L", "1A234B"}
        )

        response = client.post(
            "/applications/upload-coroners-letter",
            data={"office_id": "1A234B"},
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
        assert body == {
            "coronersLetterId": body["coronersLetterId"],
            "coronersLetterFileName": "coroners_letter.pdf",
        }
        letter = session.get(CoronersLetter, uuid.UUID(body["coronersLetterId"]))
        assert letter is not None
        assert letter.office_id == "1A234B"

    @pytest.mark.parametrize(
        "office_id", [None, "", " ", "0U 651L", "0U651L<b>", "0U-651L", "A" * 21]
    )
    def test_422_upload_coroners_letter_requires_a_valid_office_id(
        self, client: TestClient, session: Session, office_id: str | None
    ) -> None:
        mock_sds = MagicMock(spec=SdsPort)
        api.dependency_overrides[get_sds_port] = lambda: mock_sds
        letter_ids_before = session.exec(
            select(CoronersLetter.coroners_letter_id)
        ).all()

        response = client.post(
            "/applications/upload-coroners-letter",
            data={} if office_id is None else {"office_id": office_id},
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
        assert any(
            error["loc"] == ["body", "office_id"] for error in response.json()["detail"]
        )
        mock_sds.virus_check_coroners_letter.assert_not_called()
        mock_sds.save_coroners_letter.assert_not_called()
        assert (
            session.exec(select(CoronersLetter.coroners_letter_id)).all()
            == letter_ids_before
        )

    def test_403_upload_coroners_letter_for_another_office_has_no_side_effects(
        self, client: TestClient, session: Session
    ) -> None:
        mock_sds = MagicMock(spec=SdsPort)
        api.dependency_overrides[get_sds_port] = lambda: mock_sds
        letter_ids_before = session.exec(
            select(CoronersLetter.coroners_letter_id)
        ).all()

        response = client.post(
            "/applications/upload-coroners-letter",
            data={"office_id": "1A234B"},
            files={
                "file": (
                    "coroners_letter.pdf",
                    io.BytesIO(b"test content"),
                    "application/pdf",
                )
            },
            headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
        )

        assert response.status_code == 403
        mock_sds.virus_check_coroners_letter.assert_not_called()
        mock_sds.save_coroners_letter.assert_not_called()
        assert (
            session.exec(select(CoronersLetter.coroners_letter_id)).all()
            == letter_ids_before
        )

    def test_422_upload_coroners_letter_with_no_file(self, client):
        response = client.post(
            "/applications/upload-coroners-letter",
            data={"office_id": "0U651L"},
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
            data={"office_id": "0U651L"},
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
            data={"office_id": "0U651L"},
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


class TestUploadCoronersLetterFileName:
    @pytest.mark.parametrize("file_name", UNSAFE_FILE_NAMES)
    def test_422_upload_coroners_letter_with_unsafe_file_name(
        self, client, session, file_name
    ):
        mock_sds = MagicMock()
        api.dependency_overrides[get_sds_port] = lambda: mock_sds
        letters_before = session.exec(select(CoronersLetter)).all()

        response = raw_file_upload(
            client,
            "/applications/upload-coroners-letter",
            file_name,
            {"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
            fields={"office_id": "0U651L"},
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "Invalid file name"
        mock_sds.virus_check_coroners_letter.assert_not_called()
        mock_sds.save_coroners_letter.assert_not_called()
        assert session.exec(select(CoronersLetter)).all() == letters_before

    @pytest.mark.parametrize(
        "file_name",
        [
            "coroners_letter.pdf",
            "Coroners letter (1).pdf",
            "Jane Doe - letter_2024.pdf",
        ],
    )
    def test_201_upload_coroners_letter_with_normal_file_name(self, client, file_name):
        response = raw_file_upload(
            client,
            "/applications/upload-coroners-letter",
            file_name,
            {"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
            fields={"office_id": "0U651L"},
        )

        assert response.status_code == 201
        assert response.json()["coronersLetterFileName"] == file_name


PII_FILE_NAME = "Jane Doe passport.pdf"


class TestUploadCoronersLetterSentryPii:
    def _upload(self, client):
        return client.post(
            "/applications/upload-coroners-letter",
            data={"office_id": "0U651L"},
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

    def test_422_virus_detected_sends_event_without_file_name_to_sentry(
        self, client, captured_sentry_events
    ):
        mock_sds = MagicMock()
        mock_sds.virus_check_coroners_letter.return_value = False
        api.dependency_overrides[get_sds_port] = lambda: mock_sds

        response = self._upload(client)

        assert response.status_code == 422
        assert len(captured_sentry_events) >= 1
        assert "Jane" not in json.dumps(captured_sentry_events)
        assert "passport" not in json.dumps(captured_sentry_events)


class TestUploadCoronersLetterRbac:
    def test_201_upload_coroners_letter_with_provider_application_user_app_role(
        self, client
    ):
        response = client.post(
            "/applications/upload-coroners-letter",
            data={"office_id": "0U651L"},
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
            data={"office_id": "0U651L"},
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
