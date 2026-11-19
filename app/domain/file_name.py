import re

MAX_FILE_NAME_LENGTH = 255

# Mirrors the external UI's client-side rule, which a crafted request can bypass.
_FILE_NAME_PATTERN = re.compile(r"[A-Za-z0-9.!()_ \-]+")


def is_valid_upload_file_name(file_name: str | None) -> bool:
    """Whether an uploaded file name is safe to store and later render or echo in a header."""
    if not file_name or len(file_name) > MAX_FILE_NAME_LENGTH:
        return False
    return _FILE_NAME_PATTERN.fullmatch(file_name) is not None
