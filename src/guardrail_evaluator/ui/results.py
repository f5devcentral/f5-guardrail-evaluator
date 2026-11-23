from html import escape

import pandas as pd

from ..reporting.charts import result_frame


def metric_frame(summary):
    rows = []
    for layer in ("input", "output", "defence_in_depth"):
        for key, value in summary.get(layer, {}).items():
            if isinstance(value, dict) and "denominator" in value:
                display = "N/A" if value["value"] is None else f"{value['value']:.2%}"
                rows.append(
                    [layer, key.replace("_", " "), display, f"{value['numerator']} / {value['denominator']}"]
                )
            elif key == "latency_ms":
                for name, latency in value.items():
                    rows.append(
                        [
                            layer,
                            f"latency {name}",
                            "N/A" if latency is None else f"{latency:.2f}",
                            "valid scans" if name == "count" else "ms",
                        ]
                    )
            else:
                rows.append([layer, key.replace("_", " "), str(value), "count"])
    return pd.DataFrame(rows, columns=["Layer", "Metric", "Value", "Denominator / unit"])


def scanner_frame(summary):
    return pd.DataFrame(
        [{"Scanner / direction": name, **counts} for name, counts in summary["scanners"].items()]
    ).fillna(0)


def category_frame(summary):
    rows = []
    for category, layers in summary["categories"].items():
        for layer, values in layers.items():
            rate = values["recall"]
            rows.append(
                {
                    "Category": category,
                    "Layer": layer,
                    "Scenarios": values["total"],
                    "Detection": "N/A" if rate["value"] is None else f"{rate['value']:.1%}",
                    "Unsafe evaluated": rate["denominator"],
                    "FP": values["fp"],
                    "FN": values["fn"],
                    "Errors": values["error"],
                }
            )
    return pd.DataFrame(rows)


def metric_cards(run, summary):
    cells = [
        ("Scenarios", str(len(run.results))),
        ("Execution errors", str(sum(r.status == "error" for r in run.results))),
    ]
    for layer in ("input", "output"):
        if layer in summary:
            rate = summary[layer]["recall"]
            text = "N/A" if rate["value"] is None else f"{rate['value']:.1%}"
            cells.append((f"{layer.title()} detection · {rate['numerator']}/{rate['denominator']}", text))
    if "defence_in_depth" in summary:
        rate = summary["defence_in_depth"]["combined_prevention_rate"]
        cells.append(
            (
                f"Combined prevention · {rate['numerator']}/{rate['denominator']}",
                "N/A" if rate["value"] is None else f"{rate['value']:.1%}",
            )
        )
    return (
        f'<div class="source-banner">{escape(run.source)} · {escape(run.mode.value)} · {escape(run.strategy.value)}</div><div class="metrics">'
        + "".join(
            f"<article><small>{escape(name)}</small><strong>{escape(value)}</strong></article>"
            for name, value in cells
        )
        + "</div>"
    )


def filter_results(
    run, category="", scanner="", outcome="all", label="all", status="all", mode="all", confusion="all"
):
    if run is None:
        return []
    frame = result_frame(run)
    if mode != "all" and mode != run.mode.value:
        return frame.iloc[0:0]
    if category:
        frame = frame[frame.category.str.contains(category, case=False, regex=False)]
    if scanner:
        frame = frame[frame.scanners.str.contains(scanner, case=False, regex=False)]
    if outcome != "all":
        frame = frame[(frame.input == outcome) | (frame.output == outcome) | (frame.final == outcome)]
    if label != "all":
        a, b = frame.input_unsafe, frame.output_unsafe
        if label == "unlabelled":
            mask = (
                a.isna() if run.mode == "input" else b.isna() if run.mode == "output" else a.isna() | b.isna()
            )
        else:
            expected = label == "unsafe"
            mask = (
                a.eq(expected)
                if run.mode == "input"
                else b.eq(expected)
                if run.mode == "output"
                else a.eq(expected) | b.eq(expected)
            )
        frame = frame[mask]
    if status != "all":
        frame = frame[frame.status == status]
    if confusion != "all":
        frame = frame[(frame.input_detection == confusion) | (frame.output_detection == confusion)]
    return frame
