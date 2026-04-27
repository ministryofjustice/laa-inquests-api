def test_200_create_application_response_contains_expected_base_properties(
    client, auth_token
):
    request_body = {
        "status": "PENDING",
        "laa_reference": "INQ-000-004",
        "used_delegated_functions": True,
        "application_type": "INITIAL",
        "auto_grant": True,
        "overall_decision": "PENDING",
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

    assert isinstance(new_application["application_id"], str)
    assert isinstance(new_application["created_at"], str)
    assert isinstance(new_application["updated_at"], str)
    assert isinstance(new_application["status"], str)
    assert isinstance(new_application["laa_reference"], str)
    assert isinstance(new_application["used_delegated_functions"], bool)
    assert isinstance(new_application["application_type"], str)
    assert isinstance(new_application["auto_grant"], bool)
    assert isinstance(new_application["overall_decision"], str)
