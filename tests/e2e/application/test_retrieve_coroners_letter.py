from app.models.application.index import Application, CoronersLetter
from sqlmodel import select


def test_200_retrieve_coroners_letter_returns_file_bytes(session, client, auth_token):
    application = session.exec(select(Application)).first()

    coroners_letter = CoronersLetter(
        sds_id="test-document_abc123.pdf",
        file_name="test-document.pdf",
    )
    session.add(coroners_letter)
    session.commit()
    session.refresh(coroners_letter)

    application.coroners_letter_id = coroners_letter.coroners_letter_id
    session.add(application)
    session.commit()

    laa_reference = application.laa_reference

    response = client.get(
        f"/applications/{laa_reference}/coroners-letter",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    assert response.content == b"file bytes"
    assert (
        response.headers["content-disposition"]
        == 'attachment; filename="test-document.pdf"'
    )
