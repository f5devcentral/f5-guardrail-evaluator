from html import escape

from ..datasets.schemas import Decision, Mode, ScenarioResult
from ..engine.decisions import classify
from ..engine.orchestrator import safe_scan


def new_demo(scenario):
    return {"stage": 0, "result": ScenarioResult(scenario=scenario), "source": None, "independent": None}


async def advance_demo(state, client, independent=False):
    stage, r = state["stage"], state["result"]
    if stage >= 4:
        return state
    if stage == 0:
        state["source"] = client.source
        state["independent"] = independent
        r.input_scan = await safe_scan(client, r.scenario.input, "request", r.scenario, "demo-lab")
    elif stage == 2:
        reached = r.input_scan.decision in (Decision.ALLOWED, Decision.FLAGGED)
        if reached or independent:
            r.output_reached = reached
            r.output_hypothetical = not reached
            r.output_scan = await safe_scan(
                client,
                r.scenario.simulated_response,
                "response",
                r.scenario,
                "demo-lab",
                r.input_scan.scan_id,
            )
    elif stage == 3:
        r.final = classify(r, Mode.PAIRED)
        r.status = (
            "error" if Decision.ERROR in (r.input_scan.decision, r.output_scan.decision) else "completed"
        )
    state["stage"] += 1
    return state


def render_demo(state):
    r, stage = state["result"], state["stage"]
    stopped = r.input_scan.decision in (Decision.BLOCKED, Decision.ERROR) and not state["independent"]
    nodes = [
        ("Incoming prompt", "ready", r.scenario.input.text),
        (
            "Input guardrail",
            r.input_scan.decision.value,
            scan_description(r.input_scan) if stage >= 1 else "Advance to scan the incoming prompt.",
        ),
        (
            "Simulated model",
            "not_executed" if stopped else "ready" if stage >= 2 else "pending",
            "Production path stopped; response fixture not injected."
            if stopped
            else r.scenario.simulated_response.text
            if stage >= 2
            else "Predefined response fixture. No model will be called.",
        ),
        (
            "Output guardrail",
            r.output_scan.decision.value,
            ("HYPOTHETICAL independent test · " if r.output_hypothetical else "")
            + scan_description(r.output_scan)
            if stage >= 3
            else "Awaiting response stage.",
        ),
        (
            "Final outcome",
            r.final if stage >= 4 else "pending",
            r.final.replace("_", " ") if stage >= 4 else "Advance through the stages to inspect the outcome.",
        ),
    ]
    rail = (
        '<ol class="demo-rail" aria-label="Demo stages">'
        + "".join(
            f'<li class="{"active" if i == stage else "complete" if i < stage else "pending"}">{i + 1} · {escape(title)}</li>'
            for i, (title, _, _) in enumerate(nodes)
        )
        + "</ol>"
    )
    title, status, body = nodes[stage]
    focus = (
        f'<article class="demo-focus" data-status="{escape(status, quote=True)}">'
        f"<small>Step {stage + 1} of 5</small><h3>{escape(title)}</h3>"
        f'<p>{escape(body)}</p><div class="demo-status">{escape(status.replace("_", " "))}</div></article>'
    )
    history = ""
    if stage:
        history = (
            '<details class="demo-history"><summary>Review earlier stages</summary>'
            + "".join(
                f"<p><strong>{escape(title)} · {escape(status.replace('_', ' '))}</strong><br>{escape(body)}</p>"
                for title, status, body in nodes[:stage]
            )
            + "</details>"
        )
    source = state["source"] or "No scans executed"
    return f'<div class="source-banner">{escape(source)} · All model responses are predefined fixtures</div>{rail}{focus}{history}'


def next_demo_label(state):
    if (
        state["stage"] in (1, 2)
        and state["result"].input_scan.decision in (Decision.BLOCKED, Decision.ERROR)
        and not state["independent"]
    ):
        return "Continue · output skipped →"
    return (
        "Scan input →",
        "Show response fixture →",
        "Scan output →",
        "Show final outcome →",
        "Walkthrough complete",
    )[state["stage"]]


def scan_description(scan):
    if scan.decision == Decision.NOT_EXECUTED:
        return "Not executed."
    scanners = "; ".join(
        f"{s.get('scannerName', s.get('scannerId', 'unknown'))}: {s.get('outcome', 'unknown')}"
        for s in scan.scanners
    )
    latency = f"{scan.latency_ms:.1f} ms" if scan.latency_ms is not None else "N/A"
    return (
        f"{latency} · API outcome: {scan.original_outcome or 'N/A'} · {scanners or 'No scanner evidence returned'}"
        + (f" · {scan.error}" if scan.error else "")
    )
