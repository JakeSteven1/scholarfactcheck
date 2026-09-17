# scholarfactcheck.com

Static site: plain HTML, Tailwind (Play CDN), vanilla JS. No build step.

**`*/index.html` are the canonical source.** Edit them directly. Each page is self-contained —
header, nav, footer, styles and scripts are repeated in every file — so a site-wide change means
editing every page (e.g. `sed -i` across `*/index.html` and `index.html`), and `check.py` verifies
the shared chrome is still intact afterwards.

```
index.html              homepage
<slug>/index.html       one folder per page; URL is /<slug>/
sitemap.xml             regenerate with: python3 check.py --write-sitemap
robots.txt, ads.txt, favicon.svg
check.py                pre-push checks (see below)
_archive/               the one-time WordPress → HTML migration, retired; never served, never re-run
```

## Adding or renaming a page

1. Copy an existing `<slug>/index.html`, keep the `<head>` and shared chrome, replace the article.
2. Set `<title>`, `<meta name="description">`, and `<link rel="canonical">` to `https://scholarfactcheck.com/<slug>/`.
3. `python3 check.py --write-sitemap` to add it to `sitemap.xml`.

## Before pushing

```
python3 check.py
```

Exits non-zero with a list of failures if any HTML file has unbalanced tags, a broken internal
link or asset path, a missing/duplicate `<h1>`, missing `<title>`/description, a canonical URL that
doesn't match its folder, missing Tailwind or shared header/footer, or if `sitemap.xml` is out of
sync with the pages on disk. Add `--write-sitemap` to rebuild the sitemap first. Stdlib only.
