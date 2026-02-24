#!/usr/bin/env python3
"""
ScholarFactCheck — WordPress XML → Static HTML Generator
Usage:  python3 generate.py
Output: creates one folder/index.html per published post/page
"""

import xml.etree.ElementTree as ET
import re, os, html, textwrap
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
XML_FILE    = "theonlinescholarfactcheck.WordPress.2026-02-24.xml"
OUTPUT_DIR  = Path(".")          # writes into current directory (repo root)
ADSENSE_ID  = "ca-pub-7205603150750890"   # your real ID found in the XML

# ── Thinker nav map ───────────────────────────────────────────────────────────
NAV_LINKS = [
    ("/", "Home"),
    ("/ben-shapiro-bio-and-positions/", "Ben Shapiro"),
    ("/jordan-peterson-bio-positions/", "Jordan Peterson"),
    ("/sam-harris-bio/", "Sam Harris"),
    ("/noam-chomsky-bio-positions/", "Noam Chomsky"),
    ("/christopher-hitchens-bio-and-positions/", "Christopher Hitchens"),
]

# ── Related pages: slug prefix → list of (url, label) ───────────────────────
RELATED = {
    "ben-shapiro": [
        ("/ben-shapiro-bio-and-positions/", "Ben Shapiro — All Positions"),
        ("/jordan-peterson-bio-positions/", "Jordan Peterson — All Positions"),
        ("/ben-shapiro-on-socialism/", "Shapiro on Socialism"),
    ],
    "jordan-peterson": [
        ("/jordan-peterson-bio-positions/", "Jordan Peterson — All Positions"),
        ("/ben-shapiro-bio-and-positions/", "Ben Shapiro — All Positions"),
        ("/noam-chomsky-jordan-peterson/", "Chomsky vs Peterson"),
    ],
    "sam-harris": [
        ("/sam-harris-bio/", "Sam Harris — Bio"),
        ("/free-will-arguments-and-rebuttals/", "Free Will: Arguments & Rebuttals"),
    ],
    "noam-chomsky": [
        ("/noam-chomsky-bio-positions/", "Noam Chomsky — All Positions"),
        ("/noam-chomsky-on-steven-pinker-and-vice-versa/", "Chomsky vs Pinker"),
        ("/noam-chomsky-jordan-peterson/", "Chomsky vs Peterson"),
    ],
    "christopher-hitchens": [
        ("/christopher-hitchens-bio-and-positions/", "Hitchens — All Positions"),
        ("/christopher-hitchens-on-noam-chomsky-and-vice-versa/", "Hitchens vs Chomsky"),
    ],
}

def get_related(slug):
    for prefix, links in RELATED.items():
        if slug.startswith(prefix):
            return links
    return [
        ("/ben-shapiro-bio-and-positions/", "Ben Shapiro — All Positions"),
        ("/jordan-peterson-bio-positions/", "Jordan Peterson — All Positions"),
        ("/free-will-arguments-and-rebuttals/", "Free Will: Arguments & Rebuttals"),
    ]

def get_thinker(slug):
    """Return thinker name + bio url from slug, or None."""
    thinkers = {
        "ben-shapiro":         ("Ben Shapiro",         "/ben-shapiro-bio-and-positions/",  "Conservative commentator, author, and co-founder of The Daily Wire."),
        "jordan-peterson":     ("Jordan Peterson",     "/jordan-peterson-bio-positions/",   "Clinical psychologist, professor, and author of 12 Rules for Life."),
        "sam-harris":          ("Sam Harris",          "/sam-harris-bio/",                  "Neuroscientist, philosopher, and author. Co-founder of Project Reason."),
        "noam-chomsky":        ("Noam Chomsky",        "/noam-chomsky-bio-positions/",       "Linguist, philosopher, and prominent left-wing political commentator."),
        "christopher-hitchens":("Christopher Hitchens","/christopher-hitchens-bio-and-positions/", "Journalist, author, and outspoken atheist. 1949–2011."),
    }
    for key, val in thinkers.items():
        if slug.startswith(key):
            return val
    return None

def get_breadcrumb(slug, title):
    thinker = get_thinker(slug)
    if thinker:
        name, bio_url, _ = thinker
        return f'''
        <a href="/" class="hover:text-accent transition-colors">Home</a>
        <span>/</span>
        <a href="{bio_url}" class="hover:text-accent transition-colors">{name}</a>
        <span>/</span>
        <span class="text-ink">{html.escape(title)}</span>'''
    return f'''
        <a href="/" class="hover:text-accent transition-colors">Home</a>
        <span>/</span>
        <span class="text-ink">{html.escape(title)}</span>'''

def clean_content(raw):
    """Strip Divi/WP builder noise, old ad tags, keep readable HTML."""
    text = raw or ""
    # Remove Divi shortcodes
    text = re.sub(r'\[et_pb_[^\]]*\]', '', text)
    text = re.sub(r'\[/et_pb_[^\]]*\]', '', text)
    # Remove WP block comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    # Remove old AdSense ins tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ins\s+class=["\']adsbygoogle["\'][^>]*>.*?</ins>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ins\s+class=["\']adsbygoogle["\'][^>]*/>', '', text)
    # Remove leftover WP classes on spans
    text = re.sub(r'<span\s+class="s\d+">(.*?)</span>', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'<p\s+class="p\d+">', '<p>', text)
    # Clean up excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def nav_html(current_slug=""):
    links = ""
    for url, label in NAV_LINKS:
        active = 'text-accent' if url.strip('/') == current_slug else ''
        links += f'<a href="{url}" class="nav-link {active}">{label}</a>\n        '
    return links

def related_html(slug):
    items = ""
    for url, label in get_related(slug):
        items += f'<li><a href="{url}" class="text-sm hover:text-accent transition-colors nav-link">{label}</a></li>\n              '
    return items

def sidebar_html(slug):
    thinker = get_thinker(slug)
    thinker_card = ""
    if thinker:
        name, bio_url, desc = thinker
        thinker_card = f'''
        <div class="bg-cream border border-rule rounded p-5">
          <p class="font-mono text-xs uppercase tracking-widest text-muted mb-3">About the Thinker</p>
          <h3 class="font-display font-bold text-xl mb-1">{name}</h3>
          <p class="text-sm text-muted leading-relaxed mb-3">{desc}</p>
          <a href="{bio_url}" class="text-accent font-mono text-xs uppercase tracking-wider hover:underline">Full Bio &amp; All Positions →</a>
        </div>'''

    return f'''{thinker_card}
        <div class="bg-cream border border-rule rounded p-5">
          <p class="font-mono text-xs uppercase tracking-widest text-muted mb-3">Related Pages</p>
          <ul class="space-y-2">
              {related_html(slug)}
          </ul>
        </div>
        <!-- Sidebar ad -->
        <ins class="adsbygoogle"
             style="display:block"
             data-ad-client="{ADSENSE_ID}"
             data-ad-slot="1012006609"
             data-ad-format="auto"
             data-full-width-responsive="true"></ins>
        <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>'''

def build_page(title, slug, content_html, pub_date):
    """Return a complete HTML string for one page."""
    safe_title = html.escape(title)
    desc = re.sub('<[^>]+>', '', content_html)
    desc = ' '.join(desc.split())[:155]
    if len(desc) == 155:
        desc += '…'
    desc = html.escape(desc)

    formatted_date = ""
    machine_date = ""
    try:
        dt = datetime.strptime(pub_date, "%Y-%m-%d %H:%M:%S")
        formatted_date = dt.strftime("%B %Y")
        machine_date = dt.strftime("%Y-%m-%d")
    except Exception:
        formatted_date = "2020"
        machine_date = "2020-01-01"

    # Wrap first paragraph in lede class for drop cap
    first_para_done = [False]
    def add_lede(m):
        if not first_para_done[0]:
            first_para_done[0] = True
            return '<p class="lede font-body text-lg leading-relaxed mb-6">'
        return '<p class="text-lg leading-relaxed mb-6">'
    body = re.sub(r'<p>', add_lede, content_html)
    # Style h2/h3 headings
    body = re.sub(r'<h2>', '<h2 class="font-display font-bold text-2xl mt-10 mb-3">', body)
    body = re.sub(r'<h3>', '<h3 class="font-display font-bold text-xl mt-8 mb-2">', body)
    # Style links
    body = re.sub(r'<a ', '<a class="text-accent underline underline-offset-2 hover:opacity-80 transition-opacity" ', body)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe_title} | Scholar Fact Check</title>
  <meta name="description" content="{desc}" />
  <link rel="canonical" href="https://scholarfactcheck.com/{slug}/" />
  <meta property="og:title" content="{safe_title} | Scholar Fact Check" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:url" content="https://scholarfactcheck.com/{slug}/" />
  <meta property="og:type" content="article" />
  <meta property="og:image" content="https://scholarfactcheck.com/assets/og-default.jpg" />

  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;0,8..60,600;1,8..60,300;1,8..60,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />

  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          fontFamily: {{
            display: ['"Playfair Display"', 'Georgia', 'serif'],
            body:    ['"Source Serif 4"', 'Georgia', 'serif'],
            mono:    ['"JetBrains Mono"', 'monospace'],
          }},
          colors: {{
            ink:    '#0f0e0d', paper: '#f7f4ef', cream: '#ede9e1',
            rule:   '#d4cfc6', accent: '#b5451b', muted: '#7a7066',
          }},
        }}
      }}
    }}
  </script>

  <style>
    body {{
      background-color: #f7f4ef;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='400' height='400' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
    }}
    .rule        {{ border:none; border-top:1px solid #d4cfc6; }}
    .rule-accent {{ border:none; border-top:3px solid #b5451b; }}
    .lede::first-letter {{
      font-family:'Playfair Display',Georgia,serif; font-size:4.2rem;
      font-weight:900; line-height:0.8; float:left; margin:0.05em 0.08em 0 0; color:#b5451b;
    }}
    html {{ scroll-behavior:smooth; }}
    .nav-link {{ position:relative; }}
    .nav-link::after {{
      content:''; position:absolute; bottom:-2px; left:0;
      width:0; height:2px; background:#b5451b; transition:width 0.25s ease;
    }}
    .nav-link:hover::after {{ width:100%; }}
    .card-lift {{ transition:transform 0.2s ease,box-shadow 0.2s ease; }}
    .card-lift:hover {{ transform:translateY(-3px); box-shadow:0 8px 24px rgba(15,14,13,0.1); }}
    .fade-up {{ opacity:0; transform:translateY(20px); transition:opacity 0.5s ease,transform 0.5s ease; }}
    .fade-up.visible {{ opacity:1; transform:none; }}
  </style>

<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7205603150750890" crossorigin="anonymous"></script>
</head>
<body class="font-body text-ink antialiased">

  <!-- HEADER -->
  <header class="border-b border-rule bg-paper/90 backdrop-blur-sm sticky top-0 z-50">
    <div class="max-w-5xl mx-auto px-4 sm:px-6">
      <div class="flex items-center justify-between py-2 border-b border-rule text-xs font-mono text-muted tracking-widest uppercase">
        <span id="js-date"></span>
        <span>Tracking what thinkers actually say</span>
      </div>
      <div class="py-4 text-center">
        <a href="/" class="inline-block">
          <span class="font-display font-black text-3xl sm:text-4xl tracking-tight text-ink">Scholar</span><span class="font-display font-black text-3xl sm:text-4xl tracking-tight text-accent">Fact</span><span class="font-display font-black text-3xl sm:text-4xl tracking-tight text-ink">Check</span>
        </a>
        <p class="font-mono text-xs text-muted tracking-widest uppercase mt-1">Ideas · Arguments · Evidence</p>
      </div>
<!-- Mobile hamburger button -->
<div class="flex items-center justify-between pb-3 lg:hidden">
  <span class="font-mono text-xs uppercase tracking-widest text-muted">Menu</span>
  <button id="nav-toggle" class="text-ink p-1" aria-label="Toggle menu">
    <svg id="icon-open" xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
    </svg>
    <svg id="icon-close" xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 hidden" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
    </svg>
  </button>
</div>

<!-- Nav links: hidden on mobile until toggled, always visible on desktop -->
<nav id="nav-menu" class="hidden lg:flex items-center justify-center gap-6 pb-3 text-sm font-body font-semibold text-ink flex-wrap">
  <a href="/" class="nav-link">Home</a>
  <a href="/ben-shapiro-bio-and-positions/" class="nav-link">Ben Shapiro</a>
  <a href="/jordan-peterson-bio-positions/" class="nav-link">Jordan Peterson</a>
  <a href="/sam-harris-bio/" class="nav-link">Sam Harris</a>
  <a href="/noam-chomsky-bio-positions/" class="nav-link">Noam Chomsky</a>
  <a href="/christopher-hitchens-bio-and-positions/" class="nav-link">Christopher Hitchens</a>
</nav>
    </div>
  </header>

  <!-- LEADERBOARD AD -->
  <div class="max-w-5xl mx-auto px-4 sm:px-6 py-4">
    <ins class="adsbygoogle" style="display:block"
         data-ad-client="{ADSENSE_ID}" data-ad-slot="1012006609"
         data-ad-format="auto" data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
  </div>

  <main class="max-w-5xl mx-auto px-4 sm:px-6 pb-20">

    <!-- Breadcrumb -->
    <nav class="text-xs font-mono text-muted uppercase tracking-widest pt-6 pb-4 flex gap-2 flex-wrap">
      {get_breadcrumb(slug, title)}
    </nav>
    <hr class="rule" />

    <!-- Article header -->
    <header class="pt-8 pb-6 fade-up">
      <h1 class="font-display font-black text-4xl sm:text-5xl lg:text-6xl leading-tight text-ink mb-4">
        {safe_title}
      </h1>
      <p class="text-muted font-mono text-xs uppercase tracking-widest mb-6">
        Last updated <time datetime="{machine_date}">{formatted_date}</time>
      </p>
      <hr class="rule-accent" />
    </header>

    <!-- Two-column -->
    <div class="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-12 pt-6">

      <article class="fade-up prose-content">
        {body}

        <!-- Mid-article ad -->
        <div class="my-10">
          <ins class="adsbygoogle" style="display:block"
               data-ad-client="{ADSENSE_ID}" data-ad-slot="1012006609"
               data-ad-format="auto" data-full-width-responsive="true"></ins>
          <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
        </div>

        <div class="mt-10 bg-cream border border-rule rounded p-5 text-sm text-muted leading-relaxed">
          <p class="font-mono text-xs uppercase tracking-widest text-ink mb-2">Corrections Policy</p>
          Should we become aware that a thinker has changed their position, or if new evidence shows we have misconstrued their views, we will make the correction, note it here, and explain how we missed it.
        </div>
      </article>

      <aside class="space-y-6 fade-up">
        {sidebar_html(slug)}
      </aside>

    </div>
  </main>

  <!-- FOOTER -->
  <footer class="border-t border-rule bg-cream mt-10">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 py-10 grid grid-cols-1 sm:grid-cols-3 gap-8 text-sm text-muted">
      <div>
        <p class="font-display font-bold text-ink text-lg mb-2">ScholarFactCheck</p>
        <p class="leading-relaxed">Tracking what public intellectuals actually say — and whether it holds up.</p>
      </div>
      <div>
        <p class="font-mono text-xs uppercase tracking-widest text-ink mb-3">Thinkers</p>
        <ul class="space-y-1">
          <li><a href="/ben-shapiro-bio-and-positions/" class="hover:text-accent transition-colors">Ben Shapiro</a></li>
          <li><a href="/jordan-peterson-bio-positions/" class="hover:text-accent transition-colors">Jordan Peterson</a></li>
          <li><a href="/sam-harris-bio/" class="hover:text-accent transition-colors">Sam Harris</a></li>
          <li><a href="/noam-chomsky-bio-positions/" class="hover:text-accent transition-colors">Noam Chomsky</a></li>
          <li><a href="/christopher-hitchens-bio-and-positions/" class="hover:text-accent transition-colors">Christopher Hitchens</a></li>
        </ul>
      </div>
      <div>
        <p class="font-mono text-xs uppercase tracking-widest text-ink mb-3">Site</p>
        <ul class="space-y-1">
          <li><a href="/recent-posts/" class="hover:text-accent transition-colors">Recent Posts</a></li>
          <li><a href="/submission-guidelines/" class="hover:text-accent transition-colors">Submit a Claim</a></li>
          <li><a href="/contact-us/" class="hover:text-accent transition-colors">Contact</a></li>
          <li><a href="/privacy-policy-2/" class="hover:text-accent transition-colors">Privacy Policy</a></li>
        </ul>
      </div>
    </div>
    <div class="border-t border-rule text-center py-4 font-mono text-xs text-muted">
      © <span id="js-year"></span> ScholarFactCheck.com · Not affiliated with any thinker or organization
    </div>
  </footer>

  <script>
    const d = document.getElementById('js-date');
    if (d) d.textContent = new Date().toLocaleDateString('en-US', {{weekday:'long',year:'numeric',month:'long',day:'numeric'}});
    const y = document.getElementById('js-year');
    if (y) y.textContent = new Date().getFullYear();
    const obs = new IntersectionObserver(entries => {{
      entries.forEach(e => {{ if (e.isIntersecting) {{ e.target.classList.add('visible'); obs.unobserve(e.target); }} }});
    }}, {{threshold: 0.1}});
    document.querySelectorAll('.fade-up').forEach(el => obs.observe(el));
    // Hamburger menu toggle
    const toggle = document.getElementById('nav-toggle');
    const menu = document.getElementById('nav-menu');
    const iconOpen = document.getElementById('icon-open');
    const iconClose = document.getElementById('icon-close');
    if (toggle) {{
      toggle.addEventListener('click', () => {{
        menu.classList.toggle('hidden');
        iconOpen.classList.toggle('hidden');
        iconClose.classList.toggle('hidden');
      }});
    }}
  </script>

</body>
</html>'''


def main():
    tree = ET.parse(XML_FILE)
    root = tree.getroot()
    items = root.findall('.//item')

    built = 0
    skipped = 0

    for item in items:
        pt  = item.find('{http://wordpress.org/export/1.2/}post_type')
        st  = item.find('{http://wordpress.org/export/1.2/}status')
        if pt is None or st is None: continue
        if pt.text not in ('post', 'page'): continue
        if st.text != 'publish': continue

        title_el   = item.find('title')
        slug_el    = item.find('{http://wordpress.org/export/1.2/}post_name')
        date_el    = item.find('{http://wordpress.org/export/1.2/}post_date')
        content_el = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')

        title   = title_el.text.strip()   if title_el   is not None and title_el.text   else ""
        slug    = slug_el.text.strip()    if slug_el    is not None and slug_el.text    else ""
        date    = date_el.text.strip()    if date_el    is not None and date_el.text    else ""
        raw     = content_el.text         if content_el is not None                    else ""

        if not slug or not title:
            skipped += 1
            continue

        # Skip utility/system pages
        skip_slugs = {'sample-page', 'privacy-policy', 'author', 'blog', 'page'}
        if slug in skip_slugs:
            skipped += 1
            continue

        cleaned = clean_content(raw)

        # Skip pages with almost no content after cleaning
        plain = re.sub('<[^>]+>', '', cleaned).strip()
        if len(plain) < 100:
            skipped += 1
            print(f"  SKIP (too short): {slug}")
            continue

        html_out = build_page(title, slug, cleaned, date)

        out_dir = OUTPUT_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "index.html"
        out_file.write_text(html_out, encoding='utf-8')
        built += 1
        print(f"  ✓  {slug}/index.html")

    print(f"\nDone — {built} pages built, {skipped} skipped.")


if __name__ == "__main__":
    main()
