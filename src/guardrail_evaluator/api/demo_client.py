import asyncio

from ..engine.decisions import normalize_response


class DemoClient:
    """Deterministic teaching fixtures. No classifier and no network access."""

    source = "SIMULATED DEMO DATA"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def scan(self, text, direction, *, request_id=None, scenario=None, run_id=""):
        await asyncio.sleep(0)
        key = "demo_input" if direction == "request" else "demo_output"
        outcome = scenario.metadata.get(key, "cleared") if scenario else "cleared"
        if outcome not in ("cleared", "flagged", "blocked", "redacted"):
            outcome = "cleared"
        return normalize_response(
            {
                "id": f"demo-{scenario.id if scenario else 'sample'}-{direction}",
                "redactedInput": text,
                "result": {
                    "outcome": outcome,
                    "scannerResults": [
                        {
                            "scannerId": "demo-policy",
                            "scannerName": "SIMULATED policy fixture",
                            "outcome": "passed" if outcome == "cleared" else "failed",
                            "scanDirection": direction,
                            "data": {"type": "demo"},
                            "message": "Fixed teaching result; not an F5 measurement",
                        }
                    ],
                },
            },
            latency_ms=24 if direction == "request" else 38,
        )
