#!/usr/bin/env python3
"""Sync FAQPage JSON-LD with the visible <details> FAQs on static pages.

Usage: python3 scripts/sync_faq_schema.py [page.html ...]
If no pages given, processes all known static FAQ pages (not build.py-generated ones).

The visible FAQ is the single source of truth; the JSON-LD is regenerated from it.
Run this after hand-editing any visible FAQ text.
"""
import json
import re
import html as htmlmod
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAGES = ["free-coins/index.html", "free-boosters/index.html", "how-to-redeem/index.html"]

LD_RE = re.compile(
    r'<script type="application/ld\+json">\{"@context":"https://schema\.org","@type":"FAQPage".*?</script>',
    re.S,
)
DETAILS_RE = re.compile(r"<details><summary>(.*?)</summary>(.*?)</details>", re.S)


def clean_text(html_frag):
    text = re.sub(r"<[^>]+>", "", html_frag)
    text = htmlmod.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def sync_page(path):
    t = path.read_text()
    faqs = DETAILS_RE.findall(t)
    if not faqs:
        print(f"{path.name}: no <details> FAQs found — skipped")
        return False
    main_entity = []
    for q_html, a_html in faqs:
        q = clean_text(q_html)
        a = clean_text(a_html)
        if not q or not a:
            continue
        main_entity.append(
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
        )
    ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": main_entity,
    }
    new_tag = f'<script type="application/ld+json">{json.dumps(ld)}</script>'
    if LD_RE.search(t):
        t = LD_RE.sub(lambda m: new_tag, t, count=1)
        action = "replaced"
    else:
        # insert before </head> if no FAQPage block exists
        t = t.replace("</head>", new_tag + "\n</head>", 1)
        action = "inserted"
    path.write_text(t)
    print(f"{path.name}: {action} FAQPage JSON-LD ({len(main_entity)} questions)")
    return True


if __name__ == "__main__":
    pages = sys.argv[1:] or DEFAULT_PAGES
    for p in pages:
        sync_page(ROOT / p)
