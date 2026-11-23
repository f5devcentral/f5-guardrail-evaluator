# Troubleshooting

| Symptom | Check |
|---|---|
| `guardrail-evaluator` not found | Activate `.venv`, then `pip install -e .` |
| UI cannot bind | Another process may use 7860; use `guardrail-evaluator serve --port 7861` |
| Dataset has no valid rows | Preview and map the correct text/label columns; output mode needs response text |
| Labels show N/A | Add ground-truth labels; unsafe request labels are not copied to responses |
| All demo results cleared | Uploaded rows without demo outcome metadata default to cleared; use packaged paired/demo JSONL |
| HTTP 401/403 | Save the correct token; check expiry, scope, project access and scan permission |
| HTTP 422 | Inspect field types, project identifier, scanner IDs and configuration overrides against tenant documentation |
| Input detects but never blocks | Disable flag-only and check scanner enforcement actions on the project |
| Output sees no scanner evidence | Enable response scanning on the intended project guardrails |
| Response has no scan ID | Recording may be disabled; linkage is optional and is omitted |
| Rate limit or timeout | Reduce concurrency; inspect tenant quotas. Retry only with awareness of duplicate scan creation |
| Corporate proxy unreachable | Client ignores ambient proxy variables; use direct access or adapt explicit transport configuration |
| Cancel takes time | Existing HTTP calls are allowed to finish within timeout; queued work is skipped |
| Export denied | Select a writable result directory; no existing run folder is overwritten |
| Results differ from demo storyline | Live API decisions are authoritative; mock outcomes never override them |

The application intentionally does not expose API error bodies, which may contain secrets. Use the run ID in tenant logs and your normal administrative tooling for deeper diagnosis. Raw successful API evidence is visible per scenario, with the configured token scrubbed.
