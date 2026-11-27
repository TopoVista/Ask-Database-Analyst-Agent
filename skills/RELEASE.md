# Marketplace release preparation

Verified 2026-11-27 against Agensi documentation: one ZIP may contain a pack
of 2–50 skills; each must include `SKILL.md` with `name` and `description`.
The marketplace scans for secrets, dangerous commands, network access and
prompt injection. Keep source text/scripts only; do not bundle virtual
environments or credentials. The packaging helper makes a local ZIP but does
not submit it.

Historical Metric Debugger is the first listing candidate because it calls the
real deterministic attribution capability rather than providing prompt-only
advice.
