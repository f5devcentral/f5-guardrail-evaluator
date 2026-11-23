import asyncio

import pytest
from conftest import api_body

from guardrail_evaluator.datasets.schemas import Decision, ScanResult
from guardrail_evaluator.engine.decisions import normalize_response
from guardrail_evaluator.engine.orchestrator import Cancellation, evaluate


class FakeClient:
    source = "SIMULATED TEST"

    def __init__(self, outcomes=("cleared", "blocked")):
        self.calls = []
        self.outcomes = outcomes

    async def scan(self, text, direction, **kwargs):
        self.calls.append((direction, kwargs))
        outcome = self.outcomes[direction == "response"]
        return (
            ScanResult(decision=Decision.ERROR, error="fixture_error")
            if outcome == "error"
            else normalize_response(api_body(outcome), 10)
        )


@pytest.mark.parametrize("mode,directions", [("input", ["request"]), ("output", ["response"])])
async def test_single_layer(dataset, mode, directions):
    c = FakeClient()
    await evaluate(dataset, c, mode)
    assert [d for d, _ in c.calls] == directions


@pytest.mark.parametrize("strategy,count", [("production-path", 1), ("independent", 2), ("comparison", 2)])
async def test_input_blocked_paths(dataset, strategy, count):
    c = FakeClient(("blocked", "blocked"))
    run = await evaluate(dataset, c, "defence-in-depth", strategy)
    r = run.results[0]
    assert len(c.calls) == count and r.final == "input_prevention"
    assert r.output_hypothetical is (count == 2)
    assert not r.output_reached


async def test_flag_is_not_block(dataset):
    c = FakeClient(("flagged", "blocked"))
    r = (await evaluate(dataset, c, "defence-in-depth")).results[0]
    assert len(c.calls) == 2 and r.final == "additional_output_prevention"
    assert c.calls[1][1]["request_id"] == "123"


@pytest.mark.parametrize(
    "input_label,output_label,output_decision,final",
    [
        (True, False, "cleared", "safe_response"),
        (False, True, "blocked", "additional_output_prevention"),
        (False, False, "cleared", "allowed_safe_interaction"),
        (True, True, "cleared", "potential_escape"),
        (False, False, "blocked", "output_false_positive"),
    ],
)
async def test_final_classification(dataset, input_label, output_label, output_decision, final):
    dataset.scenarios[0].input.expected_unsafe = input_label
    dataset.scenarios[0].simulated_response.expected_unsafe = output_label
    run = await evaluate(dataset, FakeClient(("cleared", output_decision)), "defence-in-depth")
    assert run.results[0].final == final


async def test_error_stops_production(dataset):
    c = FakeClient(("error", "cleared"))
    run = await evaluate(dataset, c, "defence-in-depth")
    assert len(c.calls) == 1 and run.results[0].final == "input_error"
    assert run.status == "completed_with_errors"


async def test_concurrency_order_and_progress(dataset):
    dataset.scenarios = [dataset.scenarios[0].model_copy(update={"id": str(i)}) for i in range(10)]

    class Slow(FakeClient):
        active = maximum = 0

        async def scan(self, *args, **kwargs):
            self.active += 1
            self.maximum = max(self.maximum, self.active)
            await asyncio.sleep(0.003 * (10 - int(kwargs["scenario"].id)))
            self.active -= 1
            return await super().scan(*args, **kwargs)

    c = Slow()
    progress = []
    run = await evaluate(dataset, c, concurrency=3, progress=lambda n, total, r: progress.append(n))
    assert c.maximum == 3
    assert [r.scenario.id for r in run.results] == [str(i) for i in range(10)]
    assert progress == list(range(1, 11))


async def test_cancel_skips_output_and_remaining(dataset):
    dataset.scenarios *= 4
    cancel = Cancellation()

    class Cancelling(FakeClient):
        async def scan(self, *args, **kwargs):
            cancel.cancel()
            return await super().scan(*args, **kwargs)

    c = Cancelling()
    run = await evaluate(dataset, c, "defence-in-depth", concurrency=1, cancel=cancel)
    assert len(c.calls) == 1 and run.status == "cancelled"
    assert all(r.status == "cancelled" for r in run.results)
