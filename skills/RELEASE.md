# Marketplace release preparation

Rechecked 2026-11-28 against Agensi's current terms and seller guidance:
creators submit a ZIP with a valid `SKILL.md`; submissions receive security
scanning and manual review. The available public material does not establish
that every agent host supports local dependency installation or temporary
script execution. Keep source text/scripts only; do not bundle virtual
environments, credentials, or external-product routing. The packaging helper
makes a local ZIP but does not submit it.

The frozen Historical Metric Debugger 0.1.0 archive has a documented
off-platform-routing submission risk. Do not submit it unchanged; see
`release/agensi/MARKETPLACE_RECHECK_2026-11-28.md` for the precise gate.

Historical Metric Debugger is the first listing candidate because it calls the
real deterministic attribution capability rather than providing prompt-only
advice.
