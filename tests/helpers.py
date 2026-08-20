import csv
import io


def parse_csv_rows(content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(content)))


def parse_csv_fieldnames(content: str) -> list[str]:
    reader = csv.DictReader(io.StringIO(content))
    return reader.fieldnames or []
