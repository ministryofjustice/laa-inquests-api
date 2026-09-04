from sqlmodel import select

from app.models.application.enums import MeritsDecision
from app.models.application.index import Application
from tests.e2e.factories import create_application_in_db


def _seed_application_for_other_firm(session, firm_code: str = "ZZ999Z") -> int:
    other_application = create_application_in_db(
        session,
        provider_overrides={
            "firm_code": firm_code,
            "office_id": "002",
            "email_address": "other@example.com",
        },
    )
    return other_application.laa_reference


def test_200_search_application_by_reference_returns_expected_fields(
    client, auth_token
):
    response = client.get(
        "/applications/search",
        params={"laa_reference": "1"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    result = body[0]
    assert result["laaReference"] == "1"
    assert result["clientFirstName"] == "Test"
    assert result["clientLastName"] == "Surname"
    assert result["clientDateOfBirth"] == "01-02-2003"
    assert "dateSubmitted" in result
    assert result["firmName"] == "Test Firm Name"
    assert result["firmNumber"] == "0A123B"
    assert result["overallDecision"] == MeritsDecision.GRANTED


def test_200_search_application_trims_leading_and_trailing_spaces(client, auth_token):
    response = client.get(
        "/applications/search",
        params={"laa_reference": "  1  "},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["laaReference"] == "1"


def test_200_search_application_returns_empty_list_for_unknown_reference(
    client, auth_token
):
    response = client.get(
        "/applications/search",
        params={"laa_reference": "99999"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_200_search_application_includes_pending_application_when_no_merits_filter(
    session, client, auth_token
):
    app = session.exec(select(Application)).first()
    app.proceeding.merits_decision = MeritsDecision.PENDING
    session.add(app.proceeding)
    session.commit()

    response = client.get(
        "/applications/search",
        params={"laa_reference": str(app.laa_reference)},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["laaReference"] == app.laa_reference


def test_200_search_application_with_merits_filter_returns_only_granted(
    session, client, auth_token
):
    app = session.exec(select(Application)).first()
    app.proceeding.merits_decision = MeritsDecision.GRANTED
    session.add(app.proceeding)
    session.commit()

    response = client.get(
        "/applications/search",
        params={
            "laa_reference": str(app.laa_reference),
            "merits_decision": MeritsDecision.GRANTED.value,
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["laaReference"] == app.laa_reference


def test_200_search_application_with_granted_filter_excludes_pending_application(
    session, client, auth_token
):
    app = session.exec(select(Application)).first()
    app.proceeding.merits_decision = MeritsDecision.PENDING
    session.add(app.proceeding)
    session.commit()

    response = client.get(
        "/applications/search",
        params={
            "laa_reference": str(app.laa_reference),
            "merits_decision": MeritsDecision.GRANTED.value,
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_422_search_application_returns_unprocessable_when_laa_reference_missing(
    client, auth_token
):
    response = client.get(
        "/applications/search",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 422


def test_200_search_application_excludes_application_belonging_to_another_firm(
    session, client, auth_token
):
    other_firm_reference = _seed_application_for_other_firm(session)

    response = client.get(
        "/applications/search",
        params={"laa_reference": str(other_firm_reference)},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.json() == []
