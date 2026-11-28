# Agensi marketplace recheck — 2026-11-28

This is a release-gate record, not an approval claim. It was checked against
Agensi's Terms of Service (last updated 2026-11-25) and its seller page on
2026-11-28.

## Confirmed current requirements

- Submit a ZIP containing a valid `SKILL.md`; the current seller guidance
  illustrates optional scripts and reference files in the ZIP.
- New submissions receive automated security scanning and manual review before
  going live. Neither local validation nor a clean ZIP establishes approval.
- A paid listing needs an Agensi account and an enabled Stripe Connect or
  Zoneless payout method; identity/KYC steps are external creator actions.
- A listing and its package must not route buyers to obtain, use, try, or buy
  a related product outside Agensi. Buyer-facing copy must not include
  off-platform promotional links.
- Agensi delivers a purchased skill through the buyer's connected agent; it is
  not a downloadable customer artifact. The seller page nevertheless describes
  ZIP upload as the creator submission format.

## Frozen 0.1.0 archive finding

`historical-metric-debugger.zip` has the recorded SHA-256
`5f7269cd25c019f2c57ae552ea18c5429d9c55783598ff4aedfb46d286e93c00` and is
preserved unchanged. Its `SKILL.md` says that users should use an installed
MetricTrace Lite package outside marketplace delivery for unsupported
multi-table/report-verification workflows. Although it contains no external
URL, that routing is inconsistent with the current off-platform restriction
and is a submission risk.

Do not overwrite or submit the frozen archive. Resolving this requires the
copyright holder to authorize a new versioned archive whose skill reports those
workflows as unsupported instead of directing buyers elsewhere. No such new
archive was generated in this recheck.

## Dependency and execution conclusion

The archive contains source/text only and declares `duckdb==1.1.3` and
`sqlglot==25.31.4`; it does not bundle wheels, virtual environments, native
binaries, credentials, telemetry, or a seller-operated service. The skill
requires a host with Python 3.11+ and explicit authorization to install those
dependencies. Agensi's public terms/seller page do not establish that every
connected agent permits Python installation or temporary-script execution, so
that remains an environment-specific limitation rather than a marketplace
compatibility claim.

## SQL Regression Guardian packaging decision

The existing `metric-regression-investigator` skill is not a release candidate
under the current marketplace delivery model. Its instructions require an
externally installed `metrictrace-lite` package. Current packaging guidance
states that a buyer agent receives package text files only and runs each script
in isolation, so it cannot rely on another packaged script or on an off-package
companion installation. Current marketplace guidance also prohibits a skill
that depends on a seller-operated service or directs buyers to a separate
sign-up, access code, or free version.

No SQL Regression Guardian ZIP was generated. A future release must use a
small, self-contained runner generated from the shared deterministic source,
declare only well-known local Python dependencies, remain under the current
script review guidance, and be validated from an extracted temporary directory.
It must not silently copy or hand-maintain a divergent regression algorithm.

Current packaging limits observed on 2026-11-28: one ZIP; valid `SKILL.md`
frontmatter; 50 MB website-upload limit; no bundled virtual environments or
dependency trees; buyer delivery limited to `SKILL.md` files plus up to 200
other text files within six million characters. These are a release gate, not
marketplace approval.

## Manual gates still required

1. Copyright-holder authorization for the replacement version and its version
   number.
2. Creator account, payout/KYC setup, and listing details.
3. Manual ZIP upload and Agensi's security/review outcome.

No listing was uploaded, submitted, approved, published, priced, or sold.
