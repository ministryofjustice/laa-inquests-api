import io
import uuid

from sqlmodel import select

from app.models.application.enums import MeritsDecision
from app.models.application.index import Application, CoronersLetter
from app.models.claim.index import ClaimEvidence


def _create_application_payload():
    return {
        "coronersLetterId": str(uuid.uuid4()),
        "proceedings": [{"proceedingId": "IQOT"}],
        "client": {
            "clientFirstName": "Test",
            "clientLastName": "Surname",
            "dateOfBirth": "01-01-1990",
            "nationalInsuranceNumber": "AB12345A",
            "correspondenceAddressSource": "USE_SPECIFIED_ADDRESS",
            "correspondenceAddress": {
                "addressLine1": "2 Example Lane",
                "townOrCity": "London",
                "postcode": "SW1A 1AA",
            },
            "hasNoFixedAbode": False,
            "homeAddress": {
                "addressLine1": "1 Example Lane",
                "addressLine2": "Flat 2",
                "townOrCity": "London",
                "county": "Greater London",
                "postcode": "SW1A 1AA",
            },
            "isClientCorrespondenceRecipient": True,
        },
        "publicBodies": [{"publicBodyId": "Department for Transport"}],
        "deceased": {
            "deceasedFirstName": "Test",
            "deceasedLastName": "Surname",
            "deceasedDateOfBirth": "01-01-2000",
            "deceasedDateOfDeath": "01-01-2025",
            "coronersReference": "COR-2025-001",
            "furtherInformation": "Further details to be confirmed",
            "clientRelationshipToDeceased": "guardian",
        },
        "provider": {
            "firmCode": "0A123B",
            "officeId": "001",
            "emailAddress": "provider@example.com",
        },
    }


def test_200_read_all_applications_returns_200_when_valid_entra_token(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 200


def test_401_read_all_applications_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.get("/applications")

    assert response.status_code == 401


def test_401_read_all_applications_returns_401_when_bearer_token_is_invalid(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_403_read_all_applications_returns_403_when_scope_is_not_provider(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications",
        headers={"Authorization": "Bearer valid-provider-entra-token"},
    )

    assert response.status_code == 403


def test_200_read_application_by_id_returns_200_when_caseworker_token(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications/1",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 200


def test_403_read_application_by_id_returns_403_when_provider_token(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications/1",
        headers={"Authorization": "Bearer valid-provider-entra-token"},
    )

    assert response.status_code == 403


def test_201_create_application_returns_201_when_provider_token(
    entra_auth_client,
):
    response = entra_auth_client.post(
        "/applications",
        json=_create_application_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-provider-entra-token",
        },
    )

    assert response.status_code == 201


def test_403_create_application_returns_403_when_caseworker_token(
    entra_auth_client,
):
    response = entra_auth_client.post(
        "/applications",
        json=_create_application_payload(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-caseworker-entra-token",
        },
    )

    assert response.status_code == 403


def test_201_upload_coroners_letter_returns_201_when_provider_token(
    entra_auth_client,
):
    response = entra_auth_client.post(
        "/applications/upload-coroners-letter",
        files={
            "file": (
                "coroners_letter.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": "Bearer valid-provider-entra-token"},
    )

    assert response.status_code == 201


def test_403_upload_coroners_letter_returns_403_when_caseworker_token(
    entra_auth_client,
):
    response = entra_auth_client.post(
        "/applications/upload-coroners-letter",
        files={
            "file": (
                "coroners_letter.pdf",
                io.BytesIO(b"test content"),
                "application/pdf",
            )
        },
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 403


def test_204_refuse_decision_returns_204_when_caseworker_token(
    entra_auth_client,
):
    response = entra_auth_client.patch(
        "/applications/1/refuse-decision",
        json={
            "meritsDecision": MeritsDecision.REFUSED,
            "reasonForRefusal": "NOT_IN_SCOPE",
            "justification": "The matter does not meet scope requirements.",
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-caseworker-entra-token",
        },
    )

    assert response.status_code == 204


def test_403_refuse_decision_returns_403_when_provider_token(
    entra_auth_client,
):
    response = entra_auth_client.patch(
        "/applications/1/refuse-decision",
        json={
            "meritsDecision": MeritsDecision.REFUSED,
            "reasonForRefusal": "NOT_IN_SCOPE",
            "justification": "The matter does not meet scope requirements.",
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-provider-entra-token",
        },
    )

    assert response.status_code == 403


def test_204_grant_decision_returns_204_when_caseworker_token(
    entra_auth_client,
):
    response = entra_auth_client.patch(
        "/applications/1/grant-decision",
        json={"certificateStartDate": "2000-01-01"},
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-caseworker-entra-token",
        },
    )

    assert response.status_code == 204


def test_403_grant_decision_returns_403_when_provider_token(
    entra_auth_client,
):
    response = entra_auth_client.patch(
        "/applications/1/grant-decision",
        json={"certificateStartDate": "2000-01-01"},
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-provider-entra-token",
        },
    )

    assert response.status_code == 403


def test_200_search_application_returns_200_when_provider_token(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications/search",
        params={"laa_reference": "1"},
        headers={"Authorization": "Bearer valid-provider-entra-token"},
    )

    assert response.status_code == 200


def test_401_search_application_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications/search",
        params={"laa_reference": "1"},
    )

    assert response.status_code == 401


def test_401_search_application_returns_401_when_bearer_token_is_invalid(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications/search",
        params={"laa_reference": "1"},
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_403_search_application_returns_403_when_caseworker_token(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications/search",
        params={"laa_reference": "1"},
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 403


def test_200_retrieve_coroners_letter_returns_200_when_caseworker_token(
    session, entra_auth_client
):
    application = session.exec(select(Application)).first()
    coroners_letter = CoronersLetter(
        sds_file_name="stored-file_abc123.pdf",
        file_name="coroners_letter.pdf",
    )
    session.add(coroners_letter)
    session.commit()
    session.refresh(coroners_letter)

    application.coroners_letter_id = coroners_letter.coroners_letter_id
    session.add(application)
    session.commit()

    response = entra_auth_client.get(
        f"/applications/{application.laa_reference}/coroners-letter",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 200


def test_401_retrieve_coroners_letter_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.get("/applications/1/coroners-letter")

    assert response.status_code == 401


def test_401_retrieve_coroners_letter_returns_401_when_bearer_token_is_invalid(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications/1/coroners-letter",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_403_retrieve_coroners_letter_returns_403_when_provider_token(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications/1/coroners-letter",
        headers={"Authorization": "Bearer valid-provider-entra-token"},
    )

    assert response.status_code == 403


def test_200_list_public_bodies_returns_200_when_provider_token(entra_auth_client):
    response = entra_auth_client.get(
        "/applications/public-bodies",
        headers={"Authorization": "Bearer valid-provider-entra-token"},
    )

    assert response.status_code == 200


def test_401_list_public_bodies_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.get("/applications/public-bodies")

    assert response.status_code == 401


def test_401_list_public_bodies_returns_401_when_bearer_token_is_invalid(
    entra_auth_client,
):
    response = entra_auth_client.get(
        "/applications/public-bodies",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_403_list_public_bodies_returns_403_when_caseworker_token(entra_auth_client):
    response = entra_auth_client.get(
        "/applications/public-bodies",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 403


def test_403_retrieve_claim_evidence_returns_403_when_caseworker_token(
    entra_auth_client,
):
    response = entra_auth_client.get(
        f"/applications/claim/evidence/{uuid.uuid4()}",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 403


def test_200_retrieve_claim_evidence_returns_200_when_provider_token(
    session, entra_auth_client
):
    claim_evidence = ClaimEvidence(
        sds_file_name="stored-claim-evidence_abc123.pdf",
        file_name="claim_evidence.pdf",
    )
    session.add(claim_evidence)
    session.commit()
    session.refresh(claim_evidence)

    response = entra_auth_client.get(
        f"/applications/claim/evidence/{claim_evidence.claim_evidence_id}",
        headers={"Authorization": "Bearer valid-provider-entra-token"},
    )

    assert response.status_code == 200


def test_401_retrieve_claim_evidence_returns_401_when_no_authorization_header(
    entra_auth_client,
):
    response = entra_auth_client.get(f"/applications/claim/evidence/{uuid.uuid4()}")

    assert response.status_code == 401


def test_401_retrieve_claim_evidence_returns_401_when_bearer_token_is_invalid(
    entra_auth_client,
):
    response = entra_auth_client.get(
        f"/applications/claim/evidence/{uuid.uuid4()}",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
