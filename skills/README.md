# MetricTrace agent skills

These portable skills use a local MetricTrace CLI for deterministic work or an
authenticated MetricTrace API for tenant-scoped remote execution. They contain
no credentials and never publish marketplace listings. See `RELEASE.md` for
Agensi packaging limits and release preparation.

Optional MCP mode exposes only implemented replay submission. Install the
`mcp` Python package separately, set a remote API URL/token, and set the
explicit mutation authorization environment variable for state-changing calls.
