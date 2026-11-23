import json
from unittest.mock import MagicMock

import pytest
from sqlmodel import select

from app import api
from app.auth.rbac import Role
from app.models.application.index import Application, CoronersLetter
from app.routers.applications import get_sds_port
from app.use_cases.exceptions import SDSLetterRetrievalError
from tests.e2e.factories import create_application_in_db


class TestRetrieveCoronersLetter:
    def test_200_retrieve_coroners_letter(self, session, client):
        application = session.exec(select(Application)).first()

        response = client.get(
            f"/applications/{application.laa_reference}/coroners-letter",
            headers={"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"},
        )

        assert response.status_code == 200
        assert response.content == b"file bytes"  # Set in SDS mock in client fixture

    def test_500_retrieve_coroners_letter_failure_does_not_send_sds_file_key_to_sentry(
        self, session, client, captured_sentry_events
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


class TestRetrieveCoronersLetterOfficeIdCheck:
    @pytest.fixture
    def other_office_application(self, session):
        letter = CoronersLetter(
            sds_file_name="stored-file-key", file_name="letter.pdf", office_id="003"
        )
        session.add(letter)
        session.commit()
        return create_application_in_db(
            session,
            provider_overrides={"firm_code": "ZZ999Z", "office_id": "003"},
            coroners_letter_id=letter.coroners_letter_id,
        )

    @pytest.mark.parametrize(
        "provider_role", [Role.PROVIDER_APPLICATION_USER, Role.PROVIDER_CLAIMS_USER]
    )
    def test_403_provider_cannot_read_any_coroners_letter(
        self, session, client, provider_role, other_office_application
    ):
        own_application = session.exec(select(Application)).first()
        mock_sds = MagicMock()
        api.dependency_overrides[get_sds_port] = lambda: mock_sds
        headers = {"Authorization": f"Bearer {provider_role.value}"}

        own_response = client.get(
            f"/applications/{own_application.laa_reference}/coroners-letter",
            headers=headers,
        )
        other_response = client.get(
            f"/applications/{other_office_application.laa_reference}/coroners-letter",
            headers=headers,
        )

        assert own_response.status_code == other_response.status_code == 403
        mock_sds.retrieve_coroners_letter.assert_not_called()

    @pytest.mark.parametrize(
        "staff_role", [Role.APPLICATIONS_CASEWORKER, Role.CLAIMS_CASEWORKER]
    )
    def test_200_caseworker_can_read_coroners_letter_from_any_office(
        self, client, staff_role, other_office_application
    ):
        response = client.get(
            f"/applications/{other_office_application.laa_reference}/coroners-letter",
            headers={"Authorization": f"Bearer {staff_role.value}"},
        )

        assert response.status_code == 200
        assert response.content == b"file bytes"
