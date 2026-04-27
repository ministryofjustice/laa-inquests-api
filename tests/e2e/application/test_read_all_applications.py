from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers.applications import read_application
from uuid import UUID, uuid4

def test_200_read_all_applications_returns_expected_base_properties_for_each(client, auth_token):
    response = client.get(
        f"/applications",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Authorization": f"Bearer {auth_token}"},
    )

    applications = response.json()
    assert len(applications) == 3
    assert isinstance(applications, list)
    for application in applications:
        assert isinstance(application["application_id"], str)
        assert isinstance(application["created_at"], str)
        assert isinstance(application["updated_at"], str)
        assert isinstance(application["status"], str)
        assert isinstance(application["laa_reference"], str)
        assert isinstance(application["used_delegated_functions"], bool)
        assert isinstance(application["application_type"], str)
        assert isinstance(application["auto_grant"], bool)
        assert isinstance(application["overall_decision"], str)
