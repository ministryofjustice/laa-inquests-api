import pytest
from sqlmodel import select

from app.auth.rbac import Role
from app.models.application.index import Application
from app.models.claim.index import Claim
from tests.helpers.claim_payloads import (
    make_final_bill_claim_body,
    make_nil_bill_claim_body,
)

pytestmark = pytest.mark.usefixtures("mock_gov_notify")

BODY_FACTORIES = [make_final_bill_claim_body, make_nil_bill_claim_body]


def _create_claim(client, session, body):
    laa_reference = session.exec(select(Application)).first().laa_reference
    return client.post(
        f"/applications/{laa_reference}/claim",
        json=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}",
        },
    )


@pytest.mark.parametrize("make_body", BODY_FACTORIES)
@pytest.mark.parametrize(
    "value",
    [
        "<script>alert(1)</script>",
        "Council;",
        'He said "no"',
        "Co/Ltd",
        "&&",
        "bad\x00value",
        "Test\nCouncil",
        "A" * 101,
    ],
)
def test_422_paying_party_rejects_disallowed_input(session, client, make_body, value):
    response = _create_claim(client, session, make_body({"payingParty": value}))

    assert response.status_code == 422


@pytest.mark.parametrize("make_body", BODY_FACTORIES)
@pytest.mark.parametrize(
    "value",
    [
        "Test Council",
        "Hammersmith & Fulham Council",
        "St. Mary's Trust, Ltd",
        "Zoë Éditions",
        "A" * 100,
    ],
)
def test_201_paying_party_accepts_organisation_names(session, client, make_body, value):
    response = _create_claim(client, session, make_body({"payingParty": value}))

    assert response.status_code == 201


@pytest.mark.parametrize("make_body", BODY_FACTORIES)
@pytest.mark.parametrize("value", ["", "   "])
def test_201_paying_party_accepts_blank_because_the_ui_sends_it_for_final_and_nil_bills(
    session, client, make_body, value
):
    response = _create_claim(client, session, make_body({"payingParty": value}))

    assert response.status_code == 201


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" Test Council ", "Test Council"),
        ("   ", ""),
        ("O\u2019Brien Ltd", "O'Brien Ltd"),
    ],
)
def test_201_paying_party_is_stored_trimmed_and_normalised(
    session, client, value, expected
):
    response = _create_claim(
        client, session, make_final_bill_claim_body({"payingParty": value})
    )

    assert response.status_code == 201
    stored = session.exec(
        select(Claim).where(Claim.claim_reference == response.json()["claimReference"])
    ).one()
    assert stored.paying_party == expected
