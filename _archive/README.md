# Archive — one-time WordPress migration

These files produced the site's `*/index.html` pages once, in September 2026, and are kept only
for provenance. **They are retired: `*/index.html` at the repo root are now the canonical source.**
Do not re-run `generate.py` — it would overwrite hand edits made since.

- `theonlinescholarfactcheck.WordPress.2026-02-24.xml` — the WordPress (WXR) export the pages were
  built from. Contains unpublished drafts and commenter e-mails/IPs; never serve it.
- `generate.py` — XML → HTML generator (Divi shortcode stripping, markup normalisation, copy fixes).
- `generate_sitemap.py` — sitemap builder (reads `<time datetime>` from each page).
