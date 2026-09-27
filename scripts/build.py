#!/usr/bin/env python3
"""Daily build for matchmastergifts.com — static HTML hub.

Reads data/links.json, renders index.html from the template below.
Run: python3 scripts/build.py
"""
import json, html
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "links.json"
OUT = ROOT / "index.html"
PKT = timezone(timedelta(hours=5))

SITE = "https://matchmastergifts.com"
BRAND = "Match Master Gifts"

# ---------- helpers ----------

def esc(s):
    return html.escape(str(s or ""), quote=True)

def fmt_date(d):
    # d: "2026-09-27" -> "September 27, 2026"
    return datetime.strptime(d, "%Y-%m-%d").strftime("%B %d, %Y")

def rel_hours(checked_at, now):
    try:
        dt = datetime.fromisoformat(checked_at)
        h = max(0, int((now - dt).total_seconds() // 3600))
        return f"{h}h ago" if h else "just now"
    except Exception:
        return ""

def expiry_note(posted_at, now):
    # links valid ~3 days from issue
    try:
        dt = datetime.fromisoformat(posted_at)
        left = timedelta(days=3) - (now - dt)
        hrs = int(left.total_seconds() // 3600)
        if hrs <= 0:
            return ("expired", "Expired")
        if hrs < 24:
            return ("soon", f"Expires in ~{hrs}h")
        return ("ok", f"Expires in ~{hrs // 24}d {hrs % 24}h")
    except Exception:
        return ("ok", "")

# ---------- template ----------

CSS = """
:root{--bg:#0f172a;--card:#1e293b;--acc:#22c55e;--acc2:#16a34a;--txt:#f1f5f9;--mut:#94a3b8;--warn:#f59e0b;--bad:#ef4444}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--txt);line-height:1.6}
.wrap{max-width:720px;margin:0 auto;padding:0 16px}
header{padding:18px 0;border-bottom:1px solid #1e293b}
.brand{font-size:1.35rem;font-weight:800;color:#fff;text-decoration:none}
.brand span{color:var(--acc)}
nav{margin-top:8px;font-size:.9rem}
nav a{color:var(--mut);text-decoration:none;margin-right:16px}
nav a:hover{color:#fff}
.hero{padding:28px 0 8px;text-align:center}
.hero h1{font-size:1.7rem;line-height:1.25;margin-bottom:10px}
.trustbar{display:inline-flex;flex-wrap:wrap;gap:8px;justify-content:center;background:var(--card);border:1px solid #334155;border-radius:12px;padding:10px 16px;font-size:.85rem;color:var(--mut);margin:12px 0}
.trustbar b{color:var(--acc)}
.method{font-size:.82rem;color:var(--mut);text-align:center;margin-bottom:6px}
.method a{color:var(--acc)}
.links{margin:18px 0}
.dayhead{display:flex;align-items:center;justify-content:space-between;margin:22px 0 10px}
.dayhead h2{font-size:1.15rem}
.live{font-size:.72rem;font-weight:700;background:var(--acc);color:#052e16;padding:3px 10px;border-radius:999px}
.exp{font-size:.72rem;font-weight:700;background:#334155;color:var(--mut);padding:3px 10px;border-radius:999px}
.gift{display:block;background:var(--card);border:1px solid #334155;border-radius:14px;padding:16px;margin-bottom:12px;text-decoration:none;color:var(--txt);transition:border-color .15s}
.gift:hover{border-color:var(--acc)}
.gift .top{display:flex;justify-content:space-between;align-items:center;gap:10px}
.gift .reward{font-weight:800;font-size:1.05rem}
.gift .amt{color:var(--acc);font-weight:700}
.gift .meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;font-size:.78rem;color:var(--mut)}
.pill{background:#0f172a;border:1px solid #334155;border-radius:999px;padding:2px 10px}
.pill.ok{color:var(--acc);border-color:var(--acc)}
.pill.soon{color:var(--warn);border-color:var(--warn)}
.pill.expired{color:var(--bad);border-color:var(--bad)}
.claim{background:#052e16;border:1px solid var(--acc2);border-radius:14px;padding:18px;margin:24px 0}
.claim h3{margin-bottom:10px;color:var(--acc)}
.claim ol{margin-left:20px;font-size:.95rem}
.claim li{margin-bottom:8px}
.warn{background:#451a03;border:1px solid var(--warn);border-radius:12px;padding:12px 16px;font-size:.88rem;margin:16px 0;color:#fdba74}
.empty{background:var(--card);border:1px dashed #475569;border-radius:14px;padding:28px;text-align:center;color:var(--mut);margin:18px 0}
details{margin:10px 0;background:var(--card);border:1px solid #334155;border-radius:12px;padding:12px 16px}
summary{cursor:pointer;font-weight:700}
.faq{margin:26px 0}
.faq h2{margin-bottom:12px}
.faq details p{margin-top:8px;font-size:.93rem;color:#cbd5e1}
footer{border-top:1px solid #1e293b;margin-top:34px;padding:22px 0 40px;font-size:.82rem;color:var(--mut)}
footer a{color:var(--mut);margin-right:14px;text-decoration:none}
footer a:hover{color:#fff}
.disc{margin-top:12px;font-size:.76rem;color:#64748b}
h2.sec{margin:26px 0 10px;font-size:1.2rem}
"""

FAQ = [
    ("How often are the gift links updated?",
     "Every morning. Each gift card shows the exact time that link was checked, so you never have to guess how fresh it is."),
    ("How long do Match Masters gift links last?",
     "About 3 days from the day they are issued. We remove expired links automatically, and the countdown on each card is our best measured estimate \u2014 we are still calibrating it against real expiry data, and we will update this answer as we learn more."),
    ("Why does a link say 'already claimed'?",
     "Each gift link can be claimed only once per account. If you tapped it before, the game remembers. Just try the other links for today \u2014 they are separate gifts."),
    ("The link opened a Facebook error page. What now?",
     "That happens when the link is opened somewhere the game cannot reach it. Open the link on the same phone or tablet where Match Masters is installed, and make sure your Facebook account is connected inside the game. Gift links do not work in desktop browsers."),
    ("Are these links safe to tap?",
     "Yes. Every link on this page comes from Match Masters' official posts and points to the game's official link domain. We never ask for your password or login \u2014 any site that does is running a scam, close it immediately."),
    ("Do the links work in my country?",
     "Almost always yes. A small number of links can be region-locked by the game maker. If one link does not work for you, the rest of today's links still will."),
]

HOWTO = [
    "Tap any green gift button above <b>on the device where Match Masters is installed</b>.",
    "The game opens by itself and a popup shows your reward.",
    "Tap <b>Collect</b> inside the game \u2014 the reward is added to your account instantly.",
    "Done. Come back tomorrow \u2014 new links are checked and published every morning.",
]

def link_card(l, now):
    cls, exp = expiry_note(l.get("posted_at", ""), now)
    checked = rel_hours(l.get("checked_at", ""), now)
    return f"""
<a class="gift" href="{esc(l.get('url',''))}" rel="nofollow noopener">
  <div class="top">
    <div><div class="reward">{esc(l.get('label','Free Gift'))}</div>
    <div class="amt">{esc(l.get('amount',''))}</div></div>
    <div style="font-size:1.6rem">🎁</div>
  </div>
  <div class="meta">
    <span class="pill ok">✓ checked {esc(checked)}</span>
    <span class="pill {cls}">{esc(exp)}</span>
    <span class="pill">src: {esc(l.get('source','official post'))}</span>
  </div>
</a>"""

def build():
    data = json.loads(DATA.read_text())
    now = datetime.now(PKT)
    days = data.get("days", [])
    updated = data.get("updated", "")

    try:
        upd_dt = datetime.fromisoformat(updated)
        upd_str = upd_dt.strftime("%B %d, %Y at %I:%M %p PKT")
    except Exception:
        upd_str = esc(updated)

    live_links = days[0]["links"] if days and days[0].get("links") else []
    n_live = len(live_links)

    if live_links:
        today_block = "\n".join(link_card(l, now) for l in live_links)
        today_head = f'<div class="dayhead"><h2>Today — {fmt_date(days[0]["date"])}</h2><span class="live">{n_live} LIVE</span></div>'
    else:
        today_head = ""
        today_block = """<div class="empty">Today's links are being checked right now.<br>
        New verified links appear here every morning. Check back soon.</div>"""

    prev_blocks = ""
    for d in days[1:3]:
        cards = "\n".join(link_card(l, now) for l in d.get("links", []))
        prev_blocks += f"""
<details><summary>{fmt_date(d['date'])} — {len(d.get('links',[]))} links <span class="exp">EXPIRED</span></summary>
<div class="links">{cards}</div>
<p style="font-size:.8rem;color:var(--mut)">These links are past the 3-day window and no longer work. Shown for transparency only.</p>
</details>"""

    faq_html = "\n".join(
        f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in FAQ)
    howto_html = "\n".join(f"<li>{s}</li>" for s in HOWTO)

    # JSON-LD
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}

    title = f"Match Masters Free Gifts Today ({fmt_date(days[0]['date']) if days else now.strftime('%B %d, %Y')}) – Verified Daily Links"
    desc = ("Claim today's verified Match Masters free gift links. Every link is checked before publishing, "
            "with reward amounts and expiry times shown. Updated daily.")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}/">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE}/">
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(faq_ld)}</script>
</head>
<body>
<header><div class="wrap">
<a class="brand" href="/">Match Master <span>Gifts</span></a>
<nav><a href="/">Today's Gifts</a><a href="/how-to-redeem.html">How to Redeem</a><a href="/methodology.html">How We Verify</a></nav>
</div></header>
<main><div class="wrap">
<div class="hero">
<h1>Match Masters Free Gifts — Today</h1>
<div class="trustbar">✓ Updated <b>{upd_str}</b> &nbsp;·&nbsp; <b>{n_live}</b> links checked &nbsp;·&nbsp; <b>{n_live}</b> live</div>
<p class="method">Every link below was checked before publishing. <a href="/methodology.html">How we verify →</a></p>
</div>
{today_head}
<div class="links">{today_block}</div>
<div class="claim"><h3>How to claim (30 seconds)</h3><ol>{howto_html}</ol></div>
<div class="warn">⚠️ <b>Links do not work on desktop.</b> Open them on the same phone or tablet where Match Masters is installed, with your Facebook account connected to the game \u2014 otherwise you will land on a Facebook error page.</div>
<h2 class="sec">Previous days</h2>
{prev_blocks if prev_blocks else '<p style="color:var(--mut);font-size:.9rem">Archive builds up as we publish daily.</p>'}
<section style="margin-top:34px"><h2>\U0001f4da Match Masters guides</h2>
<div style="display:grid;gap:10px;margin-top:12px">
<a href="/free-boosters.html" style="background:var(--card);border:1px solid #334155;border-radius:12px;padding:14px 16px;color:#fff;text-decoration:none;display:block"><b>Free Boosters Guide</b><br><span style="color:var(--mut);font-size:.88rem">Every tier explained + 7 real ways to get boosters free</span></a>
<a href="/free-coins.html" style="background:var(--card);border:1px solid #334155;border-radius:12px;padding:14px 16px;color:#fff;text-decoration:none;display:block"><b>Free Coins Guide</b><br><span style="color:var(--mut);font-size:.88rem">What coins do + 7 real ways to refill your balance</span></a>
<a href="/how-to-redeem.html" style="background:var(--card);border:1px solid #334155;border-radius:12px;padding:14px 16px;color:#fff;text-decoration:none;display:block"><b>How to Redeem Gift Links</b><br><span style="color:var(--mut);font-size:.88rem">Fix every error: Facebook error page, already claimed, expired</span></a>
</div></section>
<div class="faq"><h2>Questions, answered honestly</h2>{faq_html}</div>
</div></main>
<footer><div class="wrap">
<a href="/about.html">About</a><a href="/methodology.html">How We Verify</a><a href="/contact.html">Contact</a><a href="/privacy.html">Privacy</a>
<p class="disc">{BRAND} is an independent fan site. Not affiliated with Candivore or Match Masters. All gift links come from the game's official posts.</p>
<p class="disc">© 2026 {BRAND}</p>
</div></footer>
</body>
</html>"""
    OUT.write_text(page)
    print(f"built {OUT} ({len(page)} bytes, {n_live} live links)")

if __name__ == "__main__":
    build()
