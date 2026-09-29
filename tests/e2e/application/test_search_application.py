from app.auth.rbac import Role
from app.models.application.enums import MeritsDecision
from tests.factories.persisted import create_application
from tests.factories.seed import TEST_USER_FIRM_CODE


def test_200_search_application_by_reference_returns_expected_fields(
    client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    response = client.get(
        "/applications/search",
        params={"laa_reference": laa_reference},
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    result = body[0]
    assert result["laaReference"] == laa_reference
    assert result["clientFirstName"] == "Test"
    assert result["clientLastName"] == "Surname"
    assert result["clientDateOfBirth"] == "01-02-2003"
    assert "dateSubmitted" in result
    assert result["firmName"] == "Test Firm Name"
    assert result["firmNumber"] == "0A123B"
    assert result["overallDecision"] == MeritsDecision.GRANTED


def test_200_search_application_trims_leading_and_trailing_spaces(
    client, seeded_application
):
    laa_reference = seeded_application.laa_reference
    response = client.get(
        "/applications/search",
        params={"laa_reference": f"  {laa_reference}  "},
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert response.json()[0]["laaReference"] == laa_reference


def test_200_search_application_returns_empty_list_for_unknown_reference(client):
    response = client.get(
        "/applications/search",
        params={"laa_reference": "99999"},
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_200_search_application_includes_pending_application_when_no_merits_filter(
    session, client
):
    app = create_application(
        session,
        provider_overrides={"firm_code": TEST_USER_FIRM_CODE},
        proceeding_overrides={"merits_decision": MeritsDecision.PENDING},
    )

    response = client.get(
        "/applications/search",
        params={"laa_reference": str(app.laa_reference)},
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["laaReference"] == app.laa_reference


def test_200_search_application_with_merits_filter_returns_only_granted(
    session, client
):
    app = create_application(
        session,
        provider_overrides={"firm_code": TEST_USER_FIRM_CODE},
        proceeding_overrides={"merits_decision": MeritsDecision.GRANTED},
    )

    response = client.get(
        "/applications/search",
        params={
            "laa_reference": str(app.laa_reference),
            "merits_decision": MeritsDecision.GRANTED.value,
        },
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["laaReference"] == app.laa_reference


def test_200_search_application_with_granted_filter_excludes_pending_application(
    session, client
):
    app = create_application(
        session,
        provider_overrides={"firm_code": TEST_USER_FIRM_CODE},
        proceeding_overrides={"merits_decision": MeritsDecision.PENDING},
    )

    response = client.get(
        "/applications/search",
        params={
            "laa_reference": str(app.laa_reference),
            "merits_decision": MeritsDecision.GRANTED.value,
        },
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_422_search_application_returns_unprocessable_when_laa_reference_missing(
    client,
):
    response = client.get(
        "/applications/search",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 422


def test_200_search_application_excludes_application_belonging_to_another_firm(
    session, client
):
    other_firm_reference = create_application(
        session,
        provider_overrides={
            "firm_code": "ZZ999Z",
            "office_id": "002",
            "email_address": "other@example.com",
        },
    ).laa_reference

    response = client.get(
        "/applications/search",
        params={"laa_reference": str(other_firm_reference)},
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert response.json() == []
