import asyncio
import random
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

from ..config import Settings
from ..datasets.schemas import Decision, ScanResult
from ..engine.decisions import normalize_response
from ..security import redact


class ScanOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    disabled: list[str] = Field(default_factory=list)
    forceEnabled: list[str] = Field(default_factory=list)
    configOverrides: dict[str, dict[str, Any]] = Field(default_factory=dict)


class APIError(Exception):
    """Only safe categories/status codes cross the transport boundary."""


def retry_after(value):
    try:
        seconds = float(value)
    except (ValueError, TypeError):
        try:
            seconds = (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return None
    return max(0, seconds)


class F5Client:
    source = "LIVE F5 API"

    def __init__(self, settings: Settings, transport=None, options=None):
        self.settings = settings
        self.options = options or ScanOptions()
        if not settings.token.get_secret_value().strip():
            raise ValueError("Set F5_TOKEN or enter a token in Settings")
        self.http = httpx.AsyncClient(
            base_url=settings.base_url + "/",
            timeout=settings.timeout,
            headers={
                "Authorization": f"Bearer {settings.token.get_secret_value()}",
                "Accept": "application/json",
            },
            transport=transport,
            follow_redirects=False,
            trust_env=False,
            limits=httpx.Limits(
                max_connections=settings.concurrency, max_keepalive_connections=settings.concurrency
            ),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.http.aclose()

    async def _request(self, method, path, **kwargs):
        for attempt in range(self.settings.retries + 1):
            delay = min(8, 0.5 * 2**attempt) + random.uniform(0, 0.1)
            try:
                response = await self.http.request(method, path, **kwargs)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
                if attempt == self.settings.retries:
                    raise APIError("connection_failure") from None
            except httpx.TimeoutException:
                # The server may have committed the POST. Never replay an ambiguous request.
                raise APIError("timeout_scan_may_have_been_created") from None
            except httpx.RequestError:
                raise APIError("transport_failure_scan_may_have_been_created") from None
            else:
                if 200 <= response.status_code < 300:
                    try:
                        return response.json(), attempt + 1
                    except ValueError:
                        raise APIError("invalid_json_response") from None
                retryable = response.status_code in (429, 502, 503, 504)
                safe = method == "GET" or self.settings.retry_scan_responses
                if not retryable or not safe or attempt == self.settings.retries:
                    raise APIError(f"http_{response.status_code}")
                instructed = retry_after(response.headers.get("Retry-After"))
                if instructed is not None:
                    # Do not shorten a server's rate-limit window. Stop if beyond our bound.
                    if instructed > 60:
                        raise APIError("retry_after_exceeds_60_seconds")
                    delay = max(delay, instructed)
            await asyncio.sleep(delay)
        raise APIError("retry_exhausted")

    async def scan(
        self,
        text: str,
        direction: Literal["request", "response"],
        *,
        request_id=None,
        scenario=None,
        run_id="",
    ):
        if direction not in ("request", "response") or not isinstance(text, str) or not text:
            raise ValueError("A scan requires nonempty text and a valid direction")
        payload = {
            "input": text,
            "scanDirection": direction,
            "flagOnly": self.settings.flag_only,
            "verbose": True,
            **self.options.model_dump(),
        }
        if self.settings.project:
            payload["project"] = self.settings.project
        if request_id and direction == "response":
            payload["requestPromptId"] = request_id
        if run_id:
            payload["externalMetadata"] = {"evaluator_run": run_id[:255]}
        start = time.perf_counter()
        try:
            body, attempts = await self._request("POST", "scans", json=payload)
            body = redact(body, self.settings.token.get_secret_value())
            return normalize_response(body, (time.perf_counter() - start) * 1000, attempts)
        except APIError as exc:
            return ScanResult(
                decision=Decision.ERROR, error=str(exc), latency_ms=(time.perf_counter() - start) * 1000
            )

    async def projects(self):
        items, cursor, seen = [], None, set()
        for _ in range(100):
            body, _ = await self._request("GET", "projects", params={"cursor": cursor} if cursor else {})
            if not isinstance(body, dict) or not isinstance(body.get("projects"), list):
                raise APIError("invalid_projects_response")
            for p in body["projects"]:
                if (
                    not isinstance(p, dict)
                    or not isinstance(p.get("id"), str)
                    or not isinstance(p.get("name"), str)
                ):
                    raise APIError("invalid_project")
                items.append(
                    redact({"id": p["id"], "name": p["name"]}, self.settings.token.get_secret_value())
                )
            cursor = body.get("next")
            if not cursor:
                return items
            if not isinstance(cursor, str) or cursor in seen:
                raise APIError("invalid_project_cursor")
            seen.add(cursor)
        raise APIError("project_pagination_limit")
