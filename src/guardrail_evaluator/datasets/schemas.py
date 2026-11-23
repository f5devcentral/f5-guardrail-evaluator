from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, StrictBool, model_validator


class Mode(StrEnum):
    INPUT = "input"
    OUTPUT = "output"
    PAIRED = "defence-in-depth"


class Strategy(StrEnum):
    PRODUCTION = "production-path"
    INDEPENDENT = "independent"
    COMPARISON = "comparison"


class Decision(StrEnum):
    ALLOWED = "allowed"
    FLAGGED = "flagged"
    BLOCKED = "blocked"
    ERROR = "error"
    NOT_EXECUTED = "not_executed"


class Content(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    expected_unsafe: StrictBool | None = None


class Scenario(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    name: str = ""
    category: str = "uncategorised"
    severity: str = "unspecified"
    input: Content | None = None
    simulated_response: Content | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def has_content(self):
        if self.input is None and self.simulated_response is None:
            raise ValueError("Scenario needs input or response text")
        return self


class ScanResult(BaseModel):
    decision: Decision = Decision.NOT_EXECUTED
    original_outcome: str | None = None
    scan_id: str | None = None
    latency_ms: float | None = None
    scanners: list[dict[str, Any]] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    attempts: int = 0

    @property
    def valid(self):
        return self.decision in (Decision.ALLOWED, Decision.FLAGGED, Decision.BLOCKED)


class ScenarioResult(BaseModel):
    scenario: Scenario
    input_scan: ScanResult = Field(default_factory=ScanResult)
    output_scan: ScanResult = Field(default_factory=ScanResult)
    output_hypothetical: bool = False
    output_reached: bool = False
    status: str = "pending"
    final: str = "not_executed"


class Run(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    mode: Mode
    strategy: Strategy = Strategy.PRODUCTION
    source: str = "SIMULATED DEMO DATA"
    dataset_name: str
    dataset_hash: str
    config: dict[str, Any] = Field(default_factory=dict)
    results: list[ScenarioResult] = Field(default_factory=list)
    status: str = "running"
