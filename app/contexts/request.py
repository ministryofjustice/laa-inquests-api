from contextvars import ContextVar, Token

_REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)
_CORRELATION_ID: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def set_request_context(request_id: str, correlation_id: str) -> tuple[Token, Token]:
    return (_REQUEST_ID.set(request_id), _CORRELATION_ID.set(correlation_id))


def clear_request_context(tokens: tuple[Token, Token]) -> None:
    request_token, correlation_token = tokens
    _REQUEST_ID.reset(request_token)
    _CORRELATION_ID.reset(correlation_token)


def get_request_id() -> str | None:
    return _REQUEST_ID.get()


def get_correlation_id() -> str | None:
    return _CORRELATION_ID.get()
