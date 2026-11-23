import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from guardrail_evaluator.datasets.loader import load_dataset
from guardrail_evaluator.datasets.mapping import ColumnMapping, parse_label
from guardrail_evaluator.datasets.schemas import Content


@pytest.mark.parametrize(
    "value,expected",
    [("true", True), ("0", False), ("attack", True), ("benign", False), ("", None), (None, None)],
)
def test_labels(value, expected):
    assert parse_label(value) is expected


def test_strict_unknown_label():
    with pytest.raises(ValueError):
        parse_label("maybe unsafe")
    with pytest.raises(ValidationError):
        Content(text="sample", expected_unsafe="false")


def test_input_only_unlabelled(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text('prompt\n"ordinary request"\n')
    d = load_dataset(p)
    assert len(d.scenarios) == 1 and not d.errors
    assert d.scenarios[0].simulated_response is None
    assert d.scenarios[0].input.expected_unsafe is None


def test_manual_mapping_and_output_label(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text('answer,truth\n"a response",safe\n')
    d = load_dataset(p, "output", ColumnMapping(output="answer", output_label="truth"))
    assert d.scenarios[0].simulated_response.expected_unsafe is False
    assert not d.scenarios[0].input


def test_output_autodetection(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("completion,label\nfixture,unsafe\n")
    assert load_dataset(p, "output").scenarios[0].simulated_response.expected_unsafe is True


def test_malformed_rows_and_duplicate_ids(tmp_path, scenario):
    p = tmp_path / "data.jsonl"
    p.write_text(scenario.model_dump_json() + "\nBAD JSON\n[]\n" + scenario.model_dump_json())
    d = load_dataset(p, "defence-in-depth")
    assert len(d.scenarios) == 1 and len(d.errors) == 3
    assert [r["line"] for r in d.errors] == [2, 3, 4]


def test_no_paired_label_inference(tmp_path):
    p = tmp_path / "data.jsonl"
    p.write_text(json.dumps({"prompt": "request", "response": "refusal", "label": "unsafe"}))
    s = load_dataset(p, "defence-in-depth").scenarios[0]
    assert s.input.expected_unsafe is True
    assert s.simulated_response.expected_unsafe is None


def test_limits_and_missing_fields(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("prompt\nrequest\n")
    with pytest.raises(ValueError):
        load_dataset(p, max_bytes=2)
    assert len(load_dataset(p, "defence-in-depth").errors) == 1


def test_sample_library():
    root = Path(__file__).resolve().parents[1]
    d = load_dataset(root / "datasets/paired_scenarios.jsonl", "defence-in-depth")
    assert not d.errors and len(d.scenarios) >= 100
    assert len({s.category for s in d.scenarios}) == 9
