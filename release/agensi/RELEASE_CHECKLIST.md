# Release checklist

- [x] Deterministic local replay, reports, CLI, and package metadata implemented.
- [x] Official Agensi packaging and seller pages reviewed on 2026-11-27.
- [x] Add the owner-authorized MIT license for Platform/shared engine and separate commercial notices for original premium materials.
- [x] Build wheel/sdist and install from artifacts in a clean environment.
- [x] Test MCP initialization, discovery, replay, report verification, and access rejection with an actual stdio client.
- [x] Test the generated Agensi temporary-script adapter outside the repository.
- [ ] Validate Linux and any claimed agent-host configuration.
- [x] Generate and inspect the single-skill ZIP: 6 text files, 7,572 bytes, no prohibited artifacts or secret-pattern matches.
- [x] Generate SHA-256 checksums for wheel, source distribution, and ZIP.
- [ ] Recheck marketplace rules, upload manually, and await independent review/approval.

Agensi's current documentation calls for ZIP packaging with a `SKILL.md` frontmatter containing `name` and `description`, scans submitted contents, and supports single-skill listings. Its scripts are copied individually to temporary files, so the candidate runner is self-contained and does not import sibling files. Recheck before submission because marketplace rules can change.
