# MetricTrace — SQL & Data Regression Debugger

Find out why a business metric changed by replaying old and new SQL definitions against old and new CSV/Parquet snapshots. MetricTrace runs four deterministic cells, then separates the numerical change into data, definition, and interaction effects with symmetric attribution.

For analytics engineers, finance teams, and data owners investigating dashboard restatements or historical metric disputes. Inputs are two retained dataset versions and two SQL definitions. Outputs are a reproducible JSON evidence report and optional Markdown summary.

Unlike a text-to-SQL prompt, this skill executes bounded local DuckDB queries against user-authorized files, fingerprints inputs, validates SQL and schemas, and verifies the report. It never fabricates missing historical values.

Local mode requires Python 3.11+ and installs no hosted infrastructure, database, AI key, or telemetry. CSV and Parquet are supported; multi-table joins require an explicit table-to-file manifest. Suggested experimental one-time launch price: $7.99.

Marketplace status: technically prepared, not submitted or marketplace-approved. Review the license decision and current marketplace rules before submission.
