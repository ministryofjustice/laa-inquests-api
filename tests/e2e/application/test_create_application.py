def test_201_create_application_response_contains_expected_base_properties(
    client, auth_token
):
    request_body = {
        "proceedings": [
            {
                "proceedingId": "TEST1",
            }
        ],
        "client": {
            "clientFirstName": "test",
            "clientLastName": "surname",
            "dateOfBirth": "01-01-1990",
            "nationalInsuranceNumber": "AB12345A",
            "correspondenceAddress": "123 street",
            "homeAddress": "my house",
            "relationshipToDeceased": "partner",
        },
    }
    response = client.post(
        "/applications",
        json=request_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )
    new_application = response.json()
    assert isinstance(new_application["laaReference"], int)
    assert isinstance(new_application["createdAt"], str)
    assert isinstance(new_application["updatedAt"], str)
    assert isinstance(new_application["status"], str)
    assert isinstance(new_application["usedDelegatedFunctions"], bool)
    assert isinstance(new_application["applicationType"], str)
    assert isinstance(new_application["autoGrant"], bool)
    assert isinstance(new_application["overallDecision"], str)
    assert len(new_application["proceedings"]) == 1


def test_201_create_application_response_contains_expected_proceeding_information(
    client, auth_token
):
    request_body = {
        "proceedings": [
            {
                "proceedingId": "TEST1",
            }
        ],
        "client": {
            "clientFirstName": "test",
            "clientLastName": "surname",
            "dateOfBirth": "01-01-1990",
            "nationalInsuranceNumber": "AB12345A",
            "correspondenceAddress": "123 street",
            "homeAddress": "my house",
            "relationshipToDeceased": "partner",
        },
    }
    response = client.post(
        "/applications",
        json=request_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )
    new_application = response.json()
    proceeding = new_application["proceedings"][0]
    assert proceeding["proceedingId"] == "TEST1"
    assert proceeding["categoryOfLaw"] == "INQUESTS"
    assert proceeding["matterType"] == "INQUESTS"
    assert proceeding["levelOfService"] == "FULL_REPRESENTATION"
    assert proceeding["certificateType"] == "SUBSTANTIVE"
    assert proceeding["clientInvolvementType"] == "RESPONDENT"
    assert proceeding["meritsDecision"] == "PENDING"
    assert isinstance(proceeding["substantiveCostLimitation"], int)
    assert isinstance(proceeding["scopeDescription"], str)
    assert isinstance(proceeding["proceedingDescription"], str)


def test_201_responds_with_expected_client_details(client, auth_token):
    request_body = {
        "proceedings": [
            {
                "proceedingId": "TEST1",
            }
        ],
        "client": {
            "clientFirstName": "testing",
            "clientLastName": "lastname",
            "dateOfBirth": "01-01-1990",
            "correspondenceAddress": "123 street",
            "homeAddress": "my house",
            "relationshipToDeceased": "partner",
        },
    }
    response = client.post(
        "/applications",
        json=request_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        },
    )
    new_application = response.json()
    client = new_application["client"]
    assert isinstance(client["clientId"], int)
    assert client["clientFirstName"] == "testing"
    assert client["clientLastName"] == "lastname"
    assert client["clientLastNameAtBirth"] is None
    assert client["dateOfBirth"] == "01-01-1990"
    assert client["nationalInsuranceNumber"] is None
    assert client["correspondenceAddress"] == "123 street"
    assert client["homeAddress"] == "my house"
    assert client["relationshipToDeceased"] == "partner"
    assert not client["hasAppliedPreviously"]
