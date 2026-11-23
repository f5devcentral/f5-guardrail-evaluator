# Research and attribution

Reviewed the public [f5devcentral/prompt-evaluator](https://github.com/f5devcentral/prompt-evaluator) README, shared client, evaluation helpers, sequential evaluator, concurrent evaluator, reporting implementation and OpenAPI snapshot on 2026-11-20 before implementation. The workspace also contained an older local Prompt Evaluator checkout; it was inspected read-only and not used as the source of the current API contract.

Upstream behaviours retained conceptually: scan-only operation without providers, project selection, CSV/JSONL datasets, label aliases, separate positive detection and enforcement decisions, bounded concurrency, per-row errors, original line provenance, confusion matrices, scanner evidence, latency statistics and exportable reports. The public concurrent evaluator uses threaded synchronous requests; this application uses bounded asyncio workers and httpx. The upstream PDF reports use ReportLab and matplotlib; this application uses self-contained Plotly HTML with browser printing rather than copying that reporting stack.

The implementation was written anew around Pydantic models and a standalone package. No upstream source file was copied into this repository. The upstream public version carries Apache-2.0 headers including “Copyright 2026 Andy Ryan”; that attribution is acknowledged here. If future changes directly copy upstream code, retain its notices and include the appropriate Apache-2.0 licence. The older local checkout's licence is not used to infer the public repository's licensing.

Official sources consulted:

- [Scan operation](https://docs.aisecurity.f5.com/operations/post_scans.html)
- [Project discovery](https://docs.aisecurity.f5.com/operations/get_projects.html)
- [Project guardrails](https://docs.aisecurity.f5.com/operations/get_projects_project_scanners.html)
- [Authentication/token setup](https://docs.aisecurity.f5.com/api-docs/first-steps.html)
- [Response scan configuration](https://docs.aisecurity.f5.com/guardrails/add-scans-guardrails.html)

Validated request keys, aggregate outcome enum, scanner evidence fields, optional recording ID, response direction, request linkage, bearer authentication, default flag-only behaviour and project pagination. No numeric rate limit or POST idempotency guarantee was found; the client does not invent either. Live tenant compatibility remains unverified.
