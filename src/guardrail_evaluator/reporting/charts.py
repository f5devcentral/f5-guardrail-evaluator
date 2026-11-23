import pandas as pd
import plotly.graph_objects as go

COLORS = {
    "allowed": "#13856c",
    "flagged": "#c78519",
    "blocked": "#d63b48",
    "error": "#6b55ac",
    "not_executed": "#96a0ad",
}


def decision_chart(summary):
    fig = go.Figure()
    layers = [k for k in ("input", "output") if k in summary]
    for decision, color in COLORS.items():
        fig.add_bar(
            name=decision.replace("_", " ").title(),
            x=layers,
            y=[summary[k][decision] for k in layers],
            marker_color=color,
        )
    fig.update_layout(
        barmode="stack",
        title="Decisions by layer",
        template="plotly_white",
        height=330,
        margin={"l": 35, "r": 20, "t": 55, "b": 35},
        legend={"orientation": "h", "y": -0.2},
    )
    return fig


def latency_chart(run):
    fig = go.Figure()
    for name, color in (("input", "#598ac8"), ("output", "#13856c")):
        values = [
            getattr(r, name + "_scan").latency_ms for r in run.results if getattr(r, name + "_scan").valid
        ]
        if values:
            fig.add_trace(
                go.Box(y=values, name=name.title(), marker_color=color, boxpoints="all", jitter=0.25)
            )
    fig.update_layout(
        title="Latency · milliseconds"
        + (" · fixed demo timings" if run.source.startswith("SIMULATED") else ""),
        template="plotly_white",
        height=330,
        margin={"l": 45, "r": 20, "t": 55, "b": 35},
    )
    return fig


def result_frame(run):
    rows = []
    for r in run.results:
        a, b, s = r.input_scan, r.output_scan, r.scenario
        rows.append(
            {
                "id": s.id,
                "category": s.category,
                "input": a.decision.value,
                "output": b.decision.value,
                "final": r.final,
                "status": r.status,
                "input_unsafe": s.input.expected_unsafe if s.input else None,
                "output_unsafe": s.simulated_response.expected_unsafe if s.simulated_response else None,
                "output_path": "hypothetical"
                if r.output_hypothetical
                else "reached"
                if r.output_reached
                else "not executed",
                "input_ms": a.latency_ms,
                "output_ms": b.latency_ms,
                "scanners": ", ".join(
                    sorted(
                        {
                            x.get("scannerName") or x.get("scannerId", "unknown")
                            for scan in (a, b)
                            for x in scan.scanners
                        }
                    )
                ),
                "input_detection": detection(s.input, a),
                "output_detection": detection(s.simulated_response, b),
            }
        )
    return pd.DataFrame(rows)


def detection(content, scan):
    if not content or content.expected_unsafe is None or not scan.valid:
        return "N/A"
    positive = scan.decision.value in ("flagged", "blocked")
    return {(True, True): "TP", (True, False): "FN", (False, True): "FP", (False, False): "TN"}[
        (content.expected_unsafe, positive)
    ]
