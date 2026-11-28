# MetricTrace — SQL & Data Regression Debugger 0.1.1

This is the final locally validated 0.1.1 single-skill release archive. It
preserves all frozen 0.1.0 artifacts and their checksums unchanged. The 0.1.1
skill reports unsupported multi-table and report-verification workflows as
unsupported instead of routing users to a separate product or workflow.

## Artifact

- `release/historical-metric-debugger-0.1.1.zip`
- SHA-256: `bac18e4f22cbf982604ffce41d69e08c0f2b616a291ed474492f0f6427028c36`

## Validated local evidence

- SKILL.md format validation: passed.
- ZIP inspection: passed; six expected UTF-8 source/text files and no detected
  secret pattern, external link, prohibited binary/environment file, or
  off-platform routing.
- Fresh Python 3.11 virtual environment: installed only `duckdb==1.1.3` and
  `sqlglot==25.31.4`, then successfully executed the extracted runner.
- Canonical synthetic replay: A/B/C/D = 2,400,000 / 2,100,000 / 2,220,000 /
  1,800,000; total change = -600,000; reconciliation passed.
- Backend regression suite: `208 passed, 2 skipped` on Windows/Python 3.11.
- Frontend production build: passed with Next.js 14.2.35.

## Distribution status

The proposed listing remains local-first, CSV/Parquet only, with no AI API key
or seller-operated service. The archive has not been uploaded, submitted,
reviewed, approved, published, priced, or sold. Manual Agensi account,
payout/KYC, listing, upload, and independent review steps remain required.
Only Windows/Python 3.11 is validated; Linux and macOS are not claimed.
