import pytest

from guardrail_evaluator.datasets.loader import Dataset
from guardrail_evaluator.datasets.schemas import Content, Scenario


@pytest.fixture
def scenario():
    return Scenario(
        id="test",
        input=Content(text="request", expected_unsafe=True),
        simulated_response=Content(text="response", expected_unsafe=True),
    )


@pytest.fixture
def dataset(scenario):
    return Dataset("test.jsonl", "a" * 64, [scenario])


def api_body(outcome="cleared", scans=None):
    return {
        "id": "123",
        "redactedInput": "fixture",
        "result": {
            "outcome": outcome,
            "scannerResults": scans
            if scans is not None
            else [
                {
                    "scannerId": "test",
                    "scannerName": "test",
                    "outcome": "passed" if outcome == "cleared" else "failed",
                    "scanDirection": "request",
                    "data": {"type": "regex"},
                }
            ],
        },
    }
