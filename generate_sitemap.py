#!/usr/bin/env python3
"""
ScholarFactCheck — Sitemap Generator
Usage:  python3 generate_sitemap.py
Output: sitemap.xml in repo root
"""

from pathlib import Path
from datetime import datetime

BASE_URL = "https://scholarfactcheck.com"

def generate_sitemap():
    urls = []

    # Homepage
    urls.append((f"{BASE_URL}/", "weekly", "1.0"))

    # Find all index.html files (each = one page)
    for path in sorted(Path(".").glob("*/index.html")):
        slug = path.parent.name

        # Skip system files/folders
        skip = {
            'node_modules', 'assets', '.git',
            'privacy-policy', 'errors', 'careers',
            'the-scholar-fact-check'
        }
        if slug in skip:
            continue

        # Get last modified date from file
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        lastmod = mtime.strftime("%Y-%m-%d")

        # Bio/hub pages get higher priority
        if any(slug.endswith(s) for s in [
            'bio-and-positions', 'bio-positions', 'bio'
        ]):
            priority = "0.9"
            changefreq = "monthly"
        else:
            priority = "0.7"
            changefreq = "monthly"

        urls.append((f"{BASE_URL}/{slug}/", changefreq, priority, lastmod))

    # Build XML
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for entry in urls:
        url = entry[0]
        changefreq = entry[1]
        priority = entry[2]
        lastmod = entry[3] if len(entry) > 3 else datetime.now().strftime("%Y-%m-%d")

        lines.append('  <url>')
        lines.append(f'    <loc>{url}</loc>')
        lines.append(f'    <lastmod>{lastmod}</lastmod>')
        lines.append(f'    <changefreq>{changefreq}</changefreq>')
        lines.append(f'    <priority>{priority}</priority>')
        lines.append('  </url>')

    lines.append('</urlset>')

    sitemap = "\n".join(lines)
    Path("sitemap.xml").write_text(sitemap, encoding="utf-8")

    print(f"✓ sitemap.xml generated with {len(urls)} URLs")

if __name__ == "__main__":
    generate_sitemap()