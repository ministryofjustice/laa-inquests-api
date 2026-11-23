BOUNDARY = "test-boundary-7d1f"

# Characters that make a file name unsafe to render as HTML or to place in a header.
UNSAFE_FILE_NAMES = [
    "<img src=x onerror='document.title=666'>.pdf",
    '<a href="//evil.example">click</a>.pdf',
    "letter<script>.pdf",
    'letter".pdf',
    "letter>.pdf",
    "letter\\evil.pdf",
    "folder/letter.pdf",
    "letter\x00.pdf",
    "letter\t.pdf",
    "\uff1cscript\uff1e.pdf",
    "a" * 252 + ".pdf",
]


def raw_file_upload(
    client,
    url: str,
    file_name: str,
    headers: dict,
    fields: dict[str, str] | None = None,
):
    """Send a multipart upload with the file name written verbatim.

    httpx percent-encodes quotes and control characters in file names, so
    a hand-built body is needed to reproduce a crafted request.
    """
    form_fields = "".join(
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
        f"{value}\r\n"
        for name, value in (fields or {}).items()
    )
    body = (
        form_fields + f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
        "test content\r\n"
        f"--{BOUNDARY}--\r\n"
    ).encode()
    return client.post(
        url,
        content=body,
        headers={
            **headers,
            "Content-Type": f"multipart/form-data; boundary={BOUNDARY}",
        },
    )
