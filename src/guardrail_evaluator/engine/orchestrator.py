import asyncio
import logging
import threading

from ..datasets.schemas import Decision, Mode, Run, ScanResult, ScenarioResult, Strategy
from ..security import redact
from .decisions import classify

log = logging.getLogger("guardrail_evaluator")


class Cancellation:
    """Thread-safe cooperative cancellation; in-flight HTTP calls finish within timeout."""

    def __init__(self):
        self.event = threading.Event()

    def cancel(self):
        self.event.set()

    @property
    def cancelled(self):
        return self.event.is_set()

    def __deepcopy__(self, memo):
        return Cancellation()


async def safe_scan(client, content, direction, scenario, run_id, request_id=None):
    try:
        return await client.scan(
            content.text, direction, scenario=scenario, run_id=run_id, request_id=request_id
        )
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001 — a failed client must remain a per-scenario error
        return ScanResult(decision=Decision.ERROR, error="unexpected_client_error")


async def evaluate_scenario(client, scenario, mode, strategy, run_id, cancel):
    result = ScenarioResult(scenario=scenario)
    if cancel.cancelled:
        result.status = "cancelled"
        return result
    if mode != Mode.OUTPUT:
        result.input_scan = await safe_scan(client, scenario.input, "request", scenario, run_id)
    a = result.input_scan
    should_output = mode == Mode.OUTPUT or (
        mode == Mode.PAIRED
        and (strategy != Strategy.PRODUCTION or a.decision in (Decision.ALLOWED, Decision.FLAGGED))
    )
    if should_output and not cancel.cancelled:
        result.output_reached = mode == Mode.OUTPUT or a.decision in (Decision.ALLOWED, Decision.FLAGGED)
        result.output_hypothetical = mode == Mode.PAIRED and not result.output_reached
        result.output_scan = await safe_scan(
            client, scenario.simulated_response, "response", scenario, run_id, a.scan_id
        )
    result.final = classify(result, mode)
    result.status = (
        "error"
        if Decision.ERROR in (a.decision, result.output_scan.decision)
        else (
            "cancelled"
            if should_output and cancel.cancelled and not result.output_scan.valid
            else "completed"
        )
    )
    return result


async def evaluate(
    dataset,
    client,
    mode=Mode.INPUT,
    strategy=Strategy.PRODUCTION,
    *,
    concurrency=5,
    config=None,
    cancel=None,
    progress=None,
):
    mode, strategy = Mode(mode), Strategy(strategy)
    if not 1 <= concurrency <= 50:
        raise ValueError("Concurrency must be between 1 and 50")
    if not dataset.scenarios:
        raise ValueError("Dataset has no valid scenarios")
    if any(
        (mode != Mode.OUTPUT and s.input is None) or (mode != Mode.INPUT and s.simulated_response is None)
        for s in dataset.scenarios
    ):
        raise ValueError("Dataset is missing text required by this evaluation mode")
    cancel = cancel or Cancellation()
    run = Run(
        mode=mode,
        strategy=strategy,
        source=client.source,
        dataset_name=dataset.name,
        dataset_hash=dataset.sha256,
        config=config or {},
    )
    results = [None] * len(dataset.scenarios)
    queue = asyncio.Queue()
    for i, s in enumerate(dataset.scenarios):
        queue.put_nowait((i, s))
    completed = 0

    async def worker():
        nonlocal completed
        while not queue.empty():
            i, scenario = queue.get_nowait()
            results[i] = await evaluate_scenario(client, scenario, mode, strategy, run.id, cancel)
            completed += 1
            if progress:
                progress(completed, len(results), results[i])
            queue.task_done()

    await asyncio.gather(*(worker() for _ in range(min(concurrency, len(results)))))
    run.results = results
    run.status = (
        "cancelled"
        if cancel.cancelled
        else "completed_with_errors"
        if any(r.status == "error" for r in results)
        else "completed"
    )
    # Even a malicious dataset/server echo must not export the configured API credential.
    token = getattr(getattr(client, "settings", None), "token", None)
    run = Run.model_validate(redact(run.model_dump(mode="json"), token.get_secret_value() if token else ""))
    log.info(
        "run_completed run_id=%s scenarios=%d status=%s source=%s",
        run.id,
        len(results),
        run.status,
        run.source,
    )
    return run
