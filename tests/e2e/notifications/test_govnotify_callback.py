"""E2E tests for GovNotify delivery receipt callback endpoint."""

import pytest
from unittest.mock import patch


@pytest.fixture
def gov_notify_bearer_token():
    """Fixture providing the expected GovNotify callback bearer token."""
    return "test-gov-notify-bearer-token"


@pytest.fixture(autouse=True)
def mock_bearer_token(gov_notify_bearer_token):
    """Mock the Config.GOV_NOTIFY_CALLBACK_BEARER_TOKEN for all tests."""
    with patch(
        "app.routers.notifications.Config.GOV_NOTIFY_CALLBACK_BEARER_TOKEN",
        gov_notify_bearer_token,
    ):
        yield


def _make_callback_payload(overrides=None):
    """Helper to create a valid GovNotify callback payload."""
    payload = {
        "id": "740e5834-3a29-46b4-9a6f-16142fde533a",
        "reference": "uat-APP-123456",
        "to": "provider@example.com",
        "status": "delivered",
        "created_at": "2026-06-17T12:00:00.000000Z",
        "completed_at": "2026-06-17T12:01:00.000000Z",
        "sent_at": "2026-06-17T12:00:30.000000Z",
        "notification_type": "email",
    }
    if overrides:
        payload.update(overrides)
    return payload


def test_200_callback_accepts_valid_bearer_token_and_payload(
    client, gov_notify_bearer_token
):
    """Test callback endpoint accepts valid bearer token and logs delivery status."""
    payload = _make_callback_payload()

    with patch("app.routers.notifications.logger") as mock_logger:
        response = client.post(
            "/notifications/callback",
            json=payload,
            headers={"Authorization": f"Bearer {gov_notify_bearer_token}"},
        )

    assert response.status_code == 200

    mock_logger.info.assert_called_once()
    log_call = mock_logger.info.call_args[0][0]
    assert "GovNotify callback received" in log_call
    assert payload["id"] in log_call
    assert payload["status"] in log_call


def test_401_callback_rejects_invalid_bearer_token(client, gov_notify_bearer_token):
    """Test callback endpoint rejects requests with invalid bearer token."""
    payload = _make_callback_payload()

    response = client.post(
        "/notifications/callback",
        json=payload,
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid bearer token"}


def test_401_callback_rejects_missing_bearer_token(client):
    """Test callback endpoint rejects requests without bearer token."""
    payload = _make_callback_payload()

    response = client.post(
        "/notifications/callback",
        json=payload,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing authorization header"}


def test_422_callback_rejects_invalid_payload_missing_required_fields(
    client, gov_notify_bearer_token
):
    """Test callback endpoint rejects payload with missing required fields."""
    payload = {"id": "test-id"}

    response = client.post(
        "/notifications/callback",
        json=payload,
        headers={"Authorization": f"Bearer {gov_notify_bearer_token}"},
    )

    assert response.status_code == 422


def test_200_callback_logs_all_delivery_statuses(client, gov_notify_bearer_token):
    """Test callback endpoint accepts and logs all GovNotify delivery statuses."""
    statuses = [
        "created",
        "sending",
        "sent",
        "delivered",
        "permanent-failure",
        "temporary-failure",
        "technical-failure",
    ]

    for status in statuses:
        payload = _make_callback_payload({"status": status})

        with patch("app.routers.notifications.logger") as mock_logger:
            response = client.post(
                "/notifications/callback",
                json=payload,
                headers={"Authorization": f"Bearer {gov_notify_bearer_token}"},
            )

        assert response.status_code == 200, f"Failed for status: {status}"
        mock_logger.info.assert_called_once()


def test_200_callback_extracts_environment_and_reference_from_reference_field(
    client, gov_notify_bearer_token
):
    """Test callback endpoint extracts environment and LAA reference from reference field."""
    payload = _make_callback_payload({"reference": "production-APP-999999"})

    with patch("app.routers.notifications.logger") as mock_logger:
        response = client.post(
            "/notifications/callback",
            json=payload,
            headers={"Authorization": f"Bearer {gov_notify_bearer_token}"},
        )

    assert response.status_code == 200
    log_call = mock_logger.info.call_args[0][0]
    assert "production" in log_call
    assert "APP-999999" in log_call
