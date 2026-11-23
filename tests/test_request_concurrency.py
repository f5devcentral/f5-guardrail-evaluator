"""Measure outstanding HTTP calls, rather than only the number of scenario workers."""

import asyncio
import json

import httpx
import pytest
from conftest import api_body

from guardrail_evaluator.api.f5_client import F5Client, ScanOptions
from guardrail_evaluator.config import Settings
from guardrail_evaluator.engine.orchestrator import Cancellation, evaluate


class ObservedTransport:
    def __init__(self):
        self.active = 0
        self.maximum = 0
        self.events = []

    async def handle(self, request):
        payload = json.loads(request.content)
        key = (payload["input"], payload["scanDirection"])
        self.active += 1
        self.maximum = max(self.maximum, self.active)
        self.events.append(("start", key))
        try:
            # Yield while the HTTP call is outstanding so accidental overlaps are observable.
            await asyncio.sleep(0.005)
            body = api_body()
            body["result"]["scannerResults"][0]["scanDirection"] = payload["scanDirection"]
            return httpx.Response(200, json=body)
        finally:
            self.events.append(("finish", key))
            self.active -= 1


@pytest.mark.parametrize("concurrency", [1, 3])
@pytest.mark.parametrize(
    "mode,strategy,directions",
    [
        ("input", "production-path", ["request"]),
        ("output", "production-path", ["response"]),
        ("defence-in-depth", "production-path", ["request", "response"]),
        ("defence-in-depth", "independent", ["request", "response"]),
        ("defence-in-depth", "comparison", ["request", "response"]),
    ],
)
async def test_http_requests_respect_run_concurrency(dataset, concurrency, mode, strategy, directions):
    scenarios = []
    for index in range(6):
        scenario = dataset.scenarios[0].model_copy(deep=True)
        scenario.id = str(index)
        scenario.input.text = f"input-{index}"
        scenario.simulated_response.text = f"output-{index}"
        scenarios.append(scenario)
    dataset.scenarios = scenarios
    observer = ObservedTransport()
    cfg = Settings(_env_file=None, token="concurrency-test-secret", concurrency=concurrency, retries=0)
    # MockTransport does not impose httpx's connection-pool limit: this catches engine overlap too.
    async with F5Client(cfg, transport=httpx.MockTransport(observer.handle)) as client:
        run = await evaluate(dataset, client, mode, strategy, concurrency=concurrency)

    assert run.status == "completed"
    assert observer.maximum == concurrency
    assert observer.active == 0
    assert len(observer.events) == 2 * len(scenarios) * len(directions)
    if concurrency == 1:
        expected = []
        for index in range(len(scenarios)):
            for direction in directions:
                text = f"input-{index}" if direction == "request" else f"output-{index}"
                expected.extend([("start", (text, direction)), ("finish", (text, direction))])
        assert observer.events == expected


async def test_evaluate_slider_one_overrides_saved_default(monkeypatch, tmp_path):
    from guardrail_evaluator.ui import app as ui

    path = tmp_path / "prompts.csv"
    path.write_text("prompt\nfirst\nsecond\nthird\n", encoding="utf-8")
    observer = ObservedTransport()
    captured = []

    def client_factory(settings, options):
        captured.append(settings.concurrency)
        return F5Client(settings, transport=httpx.MockTransport(observer.handle), options=options)

    monkeypatch.setattr(ui, "F5Client", client_factory)
    app = ui.build_app()
    try:
        event = next(item for item in app.fns.values() if item.fn.__name__ == "run_evaluation")
        assert event.inputs[5].label.startswith("Concurrent scenarios")
        result = await event.fn(
            file=str(path),
            selected="Synthetic benchmark · 108",
            selected_mode="input",
            selected_source="Live API Mode",
            selected_project="",
            workers=1,
            selected_strategy="production-path",
            allow_invalid=False,
            cfg=Settings(_env_file=None, token="concurrency-test-secret", concurrency=5, persist=False),
            opts=ScanOptions(),
            cancel=Cancellation(),
            input_col="Auto",
            output_col="Auto",
            input_label="Auto",
            output_label="Auto",
            progress=lambda *args, **kwargs: None,
        )
    finally:
        app.close()

    assert captured == [1]
    assert result[0].config["concurrency"] == 1
    assert result[0].status == "completed"
    assert observer.maximum == 1
    assert [kind for kind, _ in observer.events] == ["start", "finish"] * 3
