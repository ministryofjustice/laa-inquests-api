import pytest

from app.domain.spreadsheet_evidence import (
    SpreadsheetRejectedError,
    SpreadsheetRejectionCode,
    check_spreadsheet_evidence,
)
from tests.helpers.spreadsheet_files import (
    DIALOG_SHEET_XLSX,
    MACRO_CONTENT_TYPE_ONLY_XLSX,
    MACRO_SHEET_XLSX,
    MACRO_XLSX,
    OLE2_XLS,
    PLAIN_XLSX,
    UPPERCASE_VBA_PROJECT_XLSX,
    VBA_PROJECT_ONLY_XLSX,
    build_xlsx,
    build_zip,
)


def _rejection_code(file_name: str, content: bytes) -> SpreadsheetRejectionCode:
    with pytest.raises(SpreadsheetRejectedError) as exc_info:
        check_spreadsheet_evidence(file_name, content)
    return exc_info.value.code


@pytest.mark.parametrize("file_name", ["template.xlsx", "Template.XLSX"])
def test_accepts_macro_free_xlsx(file_name):
    check_spreadsheet_evidence(file_name, PLAIN_XLSX)


@pytest.mark.parametrize(
    ("file_name", "content"),
    [
        ("evidence.pdf", b"%PDF-1.7\n..."),
        ("photo.png", b"\x89PNG\r\n\x1a\n..."),
        ("photo.jpg", b"\xff\xd8\xff\xe0..."),
        ("scan.bmp", b"BM..."),
        ("evidence.pdf", b"test content"),
    ],
)
def test_does_not_inspect_files_that_are_not_spreadsheets(file_name, content):
    check_spreadsheet_evidence(file_name, content)


@pytest.mark.parametrize(
    "content",
    [
        MACRO_XLSX,
        MACRO_CONTENT_TYPE_ONLY_XLSX,
        VBA_PROJECT_ONLY_XLSX,
        UPPERCASE_VBA_PROJECT_XLSX,
        MACRO_SHEET_XLSX,
        DIALOG_SHEET_XLSX,
        build_xlsx(extra_parts=(("xl/nested/vbaProject.bin", b"vba"),)),
    ],
    ids=[
        "vba_project_and_macro_content_type",
        "macro_content_type_only",
        "vba_project_only",
        "uppercase_vba_project",
        "excel_4_macro_sheet",
        "dialog_sheet",
        "vba_project_in_other_folder",
    ],
)
def test_rejects_xlsx_containing_macros(content):
    assert (
        _rejection_code("template.xlsx", content)
        is SpreadsheetRejectionCode.MACROS_NOT_ALLOWED
    )


@pytest.mark.parametrize(
    "file_name",
    [
        "template.xls",
        "template.xlsm",
        "template.xlsb",
        "template.xltx",
        "template.xltm",
        "template.xlam",
        "template.xlt",
        "template.xla",
        "TEMPLATE.XLSM",
    ],
)
def test_rejects_excel_formats_other_than_xlsx(file_name):
    assert (
        _rejection_code(file_name, PLAIN_XLSX)
        is SpreadsheetRejectionCode.UNSUPPORTED_FILE_TYPE
    )


@pytest.mark.parametrize(
    ("file_name", "content"),
    [
        ("evidence.pdf", MACRO_XLSX),
        ("evidence.pdf", PLAIN_XLSX),
        ("photo.png", OLE2_XLS),
        ("template", PLAIN_XLSX),
        ("template.xlsx", b"test content"),
        ("template.xlsx", b"%PDF-1.7"),
        ("template.xlsx", OLE2_XLS),
        ("template.xlsx", b""),
    ],
    ids=[
        "macro_workbook_renamed_to_pdf",
        "workbook_renamed_to_pdf",
        "legacy_office_file_renamed_to_png",
        "workbook_without_extension",
        "xlsx_name_with_text_content",
        "xlsx_name_with_pdf_content",
        "xlsx_name_with_legacy_office_content",
        "xlsx_name_with_empty_content",
    ],
)
def test_rejects_content_that_does_not_match_extension(file_name, content):
    assert (
        _rejection_code(file_name, content) is SpreadsheetRejectionCode.CONTENT_MISMATCH
    )


@pytest.mark.parametrize(
    "content",
    [
        b"PK\x03\x04garbage",
        build_zip((("readme.txt", b"hi"),)),
        build_zip((("[Content_Types].xml", b"<Types/>"),)),
        build_zip((("xl/workbook.xml", b"<workbook/>"),)),
    ],
    ids=[
        "corrupt_zip",
        "zip_without_workbook_parts",
        "zip_without_workbook",
        "zip_without_content_types",
    ],
)
def test_rejects_zip_that_is_not_a_valid_workbook(content):
    assert (
        _rejection_code("template.xlsx", content)
        is SpreadsheetRejectionCode.INVALID_SPREADSHEET
    )


def test_rejects_workbook_with_too_many_entries():
    parts = tuple((f"xl/media/{index}.xml", b"") for index in range(10_001))
    content = build_xlsx(extra_parts=parts)

    assert (
        _rejection_code("template.xlsx", content)
        is SpreadsheetRejectionCode.INVALID_SPREADSHEET
    )


def test_rejects_workbook_with_oversized_content_types_part():
    content = build_xlsx(extra_overrides="<!--" + "x" * (1024 * 1024) + "-->")

    assert (
        _rejection_code("template.xlsx", content)
        is SpreadsheetRejectionCode.INVALID_SPREADSHEET
    )


def test_rejection_message_does_not_contain_file_name():
    with pytest.raises(SpreadsheetRejectedError) as exc_info:
        check_spreadsheet_evidence("Jane Doe passport.xlsx", MACRO_XLSX)

    assert "Jane" not in str(exc_info.value)
    assert "Jane" not in exc_info.value.message
