import os

import pytest

from guardrail_evaluator.api.f5_client import F5Client
from guardrail_evaluator.config import Settings


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("F5_LIVE_TEST") != "1", reason="Requires explicit F5_LIVE_TEST=1 and a configured tenant"
)
async def test_live_input_and_response():
    async with F5Client(Settings()) as client:
        first = await client.scan("Synthetic integration test: hello.", "request")
        assert first.valid, first.error
        second = await client.scan(
            "Hello. This is a predefined synthetic response.", "response", request_id=first.scan_id
        )
        assert second.valid, second.error
