from app.models.application.index import Application
from sqlmodel import select


def test_200_read_application_by_id_returns_expected_application_base_properties(
    session, client, auth_token
):
    first_application_row = session.exec(select(Application)).first()
    first_application_id = str(first_application_row.__dict__["application_id"])

    response = client.get(
        f"/applications/{first_application_id}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    requested_application = response.json()
    print(requested_application)
    assert requested_application["application_id"] == first_application_id
