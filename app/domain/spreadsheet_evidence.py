"""Rules for which spreadsheets may be stored as claim evidence.

Only macro-free .xlsx workbooks are accepted. A file is treated as a spreadsheet
if it has an Excel extension or its bytes look like an Office container, so a
workbook cannot bypass the check by being renamed. Other files are not inspected.
"""

import io
import zipfile
from enum import StrEnum

_XLSX_EXTENSION = ".xlsx"
_EXCEL_EXTENSIONS = frozenset(
    {".xlsx", ".xls", ".xlsm", ".xlsb", ".xltx", ".xltm", ".xlam", ".xlt", ".xla"}
)
_ZIP_MAGIC = b"PK\x03\x04"
_OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

_CONTENT_TYPES_PART = "[content_types].xml"
_WORKBOOK_PART = "xl/workbook.xml"
_VBA_PROJECT_SUFFIX = "vbaproject.bin"
_MACRO_PART_PREFIXES = ("xl/macrosheets/", "xl/dialogsheets/")
_MACRO_CONTENT_TYPE_MARKERS = (
    b"macroenabled",
    b"vnd.ms-office.vbaproject",
    b"vnd.ms-excel.macrosheet",
    b"vnd.ms-excel.intlmacrosheet",
)
_MAX_ZIP_ENTRIES = 10_000
_MAX_CONTENT_TYPES_BYTES = 1024 * 1024


class SpreadsheetRejectionCode(StrEnum):
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    CONTENT_MISMATCH = "CONTENT_MISMATCH"
    INVALID_SPREADSHEET = "INVALID_SPREADSHEET"
    MACROS_NOT_ALLOWED = "MACROS_NOT_ALLOWED"


_MESSAGES = {
    SpreadsheetRejectionCode.UNSUPPORTED_FILE_TYPE: "Only .xlsx spreadsheets are allowed",
    SpreadsheetRejectionCode.CONTENT_MISMATCH: "File content does not match its file extension",
    SpreadsheetRejectionCode.INVALID_SPREADSHEET: "File is not a valid .xlsx workbook",
    SpreadsheetRejectionCode.MACROS_NOT_ALLOWED: "Macro-enabled spreadsheets are not allowed",
}


class SpreadsheetRejectedError(Exception):
    """The message never contains the file name, so it is safe to log and return."""

    def __init__(self, code: SpreadsheetRejectionCode) -> None:
        self.code = code
        self.message = _MESSAGES[code]
        super().__init__(self.message)


def check_spreadsheet_evidence(file_name: str, content: bytes) -> None:
    extension = _extension(file_name)
    is_excel_extension = extension in _EXCEL_EXTENSIONS
    is_office_container = content.startswith((_ZIP_MAGIC, _OLE2_MAGIC))
    if not is_excel_extension and not is_office_container:
        return
    if is_excel_extension and extension != _XLSX_EXTENSION:
        raise SpreadsheetRejectedError(SpreadsheetRejectionCode.UNSUPPORTED_FILE_TYPE)
    if extension != _XLSX_EXTENSION or not content.startswith(_ZIP_MAGIC):
        raise SpreadsheetRejectedError(SpreadsheetRejectionCode.CONTENT_MISMATCH)
    _check_xlsx_is_macro_free(content)


def _extension(file_name: str) -> str:
    dot = file_name.rfind(".")
    return file_name[dot:].lower() if dot != -1 else ""


def _check_xlsx_is_macro_free(content: bytes) -> None:
    invalid = SpreadsheetRejectedError(SpreadsheetRejectionCode.INVALID_SPREADSHEET)
    macros = SpreadsheetRejectedError(SpreadsheetRejectionCode.MACROS_NOT_ALLOWED)
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            # infolist() reads only the zip directory; nothing is decompressed.
            entries = archive.infolist()
            if len(entries) > _MAX_ZIP_ENTRIES:
                raise invalid
            parts = {entry.filename.lower(): entry for entry in entries}
            if _CONTENT_TYPES_PART not in parts or _WORKBOOK_PART not in parts:
                raise invalid
            if any(
                name.endswith(_VBA_PROJECT_SUFFIX)
                or name.startswith(_MACRO_PART_PREFIXES)
                for name in parts
            ):
                raise macros
            content_types_entry = parts[_CONTENT_TYPES_PART]
            if content_types_entry.file_size > _MAX_CONTENT_TYPES_BYTES:
                raise invalid
            with archive.open(content_types_entry) as handle:
                content_types = handle.read(_MAX_CONTENT_TYPES_BYTES + 1).lower()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError) as e:
        raise invalid from e

    # The declared size can lie, so also cap what was actually decompressed.
    if len(content_types) > _MAX_CONTENT_TYPES_BYTES:
        raise invalid
    if any(marker in content_types for marker in _MACRO_CONTENT_TYPE_MARKERS):
        raise macros
