import io
import json
import uuid
from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from app import api
from app.auth.rbac import Permission, Role, get_current_user_permissions
from app.models.application.index import CoronersLetter
from app.routers.applications import get_sds_port
from app.routers.dependencies import get_entra_auth_port
from app.use_cases.exceptions import CoronersLetterDeleteError
from tests.e2e.factories import create_application_in_db


def _upload_coroners_letter_and_get_id(client, auth_token):
    upload_response = client.post(
        "/applications/upload-coroners-letter",
        data={"office_id": "0U651L"},
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


def test_204_delete_coroners_letter(client):
    coroners_letter_id = _upload_coroners_letter_and_get_id(
        client, Role.PROVIDER_APPLICATION_USER.value
    )

    delete_response = client.delete(
        f"/applications/coroners-letter/{coroners_letter_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
    )

    assert delete_response.status_code == 204


def test_404_delete_coroners_letter_when_unknown_id(client):
    delete_response = client.delete(
        "/applications/coroners-letter/00000000-0000-0000-0000-000000000001",
        headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
    )

    assert delete_response.status_code == 404


def test_500_delete_coroners_letter_when_sds_fails(client):
    coroners_letter_id = _upload_coroners_letter_and_get_id(
        client, Role.PROVIDER_APPLICATION_USER.value
    )

    def get_sds_port_override_with_delete_error():
        mock_sds = MagicMock()
        mock_sds.delete_coroners_letter.side_effect = Exception("SDS delete failed")
        return mock_sds

    api.dependency_overrides[get_sds_port] = get_sds_port_override_with_delete_error

    delete_response = client.delete(
        f"/applications/coroners-letter/{coroners_letter_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
    )

    assert delete_response.status_code == 500


class TestDeleteCoronersLetterOfficeIdCheck:
    @pytest.fixture
    def sds_files(self, client):
        files = {"stored-file-key": b"file bytes"}
        sds = MagicMock()
        sds.delete_coroners_letter.side_effect = lambda key: files.pop(key)
        api.dependency_overrides[get_sds_port] = lambda: sds
        return files, sds

    @staticmethod
    def _set_token_offices(office_codes):
        auth = api.dependency_overrides[get_entra_auth_port]()
        verify_token = auth.verify_token.side_effect

        def verify_with_offices(role, required_scopes=None):
            user = verify_token(role, required_scopes)
            return replace(user, office_codes=frozenset(office_codes))

        auth.verify_token.side_effect = verify_with_offices
        api.dependency_overrides[get_entra_auth_port] = lambda: auth

    @pytest.mark.parametrize(
        ("file_office", "token_offices"),
        [
            ("0U651L", {"0U651L"}),
            ("002", {"0U651L", "002"}),
        ],
        ids=["own-office", "second-office-in-token"],
    )
    def test_204_deletes_letter_when_its_office_id_is_in_the_token(
        self, session, client, sds_files, file_office, token_offices
    ):
        self._set_token_offices(token_offices)
        letter = CoronersLetter(
            sds_file_name="stored-file-key",
            file_name="letter.pdf",
            office_id=file_office,
        )
        session.add(letter)
        session.commit()
        letter_id = letter.coroners_letter_id
        files, sds = sds_files

        response = client.delete(
            f"/applications/coroners-letter/{letter_id}",
            headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
        )

        assert response.status_code == 204
        assert session.get(CoronersLetter, letter_id) is None
        assert "stored-file-key" not in files
        sds.delete_coroners_letter.assert_called_once_with("stored-file-key")

    @pytest.mark.parametrize(
        ("firm_code", "file_office"),
        [("0A123B", "002"), ("ZZ999Z", "003")],
        ids=["same-firm-different-office", "different-firm"],
    )
    def test_404_does_not_delete_letter_when_its_office_id_is_not_in_the_token(
        self, session, client, sds_files, firm_code, file_office
    ):
        self._set_token_offices({"0U651L"})
        letter = CoronersLetter(
            sds_file_name="stored-file-key",
            file_name="letter.pdf",
            office_id=file_office,
        )
        session.add(letter)
        session.commit()
        letter_id = letter.coroners_letter_id
        create_application_in_db(
            session,
            provider_overrides={"firm_code": firm_code, "office_id": file_office},
            coroners_letter_id=letter_id,
        )
        files, sds = sds_files
        headers = {"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"}

        unknown_response = client.delete(
            f"/applications/coroners-letter/{uuid.uuid4()}", headers=headers
        )
        response = client.delete(
            f"/applications/coroners-letter/{letter_id}", headers=headers
        )

        assert response.status_code == unknown_response.status_code == 404
        assert response.json() == unknown_response.json()
        session.expire_all()
        assert session.get(CoronersLetter, letter_id) is not None
        assert files["stored-file-key"] == b"file bytes"
        sds.delete_coroners_letter.assert_not_called()

    def test_403_non_provider_cannot_delete_letter_even_with_create_permission(
        self, session, client, sds_files
    ):
        letter = CoronersLetter(
            sds_file_name="stored-file-key",
            file_name="letter.pdf",
            office_id="0U651L",
        )
        session.add(letter)
        session.commit()
        letter_id = letter.coroners_letter_id
        files, sds = sds_files
        api.dependency_overrides[get_current_user_permissions] = lambda: {
            Permission.APPLICATION_CREATE
        }

        response = client.delete(
            f"/applications/coroners-letter/{letter_id}",
            headers={"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"},
        )

        assert response.status_code == 403
        session.expire_all()
        assert session.get(CoronersLetter, letter_id) is not None
        assert files["stored-file-key"] == b"file bytes"
        sds.delete_coroners_letter.assert_not_called()


def test_500_delete_coroners_letter_failure_does_not_send_sds_file_key_to_sentry(
    client, captured_sentry_events
):
    coroners_letter_id = _upload_coroners_letter_and_get_id(
        client, Role.PROVIDER_APPLICATION_USER.value
    )
    mock_sds = MagicMock()
    mock_sds.delete_coroners_letter.side_effect = CoronersLetterDeleteError(
        "SDS returned 500 while deleting coroners letter for file key Jane_Doe_passport_3f2b8c1e.pdf"
    )
    api.dependency_overrides[get_sds_port] = lambda: mock_sds

    response = client.delete(
        f"/applications/coroners-letter/{coroners_letter_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
    )

    assert response.status_code == 500
    assert len(captured_sentry_events) >= 1
    assert "Jane" not in json.dumps(captured_sentry_events)
    assert "passport" not in json.dumps(captured_sentry_events)
