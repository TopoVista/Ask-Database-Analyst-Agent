# Security model

MetricTrace Lite accepts only explicit CSV/Parquet inputs, resolves their paths before process creation, enforces table and file-size allowlists, and blocks SQL file readers, URL functions, extensions, attachments, and undeclared tables. It does not send telemetry or perform runtime downloads.

MCP mode additionally requires `METRICTRACE_ALLOWED_DATA_DIRS`; an MCP caller cannot authorize an arbitrary path itself. Reports include basenames and hashes rather than absolute paths or records.

This is defense in depth, not a security sandbox. Run untrusted files and SQL in an appropriately isolated operating-system account or container.
