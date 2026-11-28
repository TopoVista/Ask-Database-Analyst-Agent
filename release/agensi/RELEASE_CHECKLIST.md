# Release checklist

- [x] Deterministic local replay, reports, CLI, and package metadata implemented.
- [x] Official Agensi terms and seller page rechecked on 2026-11-28.
- [x] Add the owner-authorized MIT license for Platform/shared engine and separate commercial notices for original premium materials.
- [x] Build wheel/sdist and install from artifacts in a clean environment.
- [x] Test MCP initialization, discovery, replay, report verification, and access rejection with an actual stdio client.
- [x] Test the generated Agensi temporary-script adapter outside the repository.
- [ ] Validate Linux and any claimed agent-host configuration.
- [x] Generate and inspect the single-skill ZIP: 6 text files, 7,572 bytes, no prohibited artifacts or secret-pattern matches.
- [x] Generate SHA-256 checksums for wheel, source distribution, and ZIP.
- [x] Build and validate the separately versioned `0.1.1` archive that removes
  the current-package off-platform-routing text while preserving 0.1.0.
- [ ] Complete creator account, eligible payout/KYC setup, manual upload, and
  independent review/approval.

As rechecked on 2026-11-28, Agensi requires a ZIP containing a valid
`SKILL.md` with frontmatter, applies an automated security scan and manual
review, and requires an enabled payout method before a paid listing can go
live. The seller page illustrates ZIPs containing scripts. The terms prohibit
listing/package material that routes buyers to obtain or use related products
outside Agensi; the frozen 0.1.0 archive must not be uploaded until the noted
wording has been resolved in an approved new version. Recheck immediately
before submission because marketplace rules can change.
