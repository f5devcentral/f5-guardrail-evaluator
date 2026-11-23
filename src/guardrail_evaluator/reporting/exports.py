import html
import json
import os
from pathlib import Path

import pandas as pd

from ..engine.metrics import summarize
from .charts import decision_chart, latency_chart


def export_records(run):
    meta = run.model_dump(mode="json", exclude={"results"})
    return [{**meta, **r.model_dump(mode="json")} for r in run.results]


def formula_safe(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def private_write(path, content):
    with open(path, "w", encoding="utf-8", opener=lambda p, flags: os.open(p, flags, 0o600)) as f:
        f.write(content)


def export_run(run, directory):
    """Explicit persistence action. HTML escapes all dataset and API evidence."""
    root = Path(directory) / run.id
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    records = export_records(run)
    summary = summarize(run)
    private_write(root / "results.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    flat = pd.json_normalize(records, sep=".")
    for col in flat.columns:
        flat[col] = flat[col].map(
            lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else formula_safe(x)
        )
    private_write(root / "results.csv", flat.to_csv(index=False))
    private_write(root / "summary.json", json.dumps(summary, indent=2, ensure_ascii=False))
    charts = decision_chart(summary).to_html(full_html=False, include_plotlyjs=True, div_id="decisions")
    charts += latency_chart(run).to_html(full_html=False, include_plotlyjs=False, div_id="latency")
    evidence = "".join(
        f"<details><summary>{html.escape(r.scenario.id)} · {html.escape(r.final)}</summary>"
        f"<pre>{html.escape(r.model_dump_json(indent=2))}</pre></details>"
        for r in run.results
    )
    title = html.escape(f"F5 Guardrail Evaluator · {run.source}")
    metric_rows = []
    for layer in ("input", "output", "defence_in_depth"):
        for key, value in summary.get(layer, {}).items():
            if isinstance(value, dict) and "denominator" in value:
                display = "N/A" if value["value"] is None else f"{value['value']:.2%}"
                metric_rows.append(
                    [layer, key.replace("_", " "), display, f"{value['numerator']} / {value['denominator']}"]
                )
            elif key == "latency_ms":
                for name, measurement in value.items():
                    metric_rows.append(
                        [
                            layer,
                            f"latency {name}",
                            "N/A" if measurement is None else f"{measurement:.2f}",
                            "scans" if name == "count" else "ms",
                        ]
                    )
            else:
                metric_rows.append([layer, key.replace("_", " "), value, "count"])
    metric_table = pd.DataFrame(
        metric_rows, columns=["Layer", "Metric", "Value", "Denominator / unit"]
    ).to_html(index=False, escape=True, border=0)
    document = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{font:16px system-ui,sans-serif;background:#f5f7fa;color:#182438;max-width:1160px;margin:40px auto;padding:24px}}
h1{{font-size:32px}}.banner{{background:#182438;color:white;padding:20px;border-radius:12px}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}details{{background:white;border:1px solid #dfe4eb;padding:16px;margin:10px 0;border-radius:8px}}
table{{width:100%;border-collapse:collapse;background:white;font-size:14px}}th,td{{padding:10px 14px;text-align:left;border-bottom:1px solid #e1e6ef}}th{{background:#eaf0f8}}
summary{{cursor:pointer;font-weight:600}}@media print{{details{{break-inside:avoid}}}}</style></head><body>
<h1>F5 Guardrail Evaluator</h1><div class="banner">{html.escape(run.source)} · {html.escape(run.mode.value)} · {html.escape(run.strategy.value)}</div>
<p>Run {html.escape(run.id)} · {html.escape(run.timestamp)}<br>Dataset: {html.escape(run.dataset_name)} · SHA-256 {run.dataset_hash}</p>
<p>All response text is a predefined fixture. No model generated these responses during the run.</p>
{charts}<h2>Metrics and explicit denominators</h2>{metric_table}<p>{html.escape(summary["notes"])}</p>
<details><summary>Full metrics, category breakdowns and scanner attribution</summary><pre>{html.escape(json.dumps(summary, indent=2))}</pre></details>
<h2>Scenario evidence</h2>{evidence}</body></html>"""
    private_write(root / "report.html", document)
    return [root / n for n in ("results.csv", "results.jsonl", "report.html", "summary.json")]
