# F5 integration contract

Reviewed on 2026-11-20 using the [official scan operation](https://docs.aisecurity.f5.com/operations/post_scans.html), [projects operation](https://docs.aisecurity.f5.com/operations/get_projects.html), [project guardrails](https://docs.aisecurity.f5.com/operations/get_projects_project_scanners.html), [authentication setup](https://docs.aisecurity.f5.com/api-docs/first-steps.html), and [response scan setup](https://docs.aisecurity.f5.com/guardrails/add-scans-guardrails.html). The upstream evaluator's OpenAPI snapshot was also inspected for expanded field descriptions and enums. The official tenant API is authoritative when versions differ.

`POST {tenant}/backend/v1/scans`, `Authorization: Bearer <token>`, JSON body:

```json
{"input":"text to scan","project":"project name or ID","scanDirection":"request","flagOnly":false,"verbose":true,"disabled":[],"forceEnabled":[],"configOverrides":{}}
```

| Field | Handling |
|---|---|
| input | Required string in both directions |
| project | Name or ID; omitted if blank to use global default |
| scanDirection | Explicit `request` or `response` |
| requestPromptId | Optional response linkage; use matching input scan's returned ID, omit when absent/null |
| flagOnly | Explicit false by default; false preserves configured actions, it does not guarantee blocking |
| verbose | True to request per-scanner evidence |
| disabled / forceEnabled | Arrays of scanner IDs; validated as strings locally, UUID/access validity checked by server |
| configOverrides | Scanner ID → configuration object; server validates scanner-specific semantics |
| externalMetadata | Object with local run UUID, within documented size limits |

No provider, generation or invented context parameter is sent. `requestPromptId` links records; the documentation does not promise that it reconstructs conversational context. Output-only scans omit linkage and do not require an input scan. Recording can be disabled, producing a null ID. The URL normaliser accepts an origin, reverse-proxy prefix, or an existing `/backend/v1` base without duplicating the API suffix.

The response contains `result.outcome`, `result.scannerResults`, required `redactedInput`, optional/null `id`, and optional scanner configuration metadata. Aggregate outcomes: cleared, flagged, blocked, redacted. Individual outcomes passed/failed describe a policy check, not a transport error. Scanner `data.type=error` or an explicit error outcome makes the overall evaluation incomplete/error. Unknown/malformed responses are errors. Original JSON and redacted text are retained with credentials scrubbed.

`GET /backend/v1/projects` uses the documented `projects` array and `next` cursor pagination. Connection testing does not create scans. A project can also be entered directly by name or ID. Scanner selection/actions are inherited from the project unless explicit overrides are supplied; the UI does not edit the tenant's guardrail configuration.

## Retry policy

Connect/connect-timeout/pool failures are retried with bounded exponential backoff and jitter. Read/write timeouts or ambiguous transport failures are not replayed because the scan may already exist. HTTP 429/502/503/504 on read-only GET requests can be retried. Scan POST status retries are disabled unless explicitly opted in; duplicates and charges are possible, and the endpoint documents no idempotency guarantee. 401/403/422 are not retried. Retry-After seconds or HTTP dates are respected; a delay above 60 seconds ends the attempt with an explicit error instead of retrying earlier than requested. No undocumented tenant quota is assumed. Latency includes retry/backoff time.

## Live validation still required

No live tenant request was made while building this application. Mock tests verify construction, normalisation, project pagination, errors, timeouts and retries. Verify scan permissions, exact tenant version compatibility, response-enabled scanners, configured blocking, null recording IDs, request linkage, scanner metadata, redaction behaviour and actual rate limits on your tenant. The integration test is explicitly opt-in. Run a small synthetic set first and inspect the returned scanner evidence.
