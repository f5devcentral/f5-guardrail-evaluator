"""Explicit browser-local appearance and matching light/dark visual tokens."""

import gradio as gr

# Run before the app mounts to avoid a light flash for a saved dark preference.
THEME_HEAD = """<script>
(() => {
    let saved;
    try { saved = localStorage.getItem('f5-evaluator-appearance'); } catch (_) {}
    const mode = ['light', 'dark'].includes(saved) ? saved :
        (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.dataset.f5Theme = mode;
    document.documentElement.style.colorScheme = mode === 'light' ? 'only light' : 'dark';
    document.documentElement.classList.toggle('dark', mode === 'dark');
})();
</script>"""

THEME_SWITCH_JS = """
const preference = window.matchMedia('(prefers-color-scheme: dark)');
let chosen;
try { chosen = localStorage.getItem('f5-evaluator-appearance'); } catch (_) {}
if (!['light', 'dark'].includes(chosen)) chosen = null;
function apply(mode) {
    document.documentElement.dataset.f5Theme = mode;
    document.documentElement.style.colorScheme = mode === 'light' ? 'only light' : 'dark';
    document.documentElement.classList.toggle('dark', mode === 'dark');
    document.body.classList.toggle('dark', mode === 'dark');
    element.querySelectorAll('[data-appearance]').forEach(button => {
        button.setAttribute('aria-pressed', String(button.dataset.appearance === mode));
    });
}
element.querySelectorAll('[data-appearance]').forEach(button => {
    button.addEventListener('click', () => {
        chosen = button.dataset.appearance;
        try { localStorage.setItem('f5-evaluator-appearance', chosen); } catch (_) {}
        apply(chosen);
    });
});
// Gradio also observes system appearance. Reapply an explicit choice after that
// listener runs, so a system change cannot leave mixed light/dark controls.
preference.addEventListener('change', () => {
    apply(chosen || (preference.matches ? 'dark' : 'light'));
});
apply(chosen || (preference.matches ? 'dark' : 'light'));
"""


def build_theme():
    """Keep native controls on the same palette as the custom presentation."""
    return gr.themes.Base(
        primary_hue="red", neutral_hue="slate", font=["system-ui", "sans-serif"], font_mono=["monospace"]
    ).set(
        body_background_fill="#ffffff",
        body_background_fill_dark="#101722",
        background_fill_primary="#ffffff",
        background_fill_primary_dark="#101722",
        background_fill_secondary="#f3f6fa",
        background_fill_secondary_dark="#1b2636",
        body_text_color="#17263b",
        body_text_color_dark="#e6edf6",
        body_text_color_subdued="#657186",
        body_text_color_subdued_dark="#a6b3c6",
        block_background_fill="*background_fill_primary",
        block_background_fill_dark="*background_fill_primary",
        block_label_background_fill="*background_fill_primary",
        block_label_background_fill_dark="*background_fill_primary",
        block_title_text_color="*body_text_color",
        block_title_text_color_dark="*body_text_color",
        block_label_text_color="*body_text_color",
        block_label_text_color_dark="*body_text_color",
        input_background_fill="*background_fill_secondary",
        input_background_fill_dark="*background_fill_secondary",
    )

CSS = """
:root {--ux-bg:#ffffff;--ux-ink:#17263b;--ux-muted:#657186;--ux-rule:#e2e7ee;--ux-red:#df1633;--ux-wash:#f3f6fa;--ux-choice-border:#cdd5df;--ux-step:#edf0f4;--ux-success:#13856c;--ux-warning:#956011;--ux-danger:#c52e3e;--ux-focus:#355d9b}
html[data-f5-theme="dark"] {--ux-bg:#101722;--ux-ink:#e6edf6;--ux-muted:#a6b3c6;--ux-rule:#334155;--ux-wash:#1b2636;--ux-choice-border:#536277;--ux-step:#253247;--ux-success:#58d4b3;--ux-warning:#efc66e;--ux-danger:#ff8191;--ux-focus:#91b9ff}
html {background:var(--ux-bg)!important}
body,.gradio-container {background:var(--ux-bg)!important;color:var(--ux-ink)!important;font-family:system-ui,-apple-system,sans-serif!important}
.gradio-container {max-width:1320px!important;width:100%!important;margin-inline:auto!important;padding:22px clamp(16px,2.4vw,28px) 36px!important}
.gradio-container .main {padding:0!important;max-width:none!important}
.masthead {display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding:0 4px 22px}
.appearance-switch {display:flex;gap:4px;margin-left:auto;padding:4px;border:1px solid var(--ux-rule);border-radius:8px;background:var(--ux-wash)}
.appearance-switch button {transition:none!important;font:inherit;font-size:13px;font-weight:600;padding:8px 14px;border:1px solid transparent;border-radius:5px;color:var(--ux-muted);background:transparent;cursor:pointer;min-height:36px}
.appearance-switch button[aria-pressed="true"] {background:var(--ux-bg);color:var(--ux-ink);border-color:var(--ux-choice-border)}
.brand {background:var(--ux-red);color:#fff;width:38px;height:38px;border-radius:50%;display:grid;place-items:center;font-size:23px;font-weight:750;flex-shrink:0}
.masthead h1 {font-size:25px;margin:0;color:var(--ux-ink);font-weight:680;letter-spacing:-.8px}
#main-tabs .tab-container {border-bottom:1px solid var(--ux-rule)!important;padding:0!important;gap:24px!important;overflow-x:auto;flex-wrap:nowrap}
#main-tabs .tab-container button {font-size:16px!important;padding:15px 8px!important;border-radius:0!important;color:var(--ux-muted)!important;border:0!important;border-bottom:3px solid transparent!important;white-space:nowrap}
#main-tabs .tab-container button.selected {color:var(--ux-ink)!important;border-bottom-color:var(--ux-red)!important;font-weight:650!important;background:transparent!important}
#main-tabs .tab-wrapper {border-bottom:1px solid var(--ux-rule)!important}
.tabitem {padding:0!important;border:0!important}
.page-heading {padding:34px 4px 6px}.page-heading h2 {font-size:36px;line-height:1.15;letter-spacing:-1.1px;font-weight:670;margin:0 0 10px;color:var(--ux-ink)}
.page-heading p {font-size:17px;line-height:1.5;color:var(--ux-muted);margin:0}
.step-rail {display:flex;align-items:center;list-style:none!important;padding:22px 4px 28px!important;margin:0 0 20px!important;border-bottom:1px solid var(--ux-rule);gap:0}
.step-rail li {display:flex;align-items:center;gap:12px;flex:1;color:var(--ux-muted);font-size:15px;margin:0!important}
.step-rail li:not(:last-child):after {content:"";height:1px;background:var(--ux-rule);flex:1;margin:0 20px}
.step-rail li:last-child {flex:0 0 auto}.step-rail span {display:grid;place-items:center;border-radius:50%;background:var(--ux-step);color:var(--ux-muted);height:32px;width:32px;font-weight:650;flex-shrink:0}
.step-rail strong {color:inherit;font-weight:550}
.step-rail .current {color:var(--ux-ink)}.step-rail .current span,.step-rail .done span {background:var(--ux-red);color:#fff}
.workspace {gap:16px!important;padding:0 4px!important}
.gradio-container .block {box-shadow:none!important;border-color:var(--ux-rule)!important;border-radius:6px!important}
.gradio-container .form {background:transparent!important;border:0!important;box-shadow:none!important;padding:0!important;gap:16px!important}
.gradio-container .block.gradio-radio,.gradio-container .block.gradio-dropdown,.gradio-container .block.gradio-textbox,.gradio-container .block.gradio-slider,.gradio-container .block.gradio-number {border:0!important;background:transparent!important;padding:0!important;overflow:visible}
.gradio-container label > span,.gradio-container .block-label {color:var(--ux-ink)!important;font-weight:550!important;font-size:14px!important;background:transparent!important}
.gradio-container .wrap.default {background:var(--ux-bg)!important}
.gradio-container input,.gradio-container textarea {font-family:inherit!important;font-size:15px!important}
.gradio-container button.primary {background:var(--ux-red)!important;border-color:var(--ux-red)!important;color:white!important;box-shadow:none!important;font-weight:600!important;border-radius:6px!important}
.gradio-container button.secondary {background:var(--ux-bg)!important;border:1px solid var(--ux-rule)!important;color:var(--ux-ink)!important;box-shadow:none!important;border-radius:6px!important}
.gradio-container button.primary:hover {background:#be102b!important}.gradio-container button:focus-visible {outline:2px solid var(--ux-focus)!important;outline-offset:3px}
.block.mode-choice,.block.source-choice {padding:0!important;border:0!important}
.mode-choice label,.source-choice label {transition:none!important;background:var(--ux-bg)!important;border:1px solid var(--ux-choice-border)!important;border-radius:6px!important;padding:14px 18px!important;min-height:48px}
.mode-choice label {flex:1!important}.mode-choice label.selected,.source-choice label.selected {border-color:var(--ux-red)!important;background:var(--ux-bg)!important}
.mode-choice label span,.source-choice label span {font-weight:450!important;font-size:16px!important}.mode-choice label.selected span,.source-choice label.selected span {font-weight:600!important}
.quiet-copy p {color:var(--ux-muted)!important;font-size:13px!important;line-height:1.6!important;margin:0!important}
.block.mode-notice {border-left:3px solid #4d6688!important;padding:10px 14px!important;background:var(--ux-wash)!important;border-radius:4px;margin:2px 0 8px}
.mode-notice p {font-size:13px!important;color:var(--ux-muted)!important}
.action-bar {border-top:1px solid var(--ux-rule);padding-top:20px!important;margin-top:16px!important;align-items:center!important;justify-content:space-between!important;gap:12px!important}
.action-bar button {height:auto!important;min-height:46px!important;padding:12px 18px!important;line-height:1.35!important}.action-bar > .quiet-copy {flex:1!important;min-width:200px}
.section-heading {font-size:19px;font-weight:650;letter-spacing:-.3px;margin:12px 0 2px}
.source-banner {font-size:12px;color:var(--ux-muted);padding:10px 0;line-height:1.6}
.metrics {display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:20px;border-bottom:1px solid var(--ux-rule);padding:14px 0 24px;margin-bottom:8px}
.metrics article {border-right:1px solid var(--ux-rule);padding:0 18px 0 0}.metrics article:last-child {border:0}
.metrics small {display:block;font-size:12px;color:var(--ux-muted)}.metrics strong {font-size:30px;display:block;margin-top:8px;font-weight:650;letter-spacing:-.8px}
.report-bar {align-items:center!important;padding:12px 0!important}.report-bar > .quiet-copy {flex:1!important}
.empty-state,.completion {padding:46px 0}.empty-state h3,.completion h3 {font-size:24px;letter-spacing:-.5px;margin:0 0 12px}.empty-state p,.completion p {font-size:15px;color:var(--ux-muted);max-width:600px;line-height:1.6}
.demo-toolbar {padding:18px 0 6px;align-items:flex-start!important}
.demo-rail {display:flex;list-style:none!important;margin:14px 0 24px!important;padding:0!important;border-bottom:1px solid var(--ux-rule);gap:12px}
.demo-rail li {flex:1;font-size:12px;color:var(--ux-muted);padding:12px 0 16px;margin:0!important;border-bottom:3px solid transparent}
.demo-rail li.active {color:var(--ux-ink);border-bottom-color:var(--ux-red);font-weight:650}.demo-rail li.complete {color:var(--ux-success)}
.demo-focus {padding:10px 0 24px;min-height:210px}.demo-focus small {color:var(--ux-muted);font-size:12px}.demo-focus h3 {font-size:28px;letter-spacing:-.6px;margin:12px 0}
.demo-focus p {font-size:16px;line-height:1.7;max-width:800px;white-space:pre-wrap;overflow-wrap:anywhere}.demo-status {font-size:13px;font-weight:650;text-transform:capitalize;margin-top:18px}
.demo-focus[data-status="blocked"] .demo-status {color:var(--ux-danger)}.demo-focus[data-status="allowed"] .demo-status {color:var(--ux-success)}.demo-focus[data-status="flagged"] .demo-status {color:var(--ux-warning)}
.demo-history {border-top:1px solid var(--ux-rule);padding:14px 0;font-size:13px}.demo-history summary {cursor:pointer;color:var(--ux-muted)}.demo-history p {color:var(--ux-muted);line-height:1.6;white-space:pre-wrap}
/* Plotly SVGs inherit appearance without changing data, zoom, or exported reports. */
.gradio-container .js-plotly-plot .main-svg {background:transparent!important}
.gradio-container .js-plotly-plot .svg-container > .main-svg:first-child {background:var(--ux-bg)!important}
.gradio-container .js-plotly-plot .bg {fill:var(--ux-bg)!important}
.gradio-container .js-plotly-plot .xtick text,.gradio-container .js-plotly-plot .ytick text,.gradio-container .js-plotly-plot .gtitle,.gradio-container .js-plotly-plot .legendtext {fill:var(--ux-ink)!important}
.gradio-container .js-plotly-plot .gridlayer path,.gradio-container .js-plotly-plot .zerolinelayer path {stroke:var(--ux-rule)!important}
.gradio-container .js-plotly-plot .modebar {background:transparent!important}
.gradio-container .js-plotly-plot .modebar-group {background:var(--ux-wash)!important}
.gradio-container .js-plotly-plot .modebar-btn path {fill:var(--ux-muted)!important}
@media(max-width:700px){.appearance-switch{margin-left:52px}.masthead{padding-bottom:16px}.masthead h1{font-size:22px}.page-heading{padding-top:24px}.page-heading h2{font-size:29px}.page-heading p{font-size:15px}#main-tabs .tab-container{gap:10px!important}#main-tabs .tab-container button{font-size:13px!important;padding:12px 4px!important}.step-rail{padding:18px 0 20px!important}.step-rail li{font-size:11px;gap:6px}.step-rail span{width:25px;height:25px}.step-rail li:not(:last-child):after{margin:0 8px}.mode-choice label{min-width:100%!important;padding:10px 14px!important;min-height:42px}.action-bar,.report-bar{flex-direction:column!important;align-items:stretch!important}.action-bar > *,.report-bar > *{width:100%!important;min-width:0!important;flex:none!important}.action-bar button,.report-bar button{width:100%!important}.metrics{grid-template-columns:repeat(2,1fr)}.demo-rail{gap:6px}.demo-rail li{font-size:10px}.demo-focus h3{font-size:24px}.demo-focus p{font-size:14px}}
"""
