import io
import json
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import api
from app.auth.rbac import Role
from app.models.application.index import CoronersLetter
from app.ports.sds_port import SdsPort
from app.routers.applications import get_sds_port
from app.routers.dependencies import get_current_provider_office_codes
from app.use_cases.exceptions import CoronersLetterDeleteError


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


@pytest.mark.parametrize("office_id", ["0U651L", "1A234B"])
def test_204_delete_coroners_letter_owned_by_any_of_providers_offices(
    client: TestClient, session: Session, office_id: str
) -> None:
    letter = CoronersLetter(
        sds_file_name="test-coroners-letter",
        file_name="coroners_letter.pdf",
        office_id=office_id,
    )
    session.add(letter)
    session.commit()
    letter_id = letter.coroners_letter_id
    api.dependency_overrides[get_current_provider_office_codes] = lambda: frozenset(
        {"0U651L", "1A234B"}
    )
    mock_sds = MagicMock(spec=SdsPort)
    api.dependency_overrides[get_sds_port] = lambda: mock_sds

    response = client.delete(
        f"/applications/coroners-letter/{letter_id}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"},
    )

    assert response.status_code == 204
    assert response.content == b""
    assert session.get(CoronersLetter, letter_id) is None
    mock_sds.delete_coroners_letter.assert_called_once_with("test-coroners-letter")


def test_404_delete_coroners_letter_from_another_office_fails(
    client: TestClient, session: Session
) -> None:
    letter = CoronersLetter(
        sds_file_name="other-office-coroners-letter",
        file_name="coroners_letter.pdf",
        office_id="1A234B",
    )
    session.add(letter)
    session.commit()
    letter_id = letter.coroners_letter_id
    mock_sds = MagicMock(spec=SdsPort)
    api.dependency_overrides[get_sds_port] = lambda: mock_sds
    headers = {"Authorization": f"Bearer {Role.PROVIDER_APPLICATION_USER.value}"}

    unknown_response = client.delete(
        f"/applications/coroners-letter/{uuid.uuid4()}", headers=headers
    )
    response = client.delete(
        f"/applications/coroners-letter/{letter_id}", headers=headers
    )

    assert response.status_code == unknown_response.status_code == 404
    assert (
        response.json()
        == unknown_response.json()
        == {"detail": "Coroners letter not found"}
    )
    session.expire_all()
    stored_letter = session.get(CoronersLetter, letter_id)
    assert stored_letter is not None
    assert stored_letter.office_id == "1A234B"
    mock_sds.delete_coroners_letter.assert_not_called()


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
