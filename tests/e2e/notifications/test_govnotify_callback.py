"""E2E tests for GovNotify delivery receipt callback endpoint."""

from unittest.mock import patch

import pytest


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
        "reference": "dev-APP-123456",
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
    assert mock_logger.info.call_args[0][0] == "GovNotify callback received"
    log_extra = mock_logger.info.call_args.kwargs["extra"]["extra"]
    assert log_extra["event"] == "govnotify_callback_received"
    assert log_extra["notification_id"] == payload["id"]
    assert log_extra["status"] == payload["status"]
    assert log_extra["recipient_masked"] == "p***@example.com"
    assert "to" not in log_extra


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


def test_200_callback_response_includes_request_and_correlation_ids(
    client, gov_notify_bearer_token
):
    payload = _make_callback_payload()

    response = client.post(
        "/notifications/callback",
        json=payload,
        headers={
            "Authorization": f"Bearer {gov_notify_bearer_token}",
            "x-request-id": "request-123",
            "x-correlation-id": "correlation-456",
        },
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-123"
    assert response.headers["x-correlation-id"] == "correlation-456"


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
    log_extra = mock_logger.info.call_args.kwargs["extra"]["extra"]
    assert log_extra["environment_from_reference"] == "production"
    assert log_extra["laa_reference"] == "APP-999999"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "a" * 65),
        ("id", "a\u200bb"),
        ("reference", "a" * 101),
        ("reference", "dev-APP\n123456"),
        ("reference", "dev-APP\x00123456"),
        ("to", "a" * 255),
        ("to", "provider@example.com\r\nBcc: someone@example.com"),
        ("created_at", "2" * 41),
        ("completed_at", "2026-06-17T12:00:00Z\n"),
        ("sent_at", "2" * 41),
    ],
)
def test_422_callback_rejects_oversized_or_control_character_fields(
    client, gov_notify_bearer_token, field, value
):
    """Fields are bounded and single line, as the body is validated before the token."""
    with patch("app.routers.notifications.logger") as mock_logger:
        response = client.post(
            "/notifications/callback",
            json=_make_callback_payload({field: value}),
            headers={"Authorization": f"Bearer {gov_notify_bearer_token}"},
        )

    assert response.status_code == 422
    mock_logger.info.assert_not_called()


def test_422_callback_rejects_oversized_fields_without_a_bearer_token(client):
    response = client.post(
        "/notifications/callback",
        json=_make_callback_payload({"reference": "a" * 10_000}),
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": "a" * 64},
        {"reference": "a" * 100},
        {"to": "a" * 254},
        {"created_at": "2" * 40, "completed_at": "2" * 40, "sent_at": "2" * 40},
        {"reference": None, "completed_at": None, "sent_at": None},
    ],
)
def test_200_callback_accepts_fields_at_their_limits_and_absent_optional_fields(
    client, gov_notify_bearer_token, overrides
):
    response = client.post(
        "/notifications/callback",
        json=_make_callback_payload(overrides),
        headers={"Authorization": f"Bearer {gov_notify_bearer_token}"},
    )

    assert response.status_code == 200
