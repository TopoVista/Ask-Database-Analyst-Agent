# MetricTrace Lite licensing review

Date reviewed: 2026-11-27. This is an engineering inventory, not legal advice.

## Repository findings

- No top-level `LICENSE`, `COPYING`, `NOTICE`, or repository copyright notice was found.
- Project source under `backend/`, `frontend/`, `skills/`, and `release/` has no declared SPDX identifier or copyright holder.
- Git history contains multiple author email/name identities. Git author metadata is not proof of copyright ownership, employment assignment, contributor agreements, or authority to grant a commercial licence.
- `docs/.docx_deps/` contains bundled third-party material and licence texts. It is unrelated to the Lite distribution and must never enter a Lite or marketplace archive.
- No copied/adapted third-party source was identified by the text scan of the Lite source. This is not a provenance guarantee; the owner must confirm provenance before sale.

## Direct Lite dependencies

| Component | Pinned use | Installed metadata licence | Distribution note |
| --- | --- | --- | --- |
| DuckDB | `duckdb==1.1.3` | MIT | Runtime dependency; do not bundle wheel/site-packages into an Agensi ZIP. |
| SQLGlot | `sqlglot==25.31.4` | MIT | Runtime dependency; do not bundle wheel/site-packages into an Agensi ZIP. |
| MCP SDK | optional `mcp>=1` | MIT | Only needed for standalone MCP integration, not the Agensi script. |
| HTTPX | optional remote extra | not part of core Lite | Only needed for authenticated Platform use. |

Installed package metadata is a useful engineering signal, not a substitute for preserving the authoritative upstream notices and terms. The full Platform carries additional dependencies and needs a separate dependency/provenance review before it is distributed.

## Authorized boundary

1. **Shared deterministic engine** — `backend/metrictrace_sdk/core.py`, `local_replay.py`, and reporting code are MIT licensed under `LICENSE`, with the authorized holder `Souradeep Ghosh`.
2. **MetricTrace Lite wheel/sdist** — MIT distribution of the shared engine with declared runtime dependencies and third-party notices.
3. **Full MetricTrace Platform** — FastAPI/frontend/storage/workers and their broader dependency set. Keep out of the Lite and Agensi artifacts; it is not required by local replay.
4. **Commercial skill materials** — original `SKILL.md`, listing, and marketplace copy use the separate commercial notice. The generated runner continues to be MIT because it embeds shared-engine code.

## Release decision

The owner authorized the above model and supplied the copyright holder name on 2026-11-27, subject to the stated personal-ownership assumption. This implementation cannot independently verify chain of title, assignment status, or all provenance. Do not submit the listing or publish package artifacts without a final human review.
