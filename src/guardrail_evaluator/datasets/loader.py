import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from .mapping import ColumnMapping, detect_columns, parse_label
from .schemas import Content, Mode, Scenario


@dataclass
class Dataset:
    name: str
    sha256: str
    scenarios: list[Scenario] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    mapping: ColumnMapping = field(default_factory=ColumnMapping)


def load_dataset(path, mode=Mode.INPUT, mapping=None, max_bytes=10 * 1024 * 1024):
    path = Path(path)
    mode = Mode(mode)
    if path.suffix.lower() not in (".csv", ".jsonl"):
        raise ValueError("Upload a CSV or JSONL file")
    with path.open("rb") as stream:
        data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("Dataset exceeds the configured file size limit")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Dataset must be UTF-8") from None
    result = Dataset(path.name, hashlib.sha256(data).hexdigest())
    rows = []
    if path.suffix.lower() == ".csv":
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("CSV needs unique column headers")
        result.columns = reader.fieldnames
        try:
            for row in reader:
                rows.append((reader.line_num, row))
        except csv.Error:
            raise ValueError("Malformed CSV") from None
    else:
        for line, raw in enumerate(text.splitlines(), 1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
                if not isinstance(row, dict):
                    raise TypeError()
                rows.append((line, row))
                result.columns = list(dict.fromkeys([*result.columns, *row.keys()]))
            except (ValueError, TypeError):
                result.errors.append({"line": line, "error": "Expected a JSON object"})
    if len(rows) > 10_000:
        raise ValueError("Maximum 10,000 scenarios per run")
    result.mapping = mapping or detect_columns(result.columns, mode)
    seen = set()
    for line, row in rows:
        try:
            if None in row:
                raise ValueError("CSV row has extra fields")

            def content(column, label, row=row):
                if not column or row.get(column) is None or row.get(column) == "":
                    return None
                value = row[column]
                if isinstance(value, dict):
                    return Content(
                        text=value.get("text"), expected_unsafe=parse_label(value.get("expected_unsafe"))
                    )
                if not isinstance(value, str):
                    raise TypeError("Text columns must contain strings")
                return Content(text=value, expected_unsafe=parse_label(row.get(label)) if label else None)

            m = result.mapping
            tags = row.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            metadata = row.get("metadata", {})
            if isinstance(metadata, str):
                metadata = json.loads(metadata) if metadata else {}
            scenario = Scenario(
                id=str(row.get("id") or f"row-{line}"),
                name=row.get("name") or "",
                category=row.get("category") or "uncategorised",
                severity=row.get("severity") or "unspecified",
                input=content(m.input, m.input_label),
                simulated_response=content(m.output, m.output_label),
                tags=tags,
                metadata={**metadata, "source_line": line},
            )
            if mode != Mode.OUTPUT and scenario.input is None:
                raise ValueError("Input text is required for this mode")
            if mode != Mode.INPUT and scenario.simulated_response is None:
                raise ValueError("Response text is required for this mode")
            if scenario.id in seen:
                raise ValueError("Duplicate scenario ID")
            seen.add(scenario.id)
            result.scenarios.append(scenario)
        except (ValidationError, ValueError, TypeError):
            # Never echo untrusted row data in exception text.
            result.errors.append(
                {"line": line, "error": "Invalid text, label, metadata, duplicate ID or missing mode fields"}
            )
    return result
