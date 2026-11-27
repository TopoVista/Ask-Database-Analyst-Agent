# FAQ

## Does it retrieve history from my database?

No. Provide historical snapshots that you retained. MetricTrace does not invent or recover data that was never preserved.

## Does it upload my data?

No. Lite runs locally. Remote Platform mode is a separate authenticated option.

## What does the report prove?

It proves the reported four computations and numerical reconciliation for the supplied files and definitions. It does not prove causality or authenticate an author.

## What do I install?

`pip install metrictrace-lite` from the reviewed local wheel, then use `metrictrace --help`. Python 3.11+ is currently tested on Windows; Linux installation is supported by packaging but has not yet been exercised in this workspace.

## Can it run an MCP server?

Install the optional `mcp` dependency and configure `METRICTRACE_ALLOWED_DATA_DIRS`. The server exposes only local inspection, validation, replay, and report verification.
