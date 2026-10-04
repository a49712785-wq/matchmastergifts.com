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

def _as_pkt(dt):
    # Stored timestamps are PKT-local naive ("YYYY-MM-DDTHH:MM"); make them
    # tz-aware so arithmetic against the aware `now` doesn't raise TypeError.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PKT)
    return dt

def rel_hours(checked_at, now):
    try:
        dt = _as_pkt(datetime.fromisoformat(checked_at))
        h = max(0, int((now - dt).total_seconds() // 3600))
        return f"{h}h ago" if h else "just now"
    except (ValueError, TypeError):
        return ""

def expiry_note(posted_at, now):
    # links valid ~3 days from issue
    try:
        dt = _as_pkt(datetime.fromisoformat(posted_at))
        left = timedelta(days=3) - (now - dt)
        hrs = int(left.total_seconds() // 3600)
        if hrs <= 0:
            return ("expired", "Expired")
        if hrs < 24:
            return ("soon", f"Expires in ~{hrs}h")
        return ("ok", f"Expires in ~{hrs // 24}d {hrs % 24}h")
    except (ValueError, TypeError):
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
.intro{margin:6px 0 4px}
.intro h2{font-size:1.2rem;margin:0 0 10px}
.intro p{font-size:.95rem;color:#cbd5e1;margin-bottom:12px}
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
    ("Are Match Masters free gifts legit?",
     "The real ones are. The game maker publishes free gift links on its official Facebook and Instagram pages — every link on this page comes from those official posts. The rule is simple: legit gifts are always free and never ask for anything. Any site or video asking for your password, or telling you to download an \u201cAPK\u201d or \u201cgenerator\u201d to claim gifts, is a scam — close it and never install it."),
    ("Where can I find Match Masters free gifts on Instagram?",
     "On the game's official Instagram account, @matchmastersofficial, which posts reward links, sticker giveaways and mini-games. The catch: posts get buried fast and links expire in about 3 days. This page collects every verified link in one place each morning, so you don't have to scroll the feed."),
    ("Where can I find free links for Match Masters?",
     "Right here. We check the game's official posts every morning and publish only links that pass verification, each stamped with its check time. Bookmark this page \u2014 today's links are always at the top."),
    ("What are Match Masters rewards?",
     "Five things: coins (the main currency), boosters (your in-match power-ups), stickers (for album completion), perks (pre-match advantages), and spins (for the Lucky Spin). Every gift link on this page prints exactly which reward it gives."),
    ("Is there a promo code for Match Masters Market?",
     "Not the way most games do it \u2014 Match Masters has no promo-code box to type into. Rewards come through gift links and Masters Market reward keys instead (our free coins guide explains how keys work). Any site selling a \u201cpromo code generator\u201d is running a scam; the real rewards are the free links on this page."),
    ("What are some tricks and tips for Match Masters?",
     "Four that actually matter: charge your booster faster by matching blue-starred tiles; save Diamond and Legendary boosters for ranked matches and tournaments; pair boosters with the right perk (Extra Moves suits board-clear boosters); and claim gift links daily \u2014 free boosters and coins compound fast. Our free boosters guide breaks down every tier."),
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
</a>
<div style="text-align:right;margin:-6px 4px 12px;font-size:.75rem"><a href="/contact.html" style="color:var(--mut)">Report broken link</a></div>"""

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
<meta property="article:modified_time" content="{esc(updated)}">
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
<div class="trustbar">✓ Updated <b>{upd_str}</b> &nbsp;·&nbsp; <b>{n_live}</b> links checked &nbsp;·&nbsp; <b>{n_live}</b> live<br><span style="font-size:.78rem">🔖 Bookmark this page — new verified links land here every morning.</span></div>
<p class="method">Every link below was checked before publishing. <a href="/methodology.html">How we verify →</a></p>
<p class="method">🎁 <b>What you can get:</b> <a href="/free-coins.html">🪙 Coins</a> · <a href="/free-boosters.html">🚀 Boosters</a> · 🃏 Stickers · ✨ Perks · 🎡 Spins — each card prints its exact reward.</p>
</div>
{today_head}
<div class="links">{today_block}</div>
<div class="claim"><h3>How to claim (30 seconds)</h3><ol>{howto_html}</ol></div>
<div class="warn">⚠️ <b>Links do not work on desktop.</b> Open them on the same phone or tablet where Match Masters is installed, with your Facebook account connected to the game \u2014 otherwise you will land on a Facebook error page.</div>
<section class="intro"><h2>What are Match Masters free gifts?</h2>
<p>Match Masters free gifts are reward links the game maker publishes on its official Facebook and Instagram pages — most days. Each link gives you something free in-game: coins, boosters, stickers, perks, or spins. Tap one on the phone or tablet where Match Masters is installed and the reward lands in your account.</p>
<p>The catch: every link expires about 3 days after it is issued, and each can be claimed only once per account. That is why this page exists — we check the official posts every morning, verify each link, and publish only the ones that pass, stamped with the exact time they were checked. Dead links are removed automatically, so what you see here is always today's live batch.</p></section>
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
    inject_guides(now, days)
    build_booster_pages()



import re as _re

def inject_block(html, marker, block):
    """Replace everything between <!-- MARKER:START --> and <!-- MARKER:END --> (idempotent)."""
    start = f"<!-- {marker}:START -->"
    end = f"<!-- {marker}:END -->"
    pat = _re.compile(_re.escape(start) + r".*?" + _re.escape(end), _re.S)
    new = start + "\n" + block + "\n" + end
    return pat.sub(new, html, count=1)

def inject_guides(now, days):
    """Push today's filtered live links + fresh date into the coins/boosters pillar pages."""
    live = days[0]["links"] if days and days[0].get("links") else []
    jobs = [
        ("free-coins.html", "LIVE-COIN-LINKS",
         lambda l: "coin" in l.get("label", "").lower(), "coin"),
        ("free-boosters.html", "LIVE-BOOSTER-LINKS",
         lambda l: "booster" in l.get("label", "").lower(), "booster"),
    ]
    for fname, marker, filt, noun in jobs:
        fp = ROOT / fname
        if not fp.exists():
            continue
        html = fp.read_text()
        cards = [l for l in live if filt(l)]
        if cards:
            block = ('<div class="livewrap"><h3>\U0001f381 Today\u2019s verified free ' + noun +
                     ' links</h3><div class="links">' +
                     "\n".join(link_card(l, now) for l in cards) +
                     '</div><p class="srcnote">Checked before publishing. <a href="/methodology.html">How we verify \u2192</a></p></div>')
        else:
            block = ('<div class="livewrap"><h3>\U0001f381 Today\u2019s verified free ' + noun +
                     ' links</h3><p class="emptysm">No ' + noun +
                     ' links in today\u2019s batch — see <a href="/">today\u2019s full gift list</a>.</p></div>')
        html = inject_block(html, marker, block)
        html = inject_block(html, "GUIDE-UPDATED",
                            f"Last updated: {fmt_date(now.strftime('%Y-%m-%d'))} — links refresh every morning.")
        fp.write_text(html)
        print(f"injected {len(cards)} {noun} link(s) into {fname}")


# ---------- single-booster pages ----------

BOOSTER_CSS = """
:root{--bg:#0f172a;--card:#1e293b;--acc:#22c55e;--acc2:#16a34a;--txt:#f1f5f9;--mut:#94a3b8;--warn:#f59e0b;--gold:#fbbf24}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--txt);line-height:1.7}
.wrap{max-width:720px;margin:0 auto;padding:0 16px}
header{padding:18px 0;border-bottom:1px solid #1e293b}
.brand{font-size:1.35rem;font-weight:800;color:#fff;text-decoration:none}
.brand span{color:var(--acc)}
nav{margin-top:8px;font-size:.9rem}
nav a{color:var(--mut);text-decoration:none;margin-right:16px}
nav a:hover{color:#fff}
main{padding:28px 0}
h1{font-size:1.7rem;margin-bottom:4px;line-height:1.3}
h2{font-size:1.2rem;margin:26px 0 10px;color:#fff}
p{margin-bottom:14px;color:#cbd5e1}
p a,li a{color:var(--acc)}
.sub{color:var(--mut);font-size:.95rem;margin-bottom:14px}
.answer{background:#052e16;border:1px solid var(--acc2);border-radius:14px;padding:16px 18px;margin:16px 0;font-size:.95rem}
.answer b{color:var(--acc)}
.tierbadge{display:inline-block;background:var(--card);border:1px solid var(--gold);color:var(--gold);border-radius:999px;padding:3px 14px;font-size:.82rem;font-weight:700;margin-bottom:8px}
.src{background:var(--card);border:1px solid #334155;border-radius:14px;padding:16px 18px;margin:12px 0}
.src ul{margin:6px 0 0 20px;font-size:.93rem;color:#cbd5e1}
.src li{margin-bottom:6px}
.note{background:#451a03;border:1px solid var(--warn);border-radius:12px;padding:14px 18px;font-size:.9rem;color:#fdba74;margin:18px 0}
.xlink{background:var(--card);border:1px solid #334155;border-radius:14px;padding:18px;margin:22px 0;font-size:.95rem}
.xlink a{color:var(--acc);font-weight:700;text-decoration:none}
.sib{display:grid;gap:10px;margin-top:12px}
.sib a{background:var(--card);border:1px solid #334155;border-radius:12px;padding:12px 16px;color:#fff;text-decoration:none;display:block}
.sib a b{color:var(--acc)}
.sib a span{color:var(--mut);font-size:.85rem}
details{margin:10px 0;background:var(--card);border:1px solid #334155;border-radius:12px;padding:12px 16px}
summary{cursor:pointer;font-weight:700}
details p,details ul{margin-top:8px;font-size:.93rem;color:#cbd5e1}
details ul{margin-left:20px}
footer{border-top:1px solid #1e293b;margin-top:34px;padding:22px 0 40px;font-size:.82rem;color:var(--mut)}
footer a{color:var(--mut);margin-right:14px;text-decoration:none}
footer a:hover{color:#fff}
.disc{margin-top:12px;font-size:.76rem;color:#64748b}
"""

def _ans_html(a):
    if isinstance(a, list):
        return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in a) + "</ul>"
    return f"<p>{esc(a)}</p>"

def _ans_text(a):
    return "; ".join(a) if isinstance(a, list) else str(a)

def render_booster(b, siblings):
    faq_html = "\n".join(
        f"<details><summary>{esc(q)}</summary>{_ans_html(a)}</details>" for q, a in b["faq"])
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q,
         "acceptedAnswer": {"@type": "Answer", "text": _ans_text(a)}} for q, a in b["faq"]]}
    get_html = "\n".join(f"<li>{esc(x)}</li>" for x in b["how_to_get"])
    sib_html = "\n".join(
        f'<a href="/{s["slug"]}.html"><b>{esc(s["name"])}</b><br><span>{s["tier_emoji"]} {esc(s["tier"])} booster guide</span></a>'
        for s in siblings)
    stages_note = ""
    if b["tier"] == "Diamond":
        stages_note = ('<div class="note">💎 <b>Diamond boosters have 3 upgrade stages.</b> '
                       "Collect duplicate cards from events, spins and album rewards — Stage 3 is "
                       "dramatically stronger than Stage 1.</div>")
    title = f'{b["name"]} in Match Masters (2026): What It Does, Best Mode & How to Get It Free'
    desc = (f'{b["name"]} is a {b["tier"]} booster in Match Masters. '
            "What it does, the best game mode for it, how to get it free, and the best perk combo — explained.")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}/{b['slug']}.html">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{SITE}/{b['slug']}.html">
<style>{BOOSTER_CSS}</style>
<script type="application/ld+json">{json.dumps(faq_ld)}</script>
</head>
<body>
<header><div class="wrap">
<a class="brand" href="/">Match Master <span>Gifts</span></a>
<nav><a href="/">Today's Gifts</a><a href="/free-boosters.html">All Boosters</a><a href="/how-to-redeem.html">How to Redeem</a></nav>
</div></header>
<main><div class="wrap">
<span class="tierbadge">{b['tier_emoji']} {esc(b['tier'])} booster</span>
<h1>{esc(b['name'])}</h1>
<p class="sub">Match Masters booster guide — what it does, where it shines, and how to get it free.</p>
<div class="answer"><b>Quick answer:</b> {esc(b['ability'])} Unlock: {esc(b['unlock'])}. Details, free sources and the best perk combo below.</div>
<h2>What {esc(b['name'])} does</h2>
<p>{esc(b['ability'])}</p>
{stages_note}
<h2>Best game mode for {esc(b['name'])}</h2>
<p>{esc(b['best_modes'])}</p>
<h2>How to get {esc(b['name'])} free</h2>
<div class="src"><ul>{get_html}</ul></div>
<p>Also check <a href="/">today's verified gift links</a> every morning — booster drops land there whenever the game publishes them.</p>
<h2>Best perk combo</h2>
<p>{b['perk_combo']}</p>
<h2>{esc(b['name'])} — FAQ</h2>
{faq_html}
<div class="xlink">🚀 <a href="/free-boosters.html">All booster tiers explained</a> · 🪙 <a href="/free-coins.html">Free coins guide</a> · 🎁 <a href="/">Today's gifts</a></div>
<h2>Other popular boosters</h2>
<div class="sib">{sib_html}</div>
</div></main>
<footer><div class="wrap">
<a href="/about.html">About</a><a href="/methodology.html">How We Verify</a><a href="/contact.html">Contact</a><a href="/privacy.html">Privacy</a>
<p class="disc">{BRAND} is an independent fan site. Not affiliated with Candivore or Match Masters. Booster details follow the game's own descriptions and player guides.</p>
<p class="disc">© 2026 {BRAND}</p>
</div></footer>
</body>
</html>"""

def build_booster_pages():
    """Render one HTML page per booster in data/boosters.json, then refresh the sitemap."""
    data = json.loads((ROOT / "data" / "boosters.json").read_text())
    boosters = data["boosters"]
    for b in boosters:
        sibs = [s for s in boosters if s["slug"] != b["slug"]]
        (ROOT / f'{b["slug"]}.html').write_text(render_booster(b, sibs))
        print(f"built booster page {b['slug']}.html")
    build_sitemap([b["slug"] for b in boosters])

def build_sitemap(booster_slugs):
    static = [
        ("/", "daily", "1.0"),
        ("/how-to-redeem.html", "monthly", "0.8"),
        ("/free-boosters.html", "monthly", "0.8"),
        ("/free-coins.html", "monthly", "0.8"),
        ("/methodology.html", "monthly", "0.6"),
        ("/about.html", "yearly", "0.4"),
        ("/contact.html", "yearly", "0.3"),
        ("/privacy.html", "yearly", "0.3"),
    ]
    urls = "".join(
        f'  <url><loc>{SITE}{p}</loc><changefreq>{f}</changefreq><priority>{pr}</priority></url>\n'
        for p, f, pr in static)
    for s in booster_slugs:
        urls += (f'  <url><loc>{SITE}/{s}.html</loc>'
                 "<changefreq>monthly</changefreq><priority>0.7</priority></url>\n")
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")
    print(f"sitemap.xml written ({len(static) + len(booster_slugs)} urls)")


if __name__ == "__main__":
    build()
