def test_200_create_application_response_contains_expected_base_properties(
    client, auth_token
):
    request_body = {
        "proceedings": [
            {
                "proceedingId": "TEST1",
            }
        ]
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


def test_200_create_application_response_contains_expected_proceeding_information(
    client, auth_token
):
    request_body = {
        "proceedings": [
            {
                "proceedingId": "TEST1",
            }
        ]
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
