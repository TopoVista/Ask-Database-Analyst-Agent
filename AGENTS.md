# Engineering guidelines

- Prefer the smallest clear implementation that preserves behavior; remove duplication rather than compressing code into hard-to-maintain forms.
- Use deterministic, schema- or data-driven logic before an LLM. Call OpenAI only where it materially improves reasoning or narrative quality.
- Keep specialist workloads bounded for the single 512 MB Render service.
- Preserve the dashboard’s polished visual quality while favoring evidence-backed chart recommendations over decorative UI.
- Verify backend and frontend changes with the relevant tests and production build before committing.
