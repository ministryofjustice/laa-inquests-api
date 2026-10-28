from app.contexts.user import (
    clear_entra_user_context,
    get_entra_user_email_address,
    get_entra_user_name,
    get_entra_user_object_id,
    set_entra_user_context,
)


def test_user_context_returns_values_until_cleared():
    set_entra_user_context("entra-object-id", "Test Name")

    try:
        assert get_entra_user_object_id() == "entra-object-id"
        assert get_entra_user_name() == "Test Name"
    finally:
        clear_entra_user_context()

    assert get_entra_user_object_id() is None
    assert get_entra_user_name() is None


def test_user_context_returns_email_address_until_cleared():
    set_entra_user_context("entra-object-id", "Test Name", "user@example.com")

    try:
        assert get_entra_user_email_address() == "user@example.com"
    finally:
        clear_entra_user_context()

    assert get_entra_user_email_address() is None


def test_user_context_email_address_defaults_to_none():
    set_entra_user_context("entra-object-id", "Test Name")

    try:
        assert get_entra_user_email_address() is None
    finally:
        clear_entra_user_context()
