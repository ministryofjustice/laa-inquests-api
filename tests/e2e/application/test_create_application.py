def test_200_create_application_response_contains_expected_base_properties(
    client, auth_token
):
    request_body = {
        "proceedings": [
            {
                "proceeding_id": "TEST1",
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

    assert isinstance(new_application["laa_reference"], int)
    assert isinstance(new_application["created_at"], str)
    assert isinstance(new_application["updated_at"], str)
    assert isinstance(new_application["status"], str)
    assert isinstance(new_application["used_delegated_functions"], bool)
    assert isinstance(new_application["application_type"], str)
    assert isinstance(new_application["auto_grant"], bool)
    assert isinstance(new_application["overall_decision"], str)
    assert len(new_application["proceedings"]) == 1


def test_200_create_application_response_contains_expected_proceeding_information(
    client, auth_token
):
    request_body = {
        "proceedings": [
            {
                "proceeding_id": "TEST1",
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
    assert proceeding["proceeding_id"] == "TEST1"
    assert proceeding["category_of_law"] == "INQUESTS"
    assert proceeding["matter_type"] == "INQUESTS"
    assert proceeding["level_of_service"] == "FULL_REPRESENTATION"
    assert proceeding["certificate_type"] == "SUBSTANTIVE"
    assert proceeding["client_involvement_type"] == "RESPONDENT"
    assert proceeding["merits_decision"] == "PENDING"
    assert isinstance(proceeding["substantive_cost_limitation"], int)
    assert isinstance(proceeding["scope_description"], str)
    assert isinstance(proceeding["proceeding_description"], str)
