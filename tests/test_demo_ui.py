import json

import pytest
from test_engine import FakeClient

from guardrail_evaluator.api.demo_client import DemoClient
from guardrail_evaluator.ui.app import build_app, load_mapped
from guardrail_evaluator.ui.demo_lab import advance_demo, new_demo, render_demo


async def test_demo_stages_really_scan_at_the_correct_time(scenario):
    state = new_demo(scenario)
    client = FakeClient(("cleared", "blocked"))
    assert client.calls == []
    await advance_demo(state, client)
    assert len(client.calls) == 1
    await advance_demo(state, client)  # fixture display only
    assert len(client.calls) == 1
    await advance_demo(state, client)
    assert len(client.calls) == 2
    await advance_demo(state, client)
    assert state["result"].final == "additional_output_prevention"
    await advance_demo(state, client)
    assert len(client.calls) == 2


@pytest.mark.parametrize("independent,expected", [(False, 1), (True, 2)])
async def test_demo_blocked_input_never_injects_production_response(scenario, independent, expected):
    state = new_demo(scenario)
    client = FakeClient(("blocked", "blocked"))
    for _ in range(4):
        await advance_demo(state, client, independent)
    assert len(client.calls) == expected
    assert state["result"].output_hypothetical is independent
    assert "input prevention" in render_demo(state)
    if not independent:
        assert "response fixture not injected" in render_demo(state)


async def test_live_client_ignores_expected_demo_storyline(scenario):
    scenario.metadata = {"demo_input": "blocked", "demo_output": "blocked"}
    client = FakeClient(("cleared", "cleared"))
    state = new_demo(scenario)
    for _ in range(4):
        await advance_demo(state, client)
    assert state["result"].final == "potential_escape"


async def test_demo_uses_fixture_not_ground_truth(scenario):
    assert scenario.input.expected_unsafe is True
    result = await DemoClient().scan("sample", "request", scenario=scenario)
    assert result.decision == "allowed"  # no claimed classifier


def test_partial_mapping_retains_automatic_columns(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("prompt,custom_label\nquestion,true\n")
    data = load_mapped(path, "input", ["Auto", "Auto", "custom_label", "Auto"])
    assert len(data.scenarios) == 1 and data.scenarios[0].input.expected_unsafe is True


def test_browser_config_never_contains_environment_token(monkeypatch):
    monkeypatch.setenv("F5_TOKEN", "environment-secret-canary")
    app = build_app()
    config = json.dumps(app.config, default=str)
    assert "environment-secret-canary" not in config
    assert "Guardrail Evaluator" in config
    app.close()
