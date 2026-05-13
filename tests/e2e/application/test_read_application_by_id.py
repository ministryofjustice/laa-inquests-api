from app.models.application.index import Application
from sqlmodel import select


def test_200_read_application_by_reference_returns_expected_application(
    session, client, auth_token
):
    first_application_row = session.exec(select(Application)).first()
    first_application_laa_reference = int(
        first_application_row.__dict__["laa_reference"]
    )

    response = client.get(
        f"/applications/{first_application_laa_reference}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    requested_application = response.json()
    print(requested_application)
    assert requested_application["laa_reference"] == 1


def test_200_proceeding_details_included_on_application_response(
    session, client, auth_token
):
    first_application_row = session.exec(select(Application)).first()
    first_application_laa_reference = first_application_row.__dict__["laa_reference"]

    response = client.get(
        f"/applications/{first_application_laa_reference}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    requested_application = response.json()
    assert len(requested_application["proceedings"]) == 1
