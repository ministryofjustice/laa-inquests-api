from app.auth.rbac import Role


def test_200_retrieve_coroners_letter(client, seeded_application):
    response = client.get(
        f"/applications/{seeded_application.laa_reference}/coroners-letter",
        headers={"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"  # Set in SDS mock in client fixture
