from unittest.mock import MagicMock

from app import api
from app.models.application.index import Application, CoronersLetter
from app.routers.applications import get_sds_port
from app.use_cases.exceptions import (
    CoronersLetterNotFoundError,
    CoronersLetterRetrievalError,
    InvalidCoronersLetterDocumentIdError,
)
from sqlmodel import select


def _add_coroners_letter_to_application(session, sds_id: str, file_name: str) -> int:
    application = session.exec(select(Application)).first()

    coroners_letter = CoronersLetter(
        sds_id=sds_id,
        file_name=file_name,
    )
    session.add(coroners_letter)
    session.commit()
    session.refresh(coroners_letter)

    application.coroners_letter_id = coroners_letter.coroners_letter_id
    session.add(application)
    session.commit()

    return application.laa_reference


def test_200_retrieve_coroners_letter_returns_file_bytes(session, client, auth_token):
    laa_reference = _add_coroners_letter_to_application(
        session=session,
        sds_id="test-document_abc123.pdf",
        file_name="test-document.pdf",
    )

    response = client.get(
        f"/applications/{laa_reference}/coroners-letter",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="test-document.pdf"'
    )


def test_404_retrieve_coroners_letter_when_sds_document_not_found(
    session, client, auth_token
):
    laa_reference = _add_coroners_letter_to_application(
        session=session,
        sds_id="missing-document.pdf",
        file_name="test-document.pdf",
    )

    default_override = api.dependency_overrides[get_sds_port]

    def get_missing_file_sds_port_override():
        mock_sds = MagicMock()
        mock_sds.retrieve_coroners_letter.side_effect = CoronersLetterNotFoundError()
        return mock_sds

    api.dependency_overrides[get_sds_port] = get_missing_file_sds_port_override

    try:
        response = client.get(
            f"/applications/{laa_reference}/coroners-letter",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    finally:
        api.dependency_overrides[get_sds_port] = default_override

    assert response.status_code == 404
    assert response.json() == {"detail": "Coroners letter not found"}


def test_400_retrieve_coroners_letter_when_sds_document_id_is_invalid(
    session, client, auth_token
):
    laa_reference = _add_coroners_letter_to_application(
        session=session,
        sds_id="bad-id",
        file_name="test-document.pdf",
    )

    default_override = api.dependency_overrides[get_sds_port]

    def get_invalid_id_sds_port_override():
        mock_sds = MagicMock()
        mock_sds.retrieve_coroners_letter.side_effect = (
            InvalidCoronersLetterDocumentIdError()
        )
        return mock_sds

    api.dependency_overrides[get_sds_port] = get_invalid_id_sds_port_override

    try:
        response = client.get(
            f"/applications/{laa_reference}/coroners-letter",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    finally:
        api.dependency_overrides[get_sds_port] = default_override

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid coroners letter document id"}


def test_500_retrieve_coroners_letter_when_sds_retrieval_fails(
    session, client, auth_token
):
    laa_reference = _add_coroners_letter_to_application(
        session=session,
        sds_id="test-document_abc123.pdf",
        file_name="test-document.pdf",
    )

    default_override = api.dependency_overrides[get_sds_port]

    def get_failing_sds_port_override():
        mock_sds = MagicMock()
        mock_sds.retrieve_coroners_letter.side_effect = CoronersLetterRetrievalError()
        return mock_sds

    api.dependency_overrides[get_sds_port] = get_failing_sds_port_override

    try:
        response = client.get(
            f"/applications/{laa_reference}/coroners-letter",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    finally:
        api.dependency_overrides[get_sds_port] = default_override

    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to retrieve coroners letter"}
