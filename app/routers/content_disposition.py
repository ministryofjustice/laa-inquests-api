import re
from urllib.parse import quote

_UNSAFE_HEADER_CHARS = re.compile(r"[^A-Za-z0-9.!()_ \-]")


def content_disposition(disposition: str, file_name: str) -> str:
    """Build a Content-Disposition value that a stored file name cannot break out of.

    Names already limited to safe characters are emitted unchanged. Anything else
    is replaced in the plain `filename` and sent in full as RFC 5987 `filename*`.
    """
    safe_name = _UNSAFE_HEADER_CHARS.sub("_", file_name)
    value = f'{disposition}; filename="{safe_name}"'
    if safe_name != file_name:
        value += f"; filename*=UTF-8''{quote(file_name, safe='')}"
    return value
