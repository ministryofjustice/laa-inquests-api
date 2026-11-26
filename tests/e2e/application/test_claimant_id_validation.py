import pytest
from sqlmodel import select

from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.claim.index import Claim
from tests.helpers.claim_payloads import make_poa_claim_request_body

pytestmark = pytest.mark.usefixtures("mock_gov_notify")


def _create_claim(client, session, claimant_id):
    laa_reference = session.exec(select(Application)).first().laa_reference
    return client.post(
        f"/applications/{laa_reference}/claim",
        json=make_poa_claim_request_body({"claimantId": claimant_id}),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}",
        },
    )


@pytest.mark.parametrize(
    "value",
    [
        "claimant",
        "claimant@",
        "<b>@example.com",
        "a@b.c",
        "a b@example.com",
        "claimant@example.com;x",
        f"{'a' * 250}@example.com",
        "",
        " ",
    ],
)
def test_422_claimant_id_rejects_values_that_are_not_mailbox_addresses(
    session, client, value
):
    assert _create_claim(client, session, value).status_code == 422


@pytest.mark.parametrize(
    "value", ["claimant-123@provider.co.uk", "o'brien+tag@firm.co.uk"]
)
def test_201_claimant_id_accepts_mailbox_style_addresses(session, client, value):
    assert _create_claim(client, session, value).status_code == 201


def test_201_claimant_id_is_stored_trimmed(session, client):
    response = _create_claim(client, session, " claimant-123@provider.co.uk\n")

    assert response.status_code == 201
    stored = session.exec(
        select(Claim).where(Claim.claim_reference == response.json()["claimReference"])
    ).one()
    assert stored.claimant_id == "claimant-123@provider.co.uk"
