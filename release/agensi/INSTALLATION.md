# Installation and host configuration

Build artifacts from `backend/`:

```bash
python -m build --wheel --sdist --outdir dist
python -m pip install dist/metrictrace_lite-0.1.0-py3-none-any.whl
metrictrace demo
```

The wheel is self-contained apart from its declared DuckDB and SQLGlot dependencies. It has no FastAPI, PostgreSQL, object-store, Clerk, OpenAI, Docker, or AI-key dependency.

The separate Agensi ZIP is not a wheel distribution. Its self-contained runner
requires the same two dependencies as an explicit, user-authorized host action;
it does not bundle them or assume every agent host permits installation.

For an MCP host that supports stdio, install the optional extra and configure an explicit file boundary:

```json
{
  "mcpServers": {
    "metrictrace-lite": {
      "command": "metrictrace-mcp",
      "env": { "METRICTRACE_ALLOWED_DATA_DIRS": "C:\\approved-metric-snapshots" }
    }
  }
}
```

Use the operating system's path separator if more than one directory is authorized. Do not claim support for a host until that host has run a protocol test.
