#!/usr/bin/env python3
"""
ScholarFactCheck — WordPress XML → Static HTML Generator
Usage:  python3 generate.py
Output: creates one folder/index.html per published post/page

All site-wide markup (header, nav, footer, sidebar, scripts) lives in this
file. Do NOT hand-edit the generated */index.html files — edit this file and
re-run it, otherwise the next regeneration silently reverts your change
(that is exactly what happened to the "auto ads only" commit).
"""

import xml.etree.ElementTree as ET
import re, os, html
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
XML_FILE    = "_source/theonlinescholarfactcheck.WordPress.2026-02-24.xml"
OUTPUT_DIR  = Path(".")          # writes into current directory (repo root)
ADSENSE_ID  = "ca-pub-7205603150750890"   # AdSense Auto Ads only — no manual slots
SITE_URL    = "https://scholarfactcheck.com"
CONTACT_EMAIL = "scholarfactcheck@gmail.com"

# Old WordPress homepage and utility pages that should not be rebuilt as articles
SKIP_SLUGS = {'sample-page', 'privacy-policy', 'author', 'blog', 'page', 'the-scholar-fact-check'}
# Slugs that exist but should not be advertised in the sitemap/nav
UTILITY_SLUGS = {'contact-us', 'errors', 'careers', 'recent-posts', 'submission-guidelines',
                 'privacy-policy-2', 'privacy-policy-3'}

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
        ("/ben-shapiro-on-socialism/", "Shapiro on Socialism"),
        ("/ben-shapiro-piers-morgan-debate/", "Shapiro vs Piers Morgan"),
        ("/jordan-peterson-bio-positions/", "Jordan Peterson — All Positions"),
    ],
    "jordan-peterson": [
        ("/jordan-peterson-bio-positions/", "Jordan Peterson — All Positions"),
        ("/jordan-peterson-vs-slavoj-zizek-full-debate-and-breakdown/", "Peterson vs Žižek"),
        ("/noam-chomsky-jordan-peterson/", "Chomsky on Peterson"),
        ("/ben-shapiro-bio-and-positions/", "Ben Shapiro — All Positions"),
    ],
    "sam-harris": [
        ("/sam-harris-bio/", "Sam Harris — Bio & Positions"),
        ("/sam-harris-on-free-will/", "Harris on Free Will"),
        ("/free-will-arguments-and-rebuttals/", "Free Will: Arguments & Rebuttals"),
    ],
    "noam-chomsky": [
        ("/noam-chomsky-bio-positions/", "Noam Chomsky — All Positions"),
        ("/noam-chomsky-on-steven-pinker-and-vice-versa/", "Chomsky vs Pinker"),
        ("/noam-chomsky-jordan-peterson/", "Chomsky on Peterson"),
        ("/christopher-hitchens-on-noam-chomsky-and-vice-versa/", "Hitchens vs Chomsky"),
    ],
    "christopher-hitchens": [
        ("/christopher-hitchens-bio-and-positions/", "Hitchens — All Positions"),
        ("/christopher-hitchens-on-noam-chomsky-and-vice-versa/", "Hitchens vs Chomsky"),
        ("/christopher-hitchens-on-abortion/", "Hitchens on Abortion"),
    ],
}
DEFAULT_RELATED = [
    ("/ben-shapiro-bio-and-positions/", "Ben Shapiro — All Positions"),
    ("/jordan-peterson-bio-positions/", "Jordan Peterson — All Positions"),
    ("/free-will-arguments-and-rebuttals/", "Free Will: Arguments & Rebuttals"),
    ("/gun-control-history-and-arguments/", "Gun Control: History & Arguments"),
]

THINKERS = {
    "ben-shapiro":         ("Ben Shapiro",         "/ben-shapiro-bio-and-positions/",  "Conservative commentator, author, and co-founder of The Daily Wire."),
    "jordan-peterson":     ("Jordan Peterson",     "/jordan-peterson-bio-positions/",   "Clinical psychologist, professor, and author of 12 Rules for Life."),
    "sam-harris":          ("Sam Harris",          "/sam-harris-bio/",                  "Neuroscientist, philosopher, and author. Host of the Making Sense podcast."),
    "noam-chomsky":        ("Noam Chomsky",        "/noam-chomsky-bio-positions/",      "Linguist, philosopher, and prominent left-wing political commentator."),
    "christopher-hitchens":("Christopher Hitchens","/christopher-hitchens-bio-and-positions/", "Journalist, author, and outspoken atheist. 1949–2011."),
}


def get_related(slug):
    for prefix, links in RELATED.items():
        if slug.startswith(prefix):
            # never link a page to itself
            return [(u, l) for (u, l) in links if u.strip('/') != slug]
    return DEFAULT_RELATED


def get_thinker(slug):
    for key, val in THINKERS.items():
        if slug.startswith(key):
            return val
    return None


# ── Copy fixes ────────────────────────────────────────────────────────────────
# Applied to every page's title and body. Only unambiguous typos, misspelled
# names and factual slips go here; anything stylistic stays in the source.
GLOBAL_FIXES = [
    # names
    (r"Danniel", "Daniel"), (r"Chomksy", "Chomsky"), (r"Hithcens", "Hitchens"),
    (r"Solzehenitsyn", "Solzhenitsyn"), (r"Judith Jarvis Thompson", "Judith Jarvis Thomson"),
    (r"Jim Crowe", "Jim Crow"), (r"Oberfell v\. Hodges", "Obergefell v. Hodges"),
    (r"Andrew Klavern", "Andrew Klavan"), (r"Jamie Lannister", "Jaime Lannister"),
    (r"Maester Eckhart", "Meister Eckhart"), (r"\bColin Noir\b", "Colion Noir"),
    (r"Prime Minister Justice Pierre Trudeau", "Prime Minister Pierre Trudeau"),
    (r"Nashville, Texas", "Nashville, Tennessee"),
    # free-will vocabulary
    (r"Incompatabilist", "Incompatibilist"), (r"incompatablist", "incompatibilist"),
    (r"incompatibles\b", "incompatibilism"),
    (r"combatabilist", "compatibilist"), (r"Compatabilist", "Compatibilist"), (r"compatabilist", "compatibilist"),
    (r"compatiblism", "compatibilism"), (r"Determinsm", "Determinism"), (r"indeterminsm", "indeterminism"),
    (r"determinsm", "determinism"),
    # plain typos
    (r"ommitted", "omitted"), (r"de-criminilzation", "decriminalization"), (r"[Aa]mmendemnt", "amendment"),
    (r"Ammendment", "Amendment"), (r"ammendment", "amendment"), (r"\bunderly\b", "underlie"),
    (r"cur[a]?tesy", "courtesy"), (r"Neddless", "Needless"), (r"unparralled", "unparalleled"),
    (r"bordering school", "boarding school"), (r"forwareded", "forwarded"), (r"improvng", "improving"),
    (r"reecieve", "receive"), (r"punction help", "punctuation help"), (r"Rank Choice Voting", "Ranked Choice Voting"),
    (r"gradated from, UCLA", "graduated from UCLA"), (r"enitrely", "entirely"), (r"highschool", "high school"),
    (r"the anser\b", "the answer"), (r"endulged", "indulged"), (r"Aright back", "Alright back"),
    (r"GRVOs", "GVROs"), (r"get to he meat", "get to the meat"), (r"whether someone days from", "whether someone dies from"),
    (r"At Berkley on", "At Berkeley on"), (r"Bernie sanders", "Bernie Sanders"), (r"in the the Post-Gazette", "in the Post-Gazette"),
    (r"The marriage of of", "The marriage of"), (r"Shapiro’s Ben position", "Shapiro’s position"),
    (r"casuaistry", "casuistry"), (r"I can’ think", "I can’t think"), (r"heall as well", "hell as well"),
    (r"Canaaties", "Canaanites"), (r"running its future sex life", "ruining its future sex life"),
    (r"nver befall", "never befall"), (r"\bDurng\b", "During"), (r"one in the same", "one and the same"),
    (r"OPEC \(Organization of the Petroleum Exporting Countries\)", "OECD (Organisation for Economic Co-operation and Development)"),
    (r"Attenance", "Attendance"), (r"socioligical", "sociological"), (r"agressively", "aggressively"),
    (r"stereotypica ", "stereotypical "), (r"deskptop", "desktop"), (r"troubel", "trouble"), (r"dissapoint", "disappoint"),
    (r"agruments", "arguments"), (r"reminiscient", "reminiscent"), (r"bioligical", "biological"), (r"\bver difficult", "very difficult"),
    (r"pblished", "published"), (r"opinined", "opined"), (r"canddiate", "candidate"), (r"pahmplet", "pamphlet"),
    (r"expereince", "experience"), (r"incapsulate", "encapsulate"), (r"athiest", "atheist"), (r"waining", "waning"),
    (r"adoped", "adopted"), (r"an omage", "an homage"), (r"public pulicy", "public policy"), (r"critque", "critique"),
    (r"occassion", "occasion"), (r"bi-product", "by-product"), (r"the populous\b", "the populace"), (r"\bwiling\b", "willing"),
    (r"easter religions", "eastern religions"), (r"less they step on an ant", "lest they step on an ant"),
    (r"price gauging", "price gouging"), (r"mother load", "mother lode"), (r"primary tenant of", "primary tenet of"),
    (r"and it’s tenants", "and its tenets"), (r"mormon church ones roughly", "Mormon church owns roughly"),
    (r"welcome site to have", "welcome sight to have"), (r"martyry producing", "martyr-producing"),
    (r"directed agains the left", "directed against the left"), (r"in plain english", "in plain English"),
    (r"This is particular article", "This particular article"), (r"formerly legal in Ontario", "formally legal in Ontario"),
    (r"the 2004 video of the video", "the 2004 Navy video"), (r"TV station KRLA-AM", "radio station KRLA-AM"),
    (r"first novel", "first book"), (r"his novel End of Faith", "his book The End of Faith"),
    (r"Perhaps more known for his debates then his books", "Perhaps better known for his debates than his books"),
    (r"more accurate about the weather tomorrow then at", "more accurate about the weather tomorrow than at"),
    (r"biologically then two men", "biologically than two men"),
    (r"\(as of 2/26/2019\)", "(as of 2/26/2020)"),
    (r"The death rate among the elderly, is at least 49% and probably higher\.", "The death rate among the elderly is substantially higher than among younger patients."),
    (r"post 2020 election fallout", "post-2018 midterm fallout"),
    (r"on his podcast \(then Making Sense\)", "on his podcast (then called Waking Up)"),
    # possessive / plural slips
    (r"it’s detractors", "its detractors"), (r"it’s importance", "its importance"), (r"it’s inception", "its inception"),
    (r"it’s scholarly legitimacy", "its scholarly legitimacy"), (r"it’s firing rate", "its firing rate"),
    (r"it’s relationship", "its relationship"), (r"it’s benefits", "its benefits"), (r"it’s release", "its release"),
    (r"it’s longitudinal", "its longitudinal"), (r"it’s critics", "its critics"), (r"it’s addition", "its addition"),
    (r"it’s purpose", "its purpose"), (r"it’s own novel", "its own novel"),
    (r"58% of American’s polled", "58% of Americans polled"), (r"shift in American’s views", "shift in Americans’ views"),
    (r"most American's agree", "most Americans agree"), (r"those American’s which", "those Americans who"),
    (r"reaction American’s may have had", "reaction Americans may have had"), (r"Californian’s may", "Californians may"),
    (r"republican’s are generally", "Republicans are generally"), (r"of philosopher’s adopted", "of philosophers adopted"),
    (r"coastline’s may", "coastlines may"), (r"human’s should", "humans should"), (r"the one’s at risk", "the ones at risk"),
    (r"the only one’s that", "the only ones that"), (r"shortage of doctor’s", "shortage of doctors"),
    (r"82% saying mother’s should", "82% saying mothers should"), (r"bump stock’s to be", "bump stocks to be"),
    (r"bump stock’s essentially", "bump stocks essentially"), (r"assault weapon's bans", "assault weapon bans"),
    (r"teacher’s should be given", "teachers should be given"), (r"Teacher’s Carrying", "Teachers Carrying"),
    (r"UFO’s", "UFOs"), (r"series of essay’s", "series of essays"),
    (r"the countries most successful", "the country’s most successful"), (r"the countries collective", "the country’s collective"),
    (r"the countries constitution", "the country’s constitution"), (r"the countries founding", "the country’s founding"),
    (r"the countries founders", "the country’s founders"), (r"the countries first", "the country’s first"),
    (r"the citizens right", "the citizen’s right"), (r"Employees freedom", "Employees’ freedom"),
    (r"the questioners remarks", "the questioner’s remarks"), (r"the naysayer argue", "the naysayers argue"),
    (r"about the voters want", "about what the voters want"),
    (r"stayed in the first amendment", "stayed in the Second Amendment"),
    # whitespace
    (r"  +", " "),
]

# Slug-specific fixes: {slug: [(pattern, replacement), ...]} — regex, DOTALL
PAGE_FIXES = {
    "ben-shapiro-on-alex-jones": [
        (r"David Hume’s spellbinding", "John Stuart Mill’s spellbinding"),
        (r"Hume argued", "Mill argued"), (r"the Hume argument", "the Mill argument"), (r"the Hume book", "the Mill book"),
        (r"written by Jonathan Haidt", "edited by Jonathan Haidt and Richard Reeves (All Minus One)"),
    ],
    "ben-shapiro-on-religion": [
        # paragraph copy-pasted from the abortion article
        (r"<p>Among Ben’s favorite arguments for Abortion is the fetal potential argument.*?</p>", ""),
    ],
    "ben-shapiro-on-abortion": [
        (r"Among Ben’s favorite arguments for Abortion is", "Among Ben’s favorite arguments against abortion is"),
    ],
    "ben-shapiro-cenk-uygur-debate": [(r"\s*\|\s*Watch Full", "")],
    "ben-shapiro-bio-and-positions": [
        (r"If you are unable to view the graph, try viewing on a mobile device or shrinking the size of your browser\.\s*", ""),
        (r"<h[1-6][^>]*>\s*Who are his fans\?\s*</h[1-6]>", "<h2>Who are his fans?</h2>"),
    ],
    "christopher-hitchens-bio-and-positions": [
        (r"\s*The graph below shows his relative popularity over time, followed by his popularity by region\.", ""),
    ],
    "jordan-peterson-bio-positions": [
        (r"initially graduated from the University of Toronto receiving a B\.A\. in Political Science", "initially graduated from the University of Alberta receiving a B.A. in Political Science"),
        (r"\s*Breakdown by country\s*is the following \(data via Google trends\):", ""),
    ],
    "jordan-peterson-vs-slavoj-zizek-full-debate-and-breakdown": [
        (r"by utilizing the oft cited Churchill quote that \"Capitalism is the worst economic system, except for all the others\.”",
         "by adapting Churchill’s oft-cited line about democracy: capitalism is the worst economic system, except for all the others."),
    ],
    "gun-control-history-and-arguments": [
        (r"Let’s state it clearly, in full, and then we’ll go over it\. The second amendment (<a[^>]*>)?states(</a>)?:",
         r"Let’s start with the Constitution’s militia clause (Article I, Section 8), which the \1amendment\2 builds on, and then the amendment itself:"),
    ],
    "david-pakman-on-joe-biden": [(r"if we become aware that Kyle\s+has changed", "if we become aware that David has changed")],
    "the-case-against-christopher-hedges": [(r"Hedge[’']s", "Hedges’"), (r"\bHedge\b", "Hedges")],
    # Google Trends charts were stripped with the scripts; drop the prose that described them
    "ben-shapiro-on-bernie-sanders": [(r"<h[1-6][^>]*>\s*Who is more popular\?\s*</h[1-6]>", "")],
    "jordan-peterson-on-bernie-sanders": [(r"<h[1-6][^>]*>\s*Jordan Peterson vs Bernie Sanders: Who is more popular\?.*?A score of 0 means there was not enough data for this term\.\s*</p>", "")],
    "noam-chomsky-on-joe-biden": [(r"<h[1-6][^>]*>\s*Who is more popular: Joe Biden vs Noam Chomsky\s*</h[1-6]>.*?A score of 0 means there was not enough data for this term\.\s*</p>", "")],
    "noam-chomsky-on-steven-pinker-and-vice-versa": [(r"<h[1-6][^>]*>\s*Pinker vs Chomsky: Who is more popular\?.*?more popular than Chomsky in the United States\.\s*</p>", "")],
    "noam-chomsky-jordan-peterson": [(r"<h[1-6][^>]*>\s*Noam vs Jordan[’']s Popularity In The United States.*?as small as a mobile device\.\s*</p>", "")],
    "noam-chomsky-bio-positions": [(r"<h[1-6][^>]*>\s*Who is searching for him\?.*?queries are for \"bananas\"\.\s*</p>", "")],
    "sam-harris-on-eckhart-tolle": [(r"<h[1-6][^>]*>\s*Who Is More Popular\?\s*</h[1-6]>", "")],
    "sam-harris-on-abortion": [(r"<iframe src=\"https://www\.pewforum\.org[^>]*>\s*</iframe>", "")],
    # Forms were a WordPress plugin; point people at the mailbox instead
    "contact-us": [
        (r"Please use the following form for issues over listings, jobs or any issue",
         f"Please email <a href=\"mailto:{CONTACT_EMAIL}\">{CONTACT_EMAIL}</a> for issues over listings, jobs or any issue"),
        (r"please use the form on the error page instead or the form in the section below this one\.", "please say so in the subject line."),
        (r"Please feel free to use this form as it is forwarded to the same place as the form on the errors page\.",
         f"Email <a href=\"mailto:{CONTACT_EMAIL}\">{CONTACT_EMAIL}</a> with the page URL, the claim in question and your source."),
    ],
    "errors": [
        (r"and we will get to work\.", f"and we will get to work. Send it to <a href=\"mailto:{CONTACT_EMAIL}\">{CONTACT_EMAIL}</a>."),
    ],
    "submission-guidelines": [
        (r"but you can also submit your query letter via the form at the end of this article",
         f"sent to <a href=\"mailto:{CONTACT_EMAIL}\">{CONTACT_EMAIL}</a>"),
        (r"when Word files are converted for WordPress they generally produce atrociously ugly HTML that takes fixing",
         "when Word files are converted to HTML they generally produce ugly markup that needs fixing"),
    ],
}

# WordPress-era disclaimers that duplicate the template's Corrections Policy box
BOILERPLATE = [
    r"(?:\*\*)?(?:As always, |As is tradition, |OK\. Now, as always, |Now, as always, |Now, |With that in mind, the same internal rules apply: if )?[Ss]hould we become aware that [^<]*?how we missed this\.\s*",
    r"Note that even though the subject of this article is deceased,[^<]*?about the subject\.\s*",
    r"As always, we will continue to accept errors[^<]*?on the relevant page\.\s*",
    r"As always, should we become aware that Noam has changed his mind[^<]*?on this page\.\s*",
    r"As always this document is a living document[^<]*?as they come in\.\s*",
    r"Outside of the disclaimer below about updating Ben's position as new information comes in, we'd love any feedback on this subject\. In the meantime, we'll work for a mechanism on the site that provides some of this functionality\. Perhaps a comments section\?\s*",
]

INTERNAL_LINK_FIXES = {
    "/ben-shapiro-bio-and-positions/ben-shapiro-on-marijuana-legalization": "/ben-shapiro-on-marijuana-legalization/",
    "/ben-shapiro-bio-and-positions/ben-shapiro-piers-morgan-debate": "/ben-shapiro-piers-morgan-debate/",
    "/contact": "/contact-us/",
    "/privacy-policy": "/privacy-policy-3/",
}


def norm_text(s):
    s = re.sub(r'<[^>]+>', '', s or '')
    s = html.unescape(s)
    return re.sub(r'[^a-z0-9]+', '', s.lower())


def apply_fixes(text, fixes):
    for pat, rep in fixes:
        text = re.sub(pat, rep, text, flags=re.DOTALL)
    return text


def fix_href(m):
    """Make internal links root-relative, repair known-bad ones, add trailing slash."""
    url = m.group(1)
    url = re.sub(r'^https?://(www\.)?(theonline)?scholarfactcheck\.com', '', url)
    if url in INTERNAL_LINK_FIXES:
        url = INTERNAL_LINK_FIXES[url]
    if url.startswith('/') and not url.startswith('//'):
        path, _, frag = url.partition('#')
        if path and not path.endswith('/') and '.' not in path.rsplit('/', 1)[-1]:
            path += '/'
        url = path + ('#' + frag if frag else '')
    return f'href="{url}"'


def clean_content(raw, slug, title):
    """Strip Divi/WP builder noise, old ad tags, and normalise markup."""
    text = raw or ""
    # 1. Divi slider modules — remove *including* their teaser captions
    text = re.sub(r'\[et_pb_slide\b[^\]]*\].*?\[/et_pb_slide\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\[et_pb_slider\b[^\]]*\].*?\[/et_pb_slider\]', '', text, flags=re.DOTALL)
    # 2. Remaining Divi shortcode tags
    text = re.sub(r'\[/?et_pb_[^\]]*\]', '', text)
    # 3. Comments, scripts, styles, old AdSense units
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<ins\s+class=["\']adsbygoogle["\'][^>]*>.*?</ins>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ins\s+class=["\']adsbygoogle["\'][^>]*/>', '', text)
    # 4. Divi placeholder copy
    text = re.sub(r'<p[^>]*>\s*Your content goes here\..*?</p>', '', text, flags=re.DOTALL)
    # 5. Amazon affiliate image widgets (endpoint is dead) and their tracking pixels
    text = re.sub(r'<a[^>]*amazon[^>]*>\s*<img[^>]*>\s*</a>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<img[^>]*amazon-adsystem[^>]*>', '', text, flags=re.IGNORECASE)
    # 6. Unwrap every <span>/<div> — WP/Word paste noise; also repairs <a><span>…</a>…</span> mis-nesting
    text = re.sub(r'</?(?:span|div)\b[^>]*>', '', text)
    # 7. Strip inline styles, paste classes and WP attributes from every tag
    text = re.sub(r'\s+style="[^"]*"', '', text)
    text = re.sub(r'\s+class="(?:[ps]\d+|Apple-[^"]*|attachment-[^"]*|wp-[^"]*)"', '', text)
    text = re.sub(r'\s+(?:srcset|sizes|border)="[^"]*"', '', text)
    text = re.sub(r'<(i|b)\b>', lambda m: '<em>' if m.group(1) == 'i' else '<strong>', text)
    text = re.sub(r'</(i|b)>', lambda m: '</em>' if m.group(1) == 'i' else '</strong>', text)
    # 8. In-body <h1>: drop if it repeats the page title, otherwise demote to <h2>
    def h1(m):
        return '' if norm_text(m.group(1)) == norm_text(title) else f'<h2>{m.group(1)}</h2>'
    text = re.sub(r'<h1\b[^>]*>(.*?)</h1>', h1, text, flags=re.DOTALL)
    # 9. Copy fixes
    text = apply_fixes(text, GLOBAL_FIXES)
    text = apply_fixes(text, PAGE_FIXES.get(slug, []))
    # 10. WordPress-era disclaimers (the template has a Corrections Policy box)
    for pat in BOILERPLATE:
        text = re.sub(pat, '', text, flags=re.DOTALL)
    # 11. Links: root-relative, repaired, trailing slash
    text = re.sub(r'href="([^"]*)"', fix_href, text)
    # 12. Empty inline/blocks left behind
    for _ in range(3):
        text = re.sub(r'<(em|strong|a)\b[^>]*>(?:\s|&nbsp;)*</\1>', '', text)
        text = re.sub(r'<(p|h[1-6]|li|blockquote|ul|ol)\b[^>]*>(?:\s|&nbsp;|<br\s*/?>)*</\1>', '', text)
    # 12b. WP sometimes nests <p><p>…</p> and leaves a dangling <p> at the end
    text = re.sub(r'<p\b[^>]*>\s*(?=<(?:p|h[1-6]|ul|ol|blockquote)\b)', '', text)
    text = re.sub(r'</p>(?:\s*</p>)+', '</p>', text)
    text = re.sub(r'<p\b[^>]*>(?:\s|&nbsp;)*$', '', text)
    # 13. First paragraph that merely repeats the title
    first = re.search(r'<p\b[^>]*>(.*?)</p>', text, flags=re.DOTALL)
    if first and norm_text(first.group(1)) == norm_text(title):
        text = text[:first.start()] + text[first.end():]
    # 14. Tidy whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def style_body(content_html):
    """Apply Tailwind classes to the cleaned WP markup."""
    body = content_html
    # Paragraphs (leave tweet-embed <p lang dir> alone)
    first_para_done = [False]
    def para(m):
        attrs = m.group(1) or ''
        if 'lang=' in attrs:
            return m.group(0)
        inner_probe = body[m.end():m.end() + 200]
        if not first_para_done[0]:
            first_para_done[0] = True
            plain = re.sub(r'<[^>]+>', '', inner_probe)
            if len(plain) > 80:
                return '<p class="lede text-lg leading-relaxed mb-6">'
        return '<p class="text-lg leading-relaxed mb-6">'
    body = re.sub(r'<p\b([^>]*)>', para, body)
    body = re.sub(r'<h2\b[^>]*>', '<h2 class="font-display font-bold text-2xl mt-10 mb-3">', body)
    body = re.sub(r'<h3\b[^>]*>', '<h3 class="font-display font-bold text-xl mt-8 mb-2">', body)
    body = re.sub(r'<h[4-6]\b[^>]*>', '<h4 class="font-display font-bold text-lg mt-6 mb-2">', body)
    body = re.sub(r'<ul\b[^>]*>', '<ul class="list-disc pl-6 mb-6 space-y-1 text-lg leading-relaxed">', body)
    body = re.sub(r'<ol\b[^>]*>', '<ol class="list-decimal pl-6 mb-6 space-y-1 text-lg leading-relaxed">', body)
    body = re.sub(r'<li\b[^>]*>', '<li>', body)
    body = re.sub(r'<blockquote\b(?![^>]*twitter-tweet)[^>]*>',
                  '<blockquote class="border-l-4 border-accent pl-5 my-8 italic text-muted">', body)
    body = re.sub(r'<blockquote\s+class="twitter-tweet"[^>]*>',
                  '<blockquote class="twitter-tweet bg-cream border border-rule rounded p-5 my-8 text-base">', body)
    body = re.sub(r'<a\b((?:(?!class=)[^>])*)>',
                  r'<a class="text-accent underline underline-offset-2 hover:opacity-80 transition-opacity"\1>', body)
    body = re.sub(r'<img\b[^>]*>', lambda m: re.sub(r'\s+class="[^"]*"', '', m.group(0))
                  .replace('<img', '<img class="max-w-full h-auto rounded my-6"', 1), body)
    # iframes: YouTube gets a 16:9 responsive box, others just stop overflowing
    def iframe(m):
        tag = m.group(1)
        if 'youtube.com/embed' in tag or 'youtu.be' in tag:
            tag = re.sub(r'\s+(?:width|height)="[^"]*"', '', tag)
            tag = tag.replace('<iframe', '<iframe class="absolute inset-0 w-full h-full"', 1)
            return f'<div class="relative w-full aspect-video my-8 rounded overflow-hidden">{tag}</iframe></div>'
        tag = re.sub(r'\s+width="[^"]*"', '', tag)
        return tag.replace('<iframe', '<iframe class="w-full max-w-full my-8"', 1) + '</iframe>'
    body = re.sub(r'(<iframe\b[^>]*>)\s*</iframe>', iframe, body)
    return body


def make_description(content_html, title):
    """First real paragraph, tags stripped WITH spaces, ≤155 chars."""
    def plain_text(s):
        s = re.sub(r'</?(?:p|h[1-6]|li|ul|ol|br|div|blockquote|iframe)\b[^>]*>', ' ', s)
        s = re.sub(r'<[^>]+>', '', s)
        return ' '.join(html.unescape(s).split())
    paras = re.findall(r'<p\b[^>]*>(.*?)</p>', content_html, flags=re.DOTALL)
    text = ''
    for p in paras:
        plain = plain_text(p)
        if len(plain) > 60 and norm_text(plain) != norm_text(title):
            text = plain
            break
    if not text:
        text = plain_text(content_html)
    if len(text) > 155:
        text = text[:154].rsplit(' ', 1)[0] + '…'
    return html.escape(text, quote=True)


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


def nav_html(current_slug=""):
    links = ""
    for url, label in NAV_LINKS:
        active = ' text-accent' if url.strip('/') == current_slug else ''
        links += f'    <a href="{url}" class="nav-link{active}">{label}</a>\n'
    return links


def related_html(slug):
    return "".join(
        f'            <li><a href="{url}" class="text-sm hover:text-accent transition-colors nav-link">{label}</a></li>\n'
        for url, label in get_related(slug))


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
{related_html(slug)}          </ul>
        </div>
        <div class="bg-cream border border-rule rounded p-5">
          <p class="font-mono text-xs uppercase tracking-widest text-muted mb-3">Spotted an error?</p>
          <p class="text-sm text-muted leading-relaxed mb-3">We correct the record when readers show us we got a position wrong.</p>
          <a href="/errors/" class="text-accent font-mono text-xs uppercase tracking-wider hover:underline">Report an error →</a>
        </div>'''


def head_html(title, desc, url, og_type="article", extra=""):
    safe_title = html.escape(title)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe_title} | Scholar Fact Check</title>
  <meta name="description" content="{desc}" />
  <link rel="canonical" href="{url}" />
  <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
  <meta property="og:title" content="{safe_title} | Scholar Fact Check" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:type" content="{og_type}" />
  <meta property="og:site_name" content="Scholar Fact Check" />
  <meta name="twitter:card" content="summary" />
{extra}
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
    .prose-content blockquote p:last-child {{ margin-bottom:0; }}
  </style>
  <noscript><style>.fade-up {{ opacity:1; transform:none; }}</style></noscript>

  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_ID}" crossorigin="anonymous"></script>
</head>'''


def header_html(current_slug=""):
    return f'''  <!-- HEADER -->
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
        <button id="nav-toggle" class="text-ink p-1" aria-label="Toggle menu" aria-controls="nav-menu" aria-expanded="false">
          <svg id="icon-open" xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
          <svg id="icon-close" xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 hidden" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
      <!-- Nav links: hidden on mobile until toggled, always visible on desktop -->
      <nav id="nav-menu" class="hidden lg:flex flex-col lg:flex-row items-center justify-center gap-3 lg:gap-6 pb-4 lg:pb-3 text-sm font-body font-semibold text-ink flex-wrap">
{nav_html(current_slug)}      </nav>
    </div>
  </header>
'''


def footer_html():
    return '''  <!-- FOOTER -->
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
          <li><a href="/errors/" class="hover:text-accent transition-colors">Report an Error</a></li>
          <li><a href="/contact-us/" class="hover:text-accent transition-colors">Contact</a></li>
          <li><a href="/privacy-policy-3/" class="hover:text-accent transition-colors">Privacy Policy</a></li>
          <li><a href="/privacy-policy-2/" class="hover:text-accent transition-colors">Terms &amp; Conditions</a></li>
        </ul>
      </div>
    </div>
    <div class="border-t border-rule text-center py-4 font-mono text-xs text-muted">
      © <span id="js-year"></span> ScholarFactCheck.com · Not affiliated with any thinker or organization
    </div>
  </footer>
'''


def scripts_html(twitter=False):
    tw = '  <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>\n' if twitter else ''
    return f'''{tw}  <script>
    const d = document.getElementById('js-date');
    if (d) d.textContent = new Date().toLocaleDateString('en-US', {{weekday:'long',year:'numeric',month:'long',day:'numeric'}});
    const y = document.getElementById('js-year');
    if (y) y.textContent = new Date().getFullYear();
    // Reveal on first intersection. threshold must be 0: a long article can never
    // have 10% of itself on a phone screen at once, so a higher threshold never fires.
    if ('IntersectionObserver' in window) {{
      const obs = new IntersectionObserver(entries => {{
        entries.forEach(e => {{ if (e.isIntersecting) {{ e.target.classList.add('visible'); obs.unobserve(e.target); }} }});
      }}, {{threshold: 0, rootMargin: '0px 0px -10% 0px'}});
      document.querySelectorAll('.fade-up').forEach(el => obs.observe(el));
    }} else {{
      document.querySelectorAll('.fade-up').forEach(el => el.classList.add('visible'));
    }}
    // Hamburger menu toggle
    const toggle = document.getElementById('nav-toggle');
    const menu = document.getElementById('nav-menu');
    const iconOpen = document.getElementById('icon-open');
    const iconClose = document.getElementById('icon-close');
    if (toggle && menu) {{
      toggle.addEventListener('click', () => {{
        const open = menu.classList.toggle('hidden') === false;
        menu.classList.toggle('flex', open);
        iconOpen.classList.toggle('hidden', open);
        iconClose.classList.toggle('hidden', !open);
        toggle.setAttribute('aria-expanded', String(open));
      }});
    }}
  </script>
'''


def build_page(title, slug, content_html, pub_date):
    """Return a complete HTML string for one page."""
    safe_title = html.escape(title)
    desc = make_description(content_html, title)
    url = f"{SITE_URL}/{slug}/"

    try:
        dt = datetime.strptime(pub_date, "%Y-%m-%d %H:%M:%S")
        formatted_date = dt.strftime("%B %Y")
        machine_date = dt.strftime("%Y-%m-%d")
    except Exception:
        formatted_date = "2020"
        machine_date = "2020-01-01"

    body = style_body(content_html)
    twitter = 'twitter-tweet' in body

    return f'''{head_html(title, desc, url)}
<body class="font-body text-ink antialiased">

{header_html(slug)}
  <main class="max-w-5xl mx-auto px-4 sm:px-6 pb-20">

    <!-- Breadcrumb -->
    <nav class="text-xs font-mono text-muted uppercase tracking-widest pt-6 pb-4 flex gap-2 flex-wrap" aria-label="Breadcrumb">
      {get_breadcrumb(slug, title)}
    </nav>
    <hr class="rule" />

    <!-- Article header -->
    <header class="pt-8 pb-6 fade-up">
      <h1 class="font-display font-black text-4xl sm:text-5xl lg:text-6xl leading-tight text-ink mb-4">
        {safe_title}
      </h1>
      <p class="text-muted font-mono text-xs uppercase tracking-widest mb-6">
        Published <time datetime="{machine_date}">{formatted_date}</time>
      </p>
      <hr class="rule-accent" />
    </header>

    <!-- Two-column -->
    <div class="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-12 pt-6">

      <article class="fade-up prose-content min-w-0">
        {body}

        <div class="mt-10 bg-cream border border-rule rounded p-5 text-sm text-muted leading-relaxed">
          <p class="font-mono text-xs uppercase tracking-widest text-ink mb-2">Corrections Policy</p>
          Should we become aware that a thinker has changed their position, or if new evidence shows we have misconstrued their views, we will make the correction, note it here, and explain how we missed it. <a href="/errors/" class="text-accent hover:underline">Report an error →</a>
        </div>
      </article>

      <aside class="space-y-6 fade-up">
        {sidebar_html(slug)}
      </aside>

    </div>
  </main>

{footer_html()}
{scripts_html(twitter)}
</body>
</html>
'''


def build_redirect(slug, target="/"):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Redirecting… | Scholar Fact Check</title>
  <meta name="robots" content="noindex" />
  <link rel="canonical" href="{SITE_URL}{target}" />
  <meta http-equiv="refresh" content="0; url={target}" />
</head>
<body>
  <p>This page has moved to <a href="{target}">{SITE_URL}{target}</a>.</p>
</body>
</html>
'''


def recent_posts_html(pages):
    """A real list for /recent-posts/ (the WP page promised one but the module was stripped)."""
    items = sorted(pages, key=lambda p: p['date'], reverse=True)
    items = [p for p in items if p['slug'] not in UTILITY_SLUGS][:20]
    out = '<h2>Latest pages</h2>\n<ul>\n'
    for p in items:
        try:
            when = datetime.strptime(p['date'], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
        except Exception:
            when = ''
        out += f'<li><a href="/{p["slug"]}/">{html.escape(p["title"])}</a> <small>— {when}</small></li>\n'
    return out + '</ul>\n'


def main():
    tree = ET.parse(XML_FILE)
    root = tree.getroot()
    items = root.findall('.//item')
    WP = '{http://wordpress.org/export/1.2/}'
    CONTENT = '{http://purl.org/rss/1.0/modules/content/}encoded'

    pages = []
    skipped = 0
    for item in items:
        pt = item.find(WP + 'post_type'); st = item.find(WP + 'status')
        if pt is None or st is None or pt.text not in ('post', 'page') or st.text != 'publish':
            continue
        title = (item.findtext('title') or '').strip()
        slug  = (item.findtext(WP + 'post_name') or '').strip()
        date  = (item.findtext(WP + 'post_date') or '').strip()
        raw   = item.findtext(CONTENT) or ''
        if not slug or not title or slug in SKIP_SLUGS:
            skipped += 1
            continue
        title = apply_fixes(title, GLOBAL_FIXES)
        title = apply_fixes(title, PAGE_FIXES.get(slug, []))
        cleaned = clean_content(raw, slug, title)
        plain = re.sub('<[^>]+>', '', cleaned).strip()
        if len(plain) < 100:
            skipped += 1
            print(f"  SKIP (too short): {slug}")
            continue
        pages.append({'title': title, 'slug': slug, 'date': date, 'html': cleaned})

    built = 0
    for p in pages:
        content = p['html']
        if p['slug'] == 'recent-posts':
            content += '\n' + recent_posts_html(pages)
        out_dir = OUTPUT_DIR / p['slug']
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(build_page(p['title'], p['slug'], content, p['date']), encoding='utf-8')
        built += 1
        print(f"  ✓  {p['slug']}/index.html")

    # Old WordPress front page → redirect home
    out_dir = OUTPUT_DIR / 'the-scholar-fact-check'
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(build_redirect('the-scholar-fact-check', '/'), encoding='utf-8')

    print(f"\nDone — {built} pages built, {skipped} skipped.")


if __name__ == "__main__":
    main()
