import pytest

from app.auth.rbac import Role

MALFORMED_REFERENCES = ["INQ%20ABC", "%3Cb%3E", "INQ.ABC", "INQ_ABC", "A" * 21]


def _get(client, path, role):
    return client.get(path, headers={"Authorization": f"Bearer {role.value}"})


@pytest.mark.parametrize("value", MALFORMED_REFERENCES)
@pytest.mark.parametrize(
    ("template", "role"),
    [
        ("/applications/{ref}", Role.APPLICATIONS_CASEWORKER),
        ("/applications/{ref}/history", Role.APPLICATIONS_CASEWORKER),
        ("/applications/{ref}/claims", Role.CLAIMS_CASEWORKER),
        ("/applications/{ref}/claims/INQC-ABCD-EFGH", Role.CLAIMS_CASEWORKER),
    ],
)
def test_422_malformed_laa_reference_in_the_path(client, template, role, value):
    assert _get(client, template.format(ref=value), role).status_code == 422


@pytest.mark.parametrize("value", MALFORMED_REFERENCES)
@pytest.mark.parametrize(
    "template",
    [
        "/applications/INQ-ABC-DEF/claims/{ref}",
        "/claims/{ref}/application",
    ],
)
def test_422_malformed_claim_reference_in_the_path(client, template, value):
    response = _get(client, template.format(ref=value), Role.CLAIMS_CASEWORKER)

    assert response.status_code == 422


@pytest.mark.parametrize("reference", ["99999", "INQ-ZZZ-ZZZ"])
def test_404_unknown_but_well_formed_laa_reference_is_still_not_found(
    client, reference
):
    response = _get(client, f"/applications/{reference}", Role.APPLICATIONS_CASEWORKER)

    assert response.status_code == 404


@pytest.mark.parametrize("value", ["%3Cb%3E", "inq%20abc%20def", "no-such-ref", ""])
def test_200_search_with_an_unknown_or_oddly_typed_reference_finds_nothing(
    client, value
):
    response = client.get(
        f"/applications/search?laa_reference={value}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_422_search_reference_longer_than_50_characters(client):
    response = client.get(
        f"/applications/search?laa_reference={'A' * 51}",
        headers={"Authorization": f"Bearer {Role.PROVIDER_CLAIMS_USER.value}"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "firm_id", ["a%3Fb", "a%23b", "a.b", "a%20b", "%3Cb%3E", "A" * 21]
)
def test_422_provider_offices_firm_id_that_could_alter_the_outbound_url(
    client, firm_id
):
    response = _get(
        client,
        f"/applications/provider-offices/{firm_id}",
        Role.PROVIDER_APPLICATION_USER,
    )

    assert response.status_code == 422
