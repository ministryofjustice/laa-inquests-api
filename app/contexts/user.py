from contextvars import ContextVar, Token

_ENTRA_USER_OBJECT_ID: ContextVar[str | None] = ContextVar(
    "entra_user_object_id", default=None
)
_ENTRA_USER_NAME: ContextVar[str | None] = ContextVar("entra_user_name", default=None)
_ENTRA_USER_EMAIL_ADDRESS: ContextVar[str | None] = ContextVar(
    "entra_user_email_address", default=None
)


def set_entra_user_context(
    entra_object_id: str | None, name: str | None, email_address: str | None = None
) -> tuple[Token, Token, Token]:
    return (
        _ENTRA_USER_OBJECT_ID.set(entra_object_id),
        _ENTRA_USER_NAME.set(name),
        _ENTRA_USER_EMAIL_ADDRESS.set(email_address),
    )


def clear_entra_user_context() -> None:
    _ENTRA_USER_OBJECT_ID.set(None)
    _ENTRA_USER_NAME.set(None)
    _ENTRA_USER_EMAIL_ADDRESS.set(None)


def get_entra_user_object_id() -> str | None:
    return _ENTRA_USER_OBJECT_ID.get()


def get_entra_user_name() -> str | None:
    return _ENTRA_USER_NAME.get()


def get_entra_user_email_address() -> str | None:
    return _ENTRA_USER_EMAIL_ADDRESS.get()
