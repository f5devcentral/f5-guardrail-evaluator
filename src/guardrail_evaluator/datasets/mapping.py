from pydantic import BaseModel


class ColumnMapping(BaseModel):
    input: str | None = None
    output: str | None = None
    input_label: str | None = None
    output_label: str | None = None


def detect_columns(columns, mode="input"):
    lookup = {str(c).strip().lower(): c for c in columns}

    def pick(*names):
        return next((lookup[n] for n in names if n in lookup), None)

    generic = pick("expected_unsafe", "label", "expected", "is_unsafe", "is_malicious")
    return ColumnMapping(
        input=pick("prompt", "input", "text"),
        output=pick(
            "simulated_response", "response", "output", "completion", *(["text"] if mode == "output" else [])
        ),
        input_label=pick("input_expected_unsafe", "input_label") or (generic if mode != "output" else None),
        output_label=pick("output_expected_unsafe", "output_label", "response_label")
        or (generic if mode == "output" else None),
    )


def parse_label(value):
    if value is None or str(value).strip().lower() in ("", "null", "none", "n/a", "unknown"):
        return None
    value = str(value).strip().lower()
    if value in ("true", "1", "yes", "y", "unsafe", "malicious", "attack", "injection", "flagged", "blocked"):
        return True
    if value in ("false", "0", "no", "n", "safe", "benign", "normal", "cleared", "allowed"):
        return False
    raise ValueError("Unrecognised label; use safe/unsafe, true/false or 0/1")
