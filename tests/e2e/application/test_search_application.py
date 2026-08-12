from sqlmodel import select

from app.models.application.enums import MeritsDecision
from app.models.application.index import Application, Provider


def _seed_application_for_other_firm(session, firm_code: str = "ZZ999Z") -> int:
    existing = session.exec(select(Application)).first()
    other_provider = Provider(
        firm_code=firm_code,
        office_id="002",
        email_address="other@example.com",
    )
    session.add(other_provider)
    session.commit()
    session.refresh(other_provider)

    other_application = Application(
        client_id=existing.client_id,
        deceased_id=existing.deceased_id,
        provider_id=other_provider.provider_id,
    )
    session.add(other_application)
    session.commit()
    session.refresh(other_application)
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
    assert result["laaReference"] == 1
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
    assert response.json()[0]["laaReference"] == 1


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


def test_200_search_application_excludes_pending_application(
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
