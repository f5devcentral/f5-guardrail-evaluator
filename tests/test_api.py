import json

import httpx
import pytest
from conftest import api_body

from guardrail_evaluator.api.f5_client import F5Client, ScanOptions
from guardrail_evaluator.config import Settings
from guardrail_evaluator.engine.decisions import normalize_response


def settings(**kwargs):
    return Settings(_env_file=None, token="secret-canary", retries=0, **kwargs)


async def test_request_contract_and_linking():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.headers["Authorization"] == "Bearer secret-canary"
        return httpx.Response(200, json=api_body())

    async with F5Client(
        settings(project="demo"), httpx.MockTransport(handler), ScanOptions(disabled=["scanner-id"])
    ) as client:
        await client.scan("request", "request", request_id="ignored")
        await client.scan("response", "response", request_id="123")
    a, b = [json.loads(r.content) for r in calls]
    assert str(calls[0].url) == "https://us1.calypsoai.app/backend/v1/scans"
    assert a["input"] == "request" and a["project"] == "demo"
    assert a["scanDirection"] == "request" and a["flagOnly"] is False and a["verbose"] is True
    assert "requestPromptId" not in a
    assert b["requestPromptId"] == "123" and b["scanDirection"] == "response"


@pytest.mark.parametrize(
    "raw,decision",
    [
        ("cleared", "allowed"),
        ("flagged", "flagged"),
        ("blocked", "blocked"),
        ("redacted", "flagged"),
        ("surprise", "error"),
    ],
)
def test_normalization(raw, decision):
    s = normalize_response(api_body(raw))
    assert s.decision == decision
    assert s.raw["result"]["outcome"] == raw


@pytest.mark.parametrize(
    "body",
    [
        {},
        [],
        {"result": {"outcome": "cleared"}},
        api_body(scans=[{"outcome": "failed", "data": {"type": "error"}}]),
    ],
)
def test_invalid_or_partial_evidence(body):
    assert normalize_response(body).decision == "error"


async def test_timeout_no_replay():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("secret-canary")

    cfg = Settings(_env_file=None, token="secret-canary", retries=3, retry_scan_responses=True)
    async with F5Client(cfg, httpx.MockTransport(handler)) as client:
        result = await client.scan("x", "request")
    assert len(calls) == 1 and result.decision == "error"
    assert "secret-canary" not in result.model_dump_json()


@pytest.mark.parametrize("status", [401, 403, 422, 429, 503])
async def test_post_errors_not_replayed_by_default(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="secret-canary")

    cfg = Settings(_env_file=None, token="secret-canary", retries=3)
    async with F5Client(cfg, httpx.MockTransport(handler)) as client:
        result = await client.scan("x", "request")
    assert len(calls) == 1 and result.error == f"http_{status}"


async def test_retry_after_and_explicit_opt_in(monkeypatch):
    waits, calls = [], []

    async def sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr("guardrail_evaluator.api.f5_client.asyncio.sleep", sleep)

    def handler(request):
        calls.append(request)
        return (
            httpx.Response(429, headers={"Retry-After": "3"})
            if len(calls) == 1
            else httpx.Response(200, json=api_body())
        )

    cfg = Settings(_env_file=None, token="retry-secret-canary", retries=2, retry_scan_responses=True)
    async with F5Client(cfg, httpx.MockTransport(handler)) as client:
        result = await client.scan("x", "request")
    assert result.valid and result.attempts == 2 and waits == [3]


async def test_secret_redaction():
    body = api_body()
    body["redactedInput"] = "echo secret-canary"
    body["authorization"] = "anything"
    body["metadata"] = {"secret-canary": "echoed as a key"}
    async with F5Client(settings(), httpx.MockTransport(lambda _: httpx.Response(200, json=body))) as client:
        result = await client.scan("x", "request")
    assert "secret-canary" not in result.model_dump_json()
    assert "token" not in settings().snapshot()


async def test_project_pagination():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "projects": [{"id": str(len(calls)), "name": "project"}],
                "next": "page2" if len(calls) == 1 else None,
            },
        )

    async with F5Client(settings(), httpx.MockTransport(handler)) as client:
        projects = await client.projects()
    assert len(projects) == 2 and calls[1].url.params["cursor"] == "page2"
