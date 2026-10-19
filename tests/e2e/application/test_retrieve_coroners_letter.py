import json
from unittest.mock import MagicMock

from sqlmodel import select

from app import api
from app.auth.rbac import Role
from app.models.application.index import Application
from app.routers.applications import get_sds_port
from app.use_cases.exceptions import SDSLetterRetrievalError


def test_200_retrieve_coroners_letter(session, client):
    application = session.exec(select(Application)).first()

    response = client.get(
        f"/applications/{application.laa_reference}/coroners-letter",
        headers={"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"  # Set in SDS mock in client fixture


def test_500_retrieve_coroners_letter_failure_does_not_send_sds_file_key_to_sentry(
    session, client, captured_sentry_events
):
    application = session.exec(select(Application)).first()
    mock_sds = MagicMock()
    mock_sds.retrieve_coroners_letter.side_effect = SDSLetterRetrievalError(
        "SDS returned 404 while retrieving coroner's letter for file key Jane_Doe_passport_3f2b8c1e.pdf"
    )
    api.dependency_overrides[get_sds_port] = lambda: mock_sds

    response = client.get(
        f"/applications/{application.laa_reference}/coroners-letter",
        headers={"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"},
    )

    assert response.status_code == 500
    assert len(captured_sentry_events) >= 1
    assert "Jane" not in json.dumps(captured_sentry_events)
    assert "passport" not in json.dumps(captured_sentry_events)
