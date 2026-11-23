"""Regression coverage for the guided flow's data selection and error recovery."""

import gradio as gr
import pytest
from test_engine import FakeClient

from guardrail_evaluator.engine.orchestrator import Cancellation
from guardrail_evaluator.ui.app import build_app
from guardrail_evaluator.ui.demo_lab import advance_demo, new_demo, next_demo_label, render_demo


@pytest.fixture(scope="module")
def callbacks():
    app = build_app()
    yield {event.fn.__name__: event.fn for event in app.fns.values() if event.fn}
    app.close()


def test_upload_selection_requires_a_file(callbacks):
    with pytest.warns(UserWarning, match="Choose a CSV"):
        result = callbacks["prepare_setup"](
            None, "Synthetic benchmark · 108", "input", "Upload a file", *(["Auto"] * 4)
        )
    assert all(update == gr.skip() for update in result)


@pytest.mark.parametrize(
    "mode,visible",
    [
        ("input", [True, False, True, False]),
        ("output", [False, True, False, True]),
        ("defence-in-depth", [True] * 4),
    ],
)
def test_sample_selection_ignores_stale_upload_and_maps_only_active_layers(callbacks, mode, visible):
    result = callbacks["prepare_setup"](
        "/does/not/exist.csv", "Synthetic benchmark · 108", mode, "Sample library", *(["Auto"] * 4)
    )
    assert "108 valid scenarios" in result[0]
    assert [update["visible"] for update in result[3:7]] == visible
    assert result[-4]["visible"] is False  # Dataset hidden
    assert result[-3]["visible"] is True  # Setup shown


def test_invalid_upload_shows_errors_without_silently_falling_back(callbacks, tmp_path):
    path = tmp_path / "mixed.csv"
    path.write_text("prompt,label\nValid prompt,safe\n,unsafe\n")
    result = callbacks["prepare_setup"](
        path, "Synthetic benchmark · 108", "input", "Upload a file", *(["Auto"] * 4)
    )
    assert "1 valid scenarios" in result[0]
    assert len(result[2]) == 1
    assert result[7]["visible"] is True


def test_starting_a_new_run_resets_cancellation_and_hides_old_completion(callbacks):
    cancel = Cancellation()
    cancel.cancel()
    result = callbacks["begin_run"](cancel)
    assert not cancel.event.is_set()
    assert result[2]["visible"] is True  # Run step
    assert result[5] == ""  # Previous completion summary
    assert result[7]["visible"] is False  # New evaluation button
    assert result[8]["visible"] is False  # View results button
    assert result[9]["interactive"] is False  # Prevent double start


async def test_demo_labels_follow_actual_blocked_path_and_keep_history(scenario):
    state = new_demo(scenario)
    client = FakeClient(("blocked", "blocked"))
    assert next_demo_label(state) == "Scan input →"
    await advance_demo(state, client)
    assert next_demo_label(state) == "Continue · output skipped →"
    for _ in range(3):
        await advance_demo(state, client)
    assert next_demo_label(state) == "Walkthrough complete"
    assert len(client.calls) == 1
    html = render_demo(state)
    assert html.count('class="demo-focus"') == 1
    assert "Review earlier stages" in html
