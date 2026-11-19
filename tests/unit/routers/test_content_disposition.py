import pytest

from app.routers.content_disposition import content_disposition


def test_leaves_a_safe_file_name_unchanged():
    assert (
        content_disposition("inline", "Letter (1).pdf")
        == 'inline; filename="Letter (1).pdf"'
    )


@pytest.mark.parametrize(
    "file_name",
    ['x".pdf', 'x"; filename="evil.exe', "x\r\nX-Injected: 1.pdf", "x\\y.pdf", "é.pdf"],
)
def test_neutralises_characters_that_could_break_out_of_the_header(file_name):
    value = content_disposition("attachment", file_name)

    plain_name = value.split('filename="', 1)[1].split('"', 1)[0]
    assert all(char not in plain_name for char in '"\\\r\n;')
    assert "\r" not in value
    assert "\n" not in value
    assert value.count('filename="') == 1
    assert "filename*=UTF-8''" in value
