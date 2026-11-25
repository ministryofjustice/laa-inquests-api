import io
import zipfile

XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="{workbook_content_type}"/>'
    "{extra_overrides}</Types>"
)
_PLAIN_WORKBOOK_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
)
_MACRO_WORKBOOK_CONTENT_TYPE = "application/vnd.ms-excel.sheet.macroEnabled.main+xml"
_VBA_PROJECT_OVERRIDE = (
    '<Override PartName="/xl/vbaProject.bin" '
    'ContentType="application/vnd.ms-office.vbaProject"/>'
)


def build_xlsx(
    *,
    workbook_content_type: str = _PLAIN_WORKBOOK_CONTENT_TYPE,
    extra_overrides: str = "",
    extra_parts: tuple[tuple[str, bytes], ...] = (),
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            _CONTENT_TYPES.format(
                workbook_content_type=workbook_content_type,
                extra_overrides=extra_overrides,
            ),
        )
        archive.writestr("xl/workbook.xml", "<workbook/>")
        for name, data in extra_parts:
            archive.writestr(name, data)
    return buffer.getvalue()


PLAIN_XLSX = build_xlsx()
MACRO_XLSX = build_xlsx(
    workbook_content_type=_MACRO_WORKBOOK_CONTENT_TYPE,
    extra_overrides=_VBA_PROJECT_OVERRIDE,
    extra_parts=(("xl/vbaProject.bin", b"\xd0\xcf\x11\xe0vba"),),
)
MACRO_CONTENT_TYPE_ONLY_XLSX = build_xlsx(
    workbook_content_type=_MACRO_WORKBOOK_CONTENT_TYPE
)
VBA_PROJECT_ONLY_XLSX = build_xlsx(extra_parts=(("xl/vbaProject.bin", b"vba"),))
UPPERCASE_VBA_PROJECT_XLSX = build_xlsx(extra_parts=(("XL/VBAPROJECT.BIN", b"vba"),))
MACRO_SHEET_XLSX = build_xlsx(
    extra_parts=(("xl/macrosheets/sheet1.xml", b"<worksheet/>"),)
)
DIALOG_SHEET_XLSX = build_xlsx(
    extra_parts=(("xl/dialogsheets/sheet1.xml", b"<dialogsheet/>"),)
)
OLE2_XLS = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 512


def build_zip(parts: tuple[tuple[str, bytes], ...]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in parts:
            archive.writestr(name, data)
    return buffer.getvalue()
