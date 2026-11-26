import pytest
from sqlmodel import select

from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.claim.enums import ClaimType
from tests.e2e.factories import create_application_in_db, create_claim_for_reference

pytestmark = pytest.mark.usefixtures("mock_gov_notify")

REJECTED_PROSE = [
    "<script>alert(1)</script>",
    "a > b",
    "<Test'';!--\"=&{()}>",
    "bad\x00value",
    "bad\x1bvalue",
]
ACCEPTED_PROSE = [
    'It\'s "quoted"; see = A1 -- fine & (ok) {yes}',
    "Line one\nLine two",
]


def _headers(role: Role) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {role.value}",
    }


class TestRefuseDecisionJustification:
    @staticmethod
    def _refuse(client, laa_reference, justification):
        return client.patch(
            f"/applications/{laa_reference}/refuse-decision",
            json={"reasonForRefusal": "NOT_IN_SCOPE", "justification": justification},
            headers=_headers(Role.APPLICATIONS_CASEWORKER),
        )

    @pytest.mark.parametrize("value", REJECTED_PROSE)
    def test_422_rejects_disallowed_characters(self, session, client, value):
        application = create_application_in_db(session)

        response = self._refuse(client, application.laa_reference, value)

        assert response.status_code == 422

    @pytest.mark.parametrize("value", ACCEPTED_PROSE)
    def test_204_accepts_quotes_semicolons_and_newlines(self, session, client, value):
        application = create_application_in_db(session)

        response = self._refuse(client, application.laa_reference, value)

        assert response.status_code == 204

    def test_204_accepts_exactly_1500_characters(self, session, client):
        application = create_application_in_db(session)

        response = self._refuse(client, application.laa_reference, "A" * 1500)

        assert response.status_code == 204

    def test_422_rejects_more_than_1500_characters(self, session, client):
        application = create_application_in_db(session)

        response = self._refuse(client, application.laa_reference, "A" * 1501)

        assert response.status_code == 422


class TestRejectClaimJustification:
    @staticmethod
    def _reject(client, session, justification):
        laa_reference = session.exec(select(Application)).first().laa_reference
        claim = create_claim_for_reference(
            session, laa_reference, claim_type=ClaimType.PAYMENT_ON_ACCOUNT
        )
        return client.patch(
            f"/applications/{laa_reference}/claims/{claim.claim_reference}/reject",
            json={"justification": justification},
            headers=_headers(Role.CLAIMS_CASEWORKER),
        )

    @pytest.mark.parametrize("value", REJECTED_PROSE)
    def test_422_rejects_disallowed_characters(self, session, client, value):
        assert self._reject(client, session, value).status_code == 422

    @pytest.mark.parametrize("value", ACCEPTED_PROSE)
    def test_204_accepts_quotes_semicolons_and_newlines(self, session, client, value):
        assert self._reject(client, session, value).status_code == 204

    def test_204_accepts_exactly_500_characters(self, session, client):
        assert self._reject(client, session, "A" * 500).status_code == 204

    @pytest.mark.parametrize("value", ["A" * 501, "", " ", "\n\t"])
    def test_422_rejects_blank_and_more_than_500_characters(
        self, session, client, value
    ):
        assert self._reject(client, session, value).status_code == 422


class TestCreateNoteText:
    @staticmethod
    def _create_note(client, session, note_text):
        laa_reference = session.exec(select(Application)).first().laa_reference
        return client.post(
            f"/applications/{laa_reference}/note",
            json={"noteText": note_text},
            headers=_headers(Role.APPLICATIONS_CASEWORKER),
        )

    @pytest.mark.parametrize("value", REJECTED_PROSE)
    def test_422_rejects_disallowed_characters(self, session, client, value):
        assert self._create_note(client, session, value).status_code == 422

    @pytest.mark.parametrize("value", ACCEPTED_PROSE)
    def test_204_accepts_quotes_semicolons_and_newlines(self, session, client, value):
        assert self._create_note(client, session, value).status_code == 204
