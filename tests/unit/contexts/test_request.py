from app.contexts.request import (
    clear_request_context,
    get_correlation_id,
    get_request_id,
    set_request_context,
)


def test_request_context_returns_values_until_cleared():
    tokens = set_request_context("request-id", "correlation-id")

    try:
        assert get_request_id() == "request-id"
        assert get_correlation_id() == "correlation-id"
    finally:
        clear_request_context(tokens)

    assert get_request_id() is None
    assert get_correlation_id() is None
