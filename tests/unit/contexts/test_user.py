from app.contexts.user import (
    clear_entra_user_context,
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
