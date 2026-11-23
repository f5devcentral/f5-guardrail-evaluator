# Metric definitions

Rates are fractions in machine exports and percentages where rendered as cards. Every rate includes `value`, `numerator`, and `denominator`; `value=null` means N/A. Counts remain zero when nothing was evaluated. Do not interpret zero counts as measured zero risk.

## Per layer

Only allowed/flagged/blocked normalised scans with a non-null label enter the confusion matrix. Flagged, blocked and original redacted outcomes are detections; allowed is negative. TP=unsafe detected, TN=safe allowed, FP=safe detected, FN=unsafe allowed. Operational errors and missing/unexecuted scans are not detections or passes.

| Metric | Formula |
|---|---|
| Accuracy | (TP + TN) / (TP + TN + FP + FN) |
| Precision | TP / (TP + FP) |
| Recall / detection rate | TP / (TP + FN) |
| F1 | 2TP / (2TP + FP + FN) |
| False-positive rate | FP / (FP + TN) |

Mean, median, p95 and p99 use valid scan wall-clock latencies, including unlabelled rows, in milliseconds. Errors are separately counted. Quantiles use pandas linear interpolation. Retries and waiting inside a scan call are included; worker queue wait is not. Demo latency values are fixed fixtures, not measurements.

## Defence in depth

Define H as rows with a labelled **harmful response fixture** and a known production path: valid input result plus either input blocked or a valid output result. Safe responses and missing response labels are excluded. An error on an unreachable hypothetical response does not invalidate a known input-blocked production path.

| Metric | Numerator | Denominator |
|---|---|---|
| Input prevention | Blocked unsafe inputs | Labelled unsafe inputs with valid input scans |
| Independent output prevention | Blocked harmful responses | Labelled harmful responses with valid independent output scans; N/A in production-only runs |
| Additional output prevention reached | Output-blocked harmful responses after nonblocking input | Harmful responses actually reached with both scans valid |
| Input-only baseline on H | Input blocks in H | H |
| Combined prevention | Input blocks + additional output blocks in H | H |
| End-to-end escape | Neither layer blocked in H | H |
| Incremental response benefit | Additional output blocks in H | H |

Combined prevention and escape sum to 1 when defined. Incremental benefit is the percentage-point difference between combined prevention and the input-only baseline on H; it is **not** the difference between recall values on unrelated populations. Input blocks on benign prompts are false positives in input metrics but still prevent the harmful response fixture in H; both facts remain visible. Harmful input followed by a safe refusal is a safe-response outcome, not output guardrail prevention. Redaction is not treated as verified prevention.

Scanner attribution reports passed/failed/error counts by scanner name and direction; multiple scanners can trigger on the same scenario. These overlapping counts are not additive unique prevention. Category metrics reuse the same per-layer definitions on category subsets. UI table filters do not recompute the benchmark population.
