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
    assert result["clientName"] == "Test Surname"
    assert result["clientDateOfBirth"] == "01-02-2003"
    assert "dateSubmitted" in result
    assert result["firmName"] == "Test Firm Name"
    assert result["firmNumber"] == "0A123B"
    assert result["caseStatus"] == "LIVE"


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


def test_422_search_application_returns_unprocessable_when_laa_reference_missing(
    client, auth_token
):
    response = client.get(
        "/applications/search",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 422
