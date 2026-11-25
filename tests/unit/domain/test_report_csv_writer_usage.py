import re
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[3] / "app"
ALLOWED_RAW_CSV_WRITER_FILES = {APP_DIR / "domain" / "csv_safety.py"}


def test_reports_write_csv_only_through_safe_csv_writer():
    offenders = [
        str(path.relative_to(APP_DIR))
        for path in APP_DIR.rglob("*.py")
        if path not in ALLOWED_RAW_CSV_WRITER_FILES
        and re.search(r"\bcsv\.(writer|DictWriter)\(", path.read_text())
    ]

    assert offenders == []
