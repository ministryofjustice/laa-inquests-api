"""E2E tests for sending grant letter print pack via Gov Notify precompiled letter."""

from sqlmodel import select

from app.models.application.index import Application


def _grant_decision_payload():
    return {"certificateStartDate": "2000-01-01"}


def test_204_grant_decision_calls_generate_print_letter_pdf(
    session, client, auth_token, mock_pdf_generation_port
):
    """Granting a decision generates the print letter PDF pack."""
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/grant-decision",
        json=_grant_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 204
    mock_pdf_generation_port.generate_print_letter_pdf.assert_called_once()


def test_204_grant_decision_calls_send_precompiled_letter(
    session, client, auth_token, mock_gov_notify, mock_pdf_generation_port
):
    """Granting a decision sends the print pack via Gov Notify precompiled letter."""
    mock_pdf_generation_port.generate_print_letter_pdf.return_value = (
        b"%PDF-1.4 print letter"
    )
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/grant-decision",
        json=_grant_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 204
    mock_gov_notify.send_precompiled_letter.assert_called_once_with(
        str(laa_reference),
        b"%PDF-1.4 print letter",
    )


def test_204_grant_decision_sends_precompiled_letter_after_email(
    session, client, auth_token, mock_gov_notify, mock_pdf_generation_port
):
    """The precompiled letter is sent after the grant email succeeds."""
    mock_pdf_generation_port.generate_print_letter_pdf.return_value = (
        b"%PDF-1.4 print letter"
    )
    application = session.exec(select(Application)).first()
    laa_reference = application.laa_reference

    response = client.patch(
        f"/applications/{laa_reference}/grant-decision",
        json=_grant_decision_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )

    assert response.status_code == 204
    # Both email and precompiled letter should have been called
    mock_gov_notify.send_application_granted_decision_email.assert_called_once()
    mock_gov_notify.send_precompiled_letter.assert_called_once()
