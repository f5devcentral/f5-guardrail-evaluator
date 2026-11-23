import argparse
import asyncio
import json
import signal
import sys
from pathlib import Path

from .api.demo_client import DemoClient
from .api.f5_client import F5Client, ScanOptions
from .config import Settings
from .datasets.loader import load_dataset
from .datasets.mapping import ColumnMapping
from .datasets.schemas import Mode, Strategy
from .engine.metrics import summarize
from .engine.orchestrator import Cancellation, evaluate
from .reporting.exports import export_run
from .security import configure_logging


def parser():
    p = argparse.ArgumentParser(description="F5 Guardrail Evaluator — no LLM required")
    commands = p.add_subparsers(dest="command", required=True)
    run = commands.add_parser("evaluate", help="Evaluate a CSV or JSONL dataset")
    run.add_argument("--mode", choices=[m.value for m in Mode], default="input")
    run.add_argument("--strategy", choices=[s.value for s in Strategy], default="production-path")
    run.add_argument("--dataset", type=Path, required=True)
    run.add_argument("--project", default=None)
    run.add_argument("--concurrency", type=int)
    run.add_argument("--demo", action="store_true", help="Use fixed, visibly simulated fixtures; no network")
    run.add_argument("--skip-invalid", action="store_true", help="Explicitly skip malformed dataset rows")
    run.add_argument("--output-dir", type=Path, help="Explicitly persist CSV, JSONL and HTML reports here")
    run.add_argument("--no-persist", action="store_true", help="Override automatic persistence")
    run.add_argument("--scan-options", type=Path, help="JSON object: disabled, forceEnabled, configOverrides")
    for name in ("input", "output", "input-label", "output-label"):
        run.add_argument(f"--{name}-column", default=None)
    launch = commands.add_parser("serve", help="Start the local Gradio console")
    launch.add_argument("--host", default="127.0.0.1")
    launch.add_argument("--port", type=int, default=7860)
    return p


async def run_cli(args):
    cfg = Settings()
    updates = cfg.snapshot()
    if args.project is not None:
        updates["project"] = args.project
    if args.concurrency is not None:
        updates["concurrency"] = args.concurrency
    cfg = Settings(**updates, token=cfg.token)
    values = {k: getattr(args, k + "_column") for k in ("input", "output", "input_label", "output_label")}
    # Unspecified fields retain auto-detection, even with a partial manual override.
    data = load_dataset(args.dataset, args.mode, max_bytes=cfg.max_file_bytes)
    if any(v is not None for v in values.values()):
        mapping = ColumnMapping(
            **{**data.mapping.model_dump(), **{k: v for k, v in values.items() if v is not None}}
        )
        data = load_dataset(args.dataset, args.mode, mapping, cfg.max_file_bytes)
    if data.errors:
        print(json.dumps({"validation_errors": data.errors}), file=sys.stderr)
        if not args.skip_invalid:
            raise ValueError("Dataset has invalid rows; fix them or use --skip-invalid")
    if args.no_persist and args.output_dir:
        raise ValueError("--no-persist conflicts with --output-dir")
    opts = (
        ScanOptions.model_validate_json(args.scan_options.read_text()) if args.scan_options else ScanOptions()
    )
    client = DemoClient() if args.demo else F5Client(cfg, options=opts)
    cancel = Cancellation()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, cancel.cancel)
    try:
        async with client:
            run = await evaluate(
                data,
                client,
                args.mode,
                args.strategy,
                concurrency=cfg.concurrency,
                cancel=cancel,
                config={
                    **cfg.snapshot(),
                    "scan_options": opts.model_dump(),
                    "mapping": data.mapping.model_dump(),
                    "invalid_rows": data.errors,
                },
            )
    finally:
        loop.remove_signal_handler(signal.SIGINT)
    reports = []
    if args.output_dir or (cfg.persist and not args.no_persist):
        reports = [str(p) for p in export_run(run, args.output_dir or cfg.result_dir)]
    print(
        json.dumps(
            {
                "run_id": run.id,
                "source": run.source,
                "status": run.status,
                "metrics": summarize(run),
                "reports": reports,
            },
            indent=2,
        )
    )
    return 130 if run.status == "cancelled" else 2 if run.status == "completed_with_errors" else 0


def main(argv=None):
    args = parser().parse_args(argv)
    configure_logging()
    try:
        if args.command == "serve":
            from .ui.app import serve

            serve(args.host, args.port)
            return 0
        return asyncio.run(run_cli(args))
    except (ValueError, OSError) as exc:
        # Do not print validation errors that may contain environment credentials.
        if args.command == "serve":
            if isinstance(exc, OSError):
                print(
                    f"Could not start the web server on port {args.port}. "
                    "The port may already be in use. Open the existing app, stop its server, "
                    f"or try: guardrail-evaluator serve --port {args.port + 1}",
                    file=sys.stderr,
                )
            else:
                print("Invalid server configuration. Check .env settings, host and port.", file=sys.stderr)
        else:
            print(
                "Configuration, dataset or file error. Check arguments, labels, credentials and filesystem permissions.",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    sys.exit(main())
