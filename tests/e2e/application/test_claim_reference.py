import re

from sqlmodel import select

from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.claim.enums import ClaimStatus
from app.models.claim.index import Claim
from tests.e2e.application.test_create_claim import _make_request_body
from tests.e2e.factories import create_claim_in_db

CLAIM_REFERENCE_PATTERN = re.compile(r"^INQC-[A-Z0-9]{4}-[A-Z0-9]{4}$")
AMBIGUOUS_CHARACTERS = "B8G6I10OQDS5Z2"

PROVIDER_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}",
}
CASEWORKER_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {Role.CLAIMS_CASEWORKER.value}",
}


def _submit_claim(client, laa_reference, overrides=None):
    return client.post(
        f"/applications/{laa_reference}/claim",
        json=_make_request_body(overrides),
        headers=PROVIDER_HEADERS,
    )


class TestClaimReferenceGeneration:
    def test_201_create_claim_response_returns_claim_reference_in_expected_format(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference

        response = _submit_claim(client, laa_reference)

        assert response.status_code == 201
        body = response.json()
        assert CLAIM_REFERENCE_PATTERN.match(body["claimReference"])

    def test_201_create_claim_response_does_not_expose_internal_claim_id(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference

        response = _submit_claim(client, laa_reference)

        assert response.status_code == 201
        assert "claimId" not in response.json()

    def test_201_create_claim_stores_claim_reference_against_record(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference

        response = _submit_claim(client, laa_reference)

        reference = response.json()["claimReference"]
        stored_claim = session.exec(
            select(Claim).where(Claim.claim_reference == reference)
        ).one()
        assert stored_claim.claim_reference == reference

    def test_claim_reference_excludes_ambiguous_characters(self, session, client):
        laa_reference = session.exec(select(Application)).first().laa_reference

        # Multiple submissions to reduce the chance of missing ambiguous characters.
        for _ in range(10):
            response = _submit_claim(client, laa_reference)
            reference = response.json()["claimReference"]
            payload = reference.removeprefix("INQC-").replace("-", "")
            assert all(char not in payload for char in AMBIGUOUS_CHARACTERS)

    def test_two_claims_receive_different_references(self, session, client):
        laa_reference = session.exec(select(Application)).first().laa_reference

        first = _submit_claim(client, laa_reference).json()["claimReference"]
        second = _submit_claim(client, laa_reference).json()["claimReference"]

        assert first != second

    def test_claim_reference_exposed_in_claim_list(self, session, client):
        application = session.exec(select(Application)).first()
        claim = create_claim_in_db(
            session,
            application_id=application.application_id,
            status=ClaimStatus.SUBMITTED,
        )

        list_response = client.get(
            f"/applications/{application.laa_reference}/claims?assessed=false",
            headers=CASEWORKER_HEADERS,
        )

        assert list_response.status_code == 200
        references = [item["claimReference"] for item in list_response.json()]
        assert claim.claim_reference in references

    def test_claim_reference_available_and_unchanged_when_claim_viewed_by_id(
        self, session, client
    ):
        laa_reference = session.exec(select(Application)).first().laa_reference
        reference = _submit_claim(client, laa_reference).json()["claimReference"]

        get_response = client.get(
            f"/applications/{laa_reference}/claims/{reference}",
            headers=CASEWORKER_HEADERS,
        )

        assert get_response.status_code == 200
        assert get_response.json()["claimReference"] == reference
