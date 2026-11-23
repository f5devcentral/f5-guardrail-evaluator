import json
import re

from test_engine import FakeClient

from guardrail_evaluator.datasets.schemas import Content, ScanResult, Scenario, ScenarioResult
from guardrail_evaluator.engine.metrics import defence_metrics, layer_metrics
from guardrail_evaluator.engine.orchestrator import evaluate
from guardrail_evaluator.reporting.exports import export_run


def row(a, b, input_decision, output_decision, reached=True):
    return ScenarioResult(
        scenario=Scenario(
            id="s",
            input=Content(text="q", expected_unsafe=a),
            simulated_response=Content(text="r", expected_unsafe=b),
        ),
        input_scan=ScanResult(decision=input_decision, latency_ms=10),
        output_scan=ScanResult(decision=output_decision, latency_ms=20),
        output_reached=reached,
    )


def test_confusion_and_missing_labels():
    rows = [
        row(True, True, "blocked", "allowed"),
        row(True, False, "allowed", "allowed"),
        row(False, False, "flagged", "allowed"),
        row(False, False, "allowed", "allowed"),
        row(True, True, "error", "not_executed"),
        row(None, None, "allowed", "allowed"),
    ]
    m = layer_metrics(rows, "input")
    assert [m[k] for k in ("tp", "tn", "fp", "fn")] == [1, 1, 1, 1]
    assert m["precision"]["value"] == 0.5 and m["f1"]["value"] == 0.5
    assert m["error"] == 1 and m["unlabelled"] == 1 and m["latency_ms"]["count"] == 5


def test_zero_denominators_are_na():
    m = layer_metrics([], "input")
    assert m["precision"]["value"] is None and m["recall"]["value"] is None
    assert m["latency_ms"]["p99"] is None
    assert defence_metrics([], "production-path")["combined_prevention_rate"]["value"] is None


def test_defence_population_and_safe_refusals():
    rows = [
        row(True, True, "blocked", "error", False),  # hypothetical error, known production block
        row(False, True, "allowed", "blocked"),
        row(True, True, "flagged", "allowed"),
        row(True, False, "allowed", "allowed"),
        row(True, True, "error", "blocked", False),
        row(False, False, "allowed", "allowed"),
    ]
    m = defence_metrics(rows, "comparison")
    assert m["combined_prevention_rate"] == {"value": 2 / 3, "numerator": 2, "denominator": 3}
    assert m["end_to_end_escape_rate"]["value"] == 1 / 3
    assert m["incremental_response_benefit"]["value"] == 1 / 3
    assert m["additional_output_prevention_reached"]["value"] == 0.5
    assert m["independent_output_prevention_rate"]["value"] == 2 / 3
    assert m["excluded_harmful_response_paths"] == 1


async def test_export_roundtrip_and_safe_html(dataset, tmp_path):
    dataset.scenarios[0].input.text = '<script>alert("evil")</script>'
    dataset.scenarios[0].name = '=HYPERLINK("bad")'
    run = await evaluate(dataset, FakeClient(), "defence-in-depth")
    paths = export_run(run, tmp_path)
    records = [json.loads(line) for line in paths[1].read_text().splitlines()]
    assert records[0]["id"] == run.id and records[0]["scenario"]["input"]["text"].startswith("<script>")
    report = paths[2].read_text()
    assert '<script>alert("evil")</script>' not in report
    assert "&lt;script&gt;" in report and "SIMULATED TEST" in report
    assert "'=HYPERLINK" in paths[0].read_text()
    assert not re.search(r'<script[^>]+src=["\x27]https?://', report)
    assert paths[0].stat().st_mode & 0o077 == 0
