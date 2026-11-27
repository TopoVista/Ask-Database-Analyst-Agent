# Agent-native distribution

The deterministic attribution algorithm now lives in
`app.domain.attribution`, independent of FastAPI and the frontend. The web
service uses it, `metrictrace_sdk` exposes a typed remote client, and the CLI
uses the same function for local A/B/C/D calculation.

```powershell
cd backend
python -m metrictrace_sdk.cli attribute --a 2400000 --b 2100000 --c 2220000 --d 1800000
python -m metrictrace_sdk.cli replay --api-url https://metrictrace.example --token <token> --workspace-id <id> --old-version-id <id> --new-version-id <id> --old-definition-id <id> --new-definition-id <id>
```

The CLI prints one JSON object and exits `0` for success, `2` for invalid
local values, `3` for a remote API error and `1` for an unexpected failure.

`metrictrace_sdk.mcp_server` is an optional stdio MCP server. It deliberately
exposes only `run_four_way_replay`, because it maps to a real underlying API.
State-changing use requires both an API token and explicit mutation enablement.
No placeholder MCP tools are shipped.

The `skills/` tree is a local, portable skill source tree. It is not evidence
of Agensi compatibility or approval. Agensi requirements were rechecked on
2026-11-28 and are recorded in
`release/agensi/MARKETPLACE_RECHECK_2026-11-28.md`; its current seller flow
uses creator-submitted ZIPs, security scanning and manual review. The frozen
Historical Metric Debugger 0.1.0 archive has a documented release gate and
must not be submitted unchanged. No submission is performed by this
repository.

## Local historical debugger

No API, Docker, AI key or database is required for a local file replay:

```powershell
python -m metrictrace_sdk.cli local-replay --old-dataset ../demo/local-old.csv --new-dataset ../demo/local-new.csv --old-sql "SELECT SUM(amount_inr) FROM source_data WHERE status = 'paid'" --new-sql "SELECT SUM(amount_inr) FROM source_data WHERE status = 'paid' AND channel <> 'marketplace'"
```

The execution process accepts only explicit CSV/Parquet paths, uses trusted
`source_data` registration, validates read-only SQL, applies DuckDB memory and
thread limits, and is terminated after its wall-clock deadline. This is bounded
process isolation, not a complete operating-system security sandbox.
