"""Small, escaped presentation helpers for the guided interface."""

from html import escape

MODE_HELP = {
    "input": "Scan prompts without a model or response dataset.",
    "output": "Scan predefined responses. No input prompts or live model are required.",
    "defence-in-depth": "Test input and response guardrails together using paired scenarios.",
}

SOURCE_HELP = {
    "Demo Data Mode": "**SIMULATED DEMO DATA** · Fixed outcomes and timings; no API calls. Uploaded rows without demo metadata default to cleared.",
    "Live API Mode": "**LIVE F5 API** · Sends text to your saved tenant. Response text is always a predefined fixture.",
}


def page_heading(title, description):
    return f'<div class="page-heading"><h2>{escape(title)}</h2><p>{escape(description)}</p></div>'


def section_heading(title):
    return f'<h3 class="section-heading">{escape(title)}</h3>'


def step_rail(current):
    parts = []
    for index, label in enumerate(("Dataset", "Review & configure", "Run"), 1):
        state = "current" if index == current else "done" if index < current else "pending"
        aria = ' aria-current="step"' if index == current else ""
        parts.append(f'<li class="{state}"{aria}><span>{index}</span><strong>{label}</strong></li>')
    return '<ol class="step-rail" aria-label="Evaluation progress">' + "".join(parts) + "</ol>"


def completion_summary(run):
    errors = sum(r.status == "error" for r in run.results)
    return (
        f'<div class="completion"><h3>{len(run.results)} scenarios in this run</h3>'
        f"<p>{escape(run.source)} · {errors} execution errors</p>"
        "<p>Open Results &amp; Reports for decisions, scanner evidence and CSV downloads.</p></div>"
    )


def compact_results(frame):
    if not hasattr(frame, "columns"):
        return frame
    return frame[["id", "category", "input", "output", "final", "status"]]
