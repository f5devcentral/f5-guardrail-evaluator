# Architecture

The dataset loader validates text/labels without network access and produces `Scenario` objects. The orchestrator accepts any asynchronous client implementing `scan(text, direction, request_id, scenario, run_id)`. UI and CLI both call this engine, then use the same summariser and exporters. No Gradio imports occur in the backend modules.

Bounded worker tasks take scenarios from an in-memory queue. Each worker performs at most one HTTP scan at a time. A limit of N scenarios therefore also bounds concurrent scan calls to N. Results are indexed by source order, independent of completion order. Cancellation uses a thread-safe event checked before starting a scenario and before its output stage; in-flight calls are not forcibly replayed or abandoned. Progress counts completed/cancelled scenarios. All scenarios remain represented after cancellation.

The client handles authentication, safe errors, retries and the documented wire format. Decision normalisation is separate. Pydantic result models retain raw JSON, original aggregate outcomes, individual scanners, IDs and local wall-clock latency including retries. Demo mode returns explicit synthetic fixtures through the same normaliser; it is not an approximation of F5's classifiers. Unspecified demo metadata defaults to cleared and must not be interpreted as a benchmark result.

Each `Run` has a UUID, UTC timestamp, mode, strategy, source marker, dataset filename/SHA-256, safe configuration and ordered scenario results. Settings tokens are excluded from model serialisation. A final recursive scrub removes the configured credential from the run, including echoes in dataset or API text. Error bodies and arbitrary exception messages are never persisted.

UI state is per Gradio session, expires after an hour, and holds only the latest run. Settings stay server-side. Run metrics are per-run and filters affect the evidence table, not denominators. Report generation is an explicit disk action unless persistence is enabled. Report folders are named by UUID and use restrictive permissions. The app binds locally and has no authentication/multi-user tenancy layer.

The internal paired schema intentionally differs from the F5 API schema. Response fixtures are sent as `input` on a response-direction scan. The app never executes scenario text, tools, shell commands or Python code, and never invokes a model provider.
