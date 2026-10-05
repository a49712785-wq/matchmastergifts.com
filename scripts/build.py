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

ORG_LD = {"@context": "https://schema.org", "@type": "Organization",
          "name": "Match Master Gifts", "url": "https://matchmastergifts.com/",
          "logo": "https://matchmastergifts.com/og-image.jpg",
          "description": "Independent fan site publishing verified daily Match Masters free gift links.", "sameAs": ["https://www.facebook.com/matchmastergiftslinks/"]}

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
     "The real ones are. The game maker publishes free gift links on its official Facebook page and WhatsApp channel — every link on this page comes from those official posts. The rule is simple: legit gifts are always free and never ask for anything. Any site or video asking for your password, or telling you to download an \u201cAPK\u201d or \u201cgenerator\u201d to claim gifts, is a scam — close it and never install it."),
    ("Where can I find Match Masters free gifts on Instagram?",
     "On the game's official Instagram account, @matchmastersofficial — with one big caveat: its posts are comment-to-enter giveaways and mini-games, not tap-to-claim gift links. We audited 3 weeks of posts and found zero claim links in captions. Occasionally a reward key is hidden inside a post image instead. For actual tap-to-claim links, this page collects every verified one each morning, so you don't have to scroll the feed."),
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
<div style="text-align:right;margin:-6px 4px 12px;font-size:.75rem"><a href="/contact/" style="color:var(--mut)">Report broken link</a></div>"""

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
        bucket_date = days[0]["date"]
        today_str = now.strftime("%Y-%m-%d")
        # Honest label: the bucket is "Today" only when it actually is today.
        day_label = (f"Today — {fmt_date(bucket_date)}" if bucket_date == today_str
                     else f"Still live from {fmt_date(bucket_date)}")
        today_head = f'<div class="dayhead"><h2>{day_label}</h2><span class="live">{n_live} LIVE</span></div>'
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

    title = f"Match Masters Free Gifts Today ({now.strftime('%b %-d')}) \u2013 Verified Links"
    desc = ("Claim today's verified Match Masters free gift links. Every link is checked before publishing, "
            "with reward amounts and expiry times shown. Updated daily.")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="google-site-verification" content="FK_vAqjuZiMsAg4k-HZhlg8cA7oLIqLxHg3rjVCd0aY" />
<meta name="google-site-verification" content="HXi2yIZGtRJ27YzPeDHc6Bw_To29TXPDb-qgVdodTbA" />
<link rel="canonical" href="{SITE}/">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE}/">
<meta property="og:image" content="{SITE}/og-image.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{SITE}/og-image.jpg">
<meta property="article:modified_time" content="{esc(updated)}">
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(faq_ld)}</script>
<script type="application/ld+json">{json.dumps(ORG_LD)}</script>
</head>
<body>
<header><div class="wrap">
<a class="brand" href="/">Match Master <span>Gifts</span></a>
<nav><a href="/">Today's Gifts</a><a href="/how-to-redeem/">How to Redeem</a><a href="/methodology/">How We Verify</a></nav>
</div></header>
<main><div class="wrap">
<div class="hero">
<h1>Match Masters Free Gifts — Today</h1>
<div class="trustbar">✓ Updated <b>{upd_str}</b> &nbsp;·&nbsp; <b>{n_live}</b> links checked &nbsp;·&nbsp; <b>{n_live}</b> live<br><span style="font-size:.78rem">🔖 Bookmark this page — new verified links land here every morning.</span></div>
<p class="method">Every link below was checked before publishing. <a href="/methodology/">How we verify →</a></p>
<p class="method">🎁 <b>What you can get:</b> <a href="/free-coins/">🪙 Coins</a> · <a href="/free-boosters/">🚀 Boosters</a> · 🃏 Stickers · ✨ Perks · 🎡 Spins — each card prints its exact reward. · 🔑 <a href="/reward-keys/">Reward keys (typed codes)</a></p>
</div>
{today_head}
<div class="links">{today_block}</div>
<div class="claim"><h3>How to claim (30 seconds)</h3><ol>{howto_html}</ol></div>
<div class="warn">⚠️ <b>Links do not work on desktop.</b> Open them on the same phone or tablet where Match Masters is installed, with your Facebook account connected to the game \u2014 otherwise you will land on a Facebook error page.</div>
<section class="intro"><h2>What are Match Masters free gifts?</h2>
<p>Match Masters free gifts are reward links the game maker publishes on its official Facebook page and WhatsApp channel — most days. Each link gives you something free in-game: coins, boosters, stickers, perks, or spins. Tap one on the phone or tablet where Match Masters is installed and the reward lands in your account.</p>
<p>The catch: every link expires about 3 days after it is issued, and each can be claimed only once per account. That is why this page exists — we check the official posts every morning, verify each link, and publish only the ones that pass, stamped with the exact time they were checked. Dead links are removed automatically, so what you see here is always today's live batch.</p></section>
<h2 class="sec">Previous days</h2>
{prev_blocks if prev_blocks else '<p style="color:var(--mut);font-size:.9rem">Archive builds up as we publish daily.</p>'}
<section style="margin-top:34px"><h2>\U0001f4da Match Masters guides</h2>
<div style="display:grid;gap:10px;margin-top:12px">
<a href="/free-boosters/" style="background:var(--card);border:1px solid #334155;border-radius:12px;padding:14px 16px;color:#fff;text-decoration:none;display:block"><b>Free Boosters Guide</b><br><span style="color:var(--mut);font-size:.88rem">Every tier explained + 7 real ways to get boosters free</span></a>
<a href="/free-coins/" style="background:var(--card);border:1px solid #334155;border-radius:12px;padding:14px 16px;color:#fff;text-decoration:none;display:block"><b>Free Coins Guide</b><br><span style="color:var(--mut);font-size:.88rem">What coins do + 7 real ways to refill your balance</span></a>
<a href="/how-to-redeem/" style="background:var(--card);border:1px solid #334155;border-radius:12px;padding:14px 16px;color:#fff;text-decoration:none;display:block"><b>How to Redeem Gift Links</b><br><span style="color:var(--mut);font-size:.88rem">Fix every error: Facebook error page, already claimed, expired</span></a>
</div></section>
<div class="faq"><h2>Questions, answered honestly</h2>{faq_html}</div>
</div></main>
<footer><div class="wrap">
<a href="/about/">About</a><a href="/methodology/">How We Verify</a><a href="/contact/">Contact</a><a href="/privacy/">Privacy</a><a href="https://www.facebook.com/matchmastergiftslinks/" target="_blank" rel="noopener">Facebook</a>
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
    def is_coin(l):
        return "coin" in l.get("label", "").lower()
    def is_booster(l):
        return "booster" in l.get("label", "").lower()
    def unclassified(l):
        # Links whose label matches neither pillar (e.g. "Social Solo Event")
        # must still surface — they ride along on both pillars as a mixed batch.
        return not is_coin(l) and not is_booster(l)
    jobs = [
        ("free-coins/index.html", "LIVE-COIN-LINKS",
         lambda l: is_coin(l) or unclassified(l), "coin"),
        ("free-boosters/index.html", "LIVE-BOOSTER-LINKS",
         lambda l: is_booster(l) or unclassified(l), "booster"),
    ]
    for fname, marker, filt, noun in jobs:
        fp = ROOT / fname
        if not fp.exists():
            continue
        html = fp.read_text()
        cards = [l for l in live if filt(l)]
        all_mixed = bool(cards) and all(unclassified(l) for l in cards)
        if cards:
            heading = ("\U0001f381 Today\u2019s verified free gift links"
                       if all_mixed else
                       "\U0001f381 Today\u2019s verified free " + noun + " links")
            block = ('<div class="livewrap"><h3>' + heading +
                     '</h3><div class="links">' +
                     "\n".join(link_card(l, now) for l in cards) +
                     '</div><p class="srcnote">Checked before publishing. <a href="/methodology/">How we verify \u2192</a></p></div>')
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
        f'<a href="/{s["slug"]}/"><b>{esc(s["name"])}</b><br><span>{s["tier_emoji"]} {esc(s["tier"])} booster guide</span></a>'
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
<link rel="canonical" href="{SITE}/{b['slug']}/">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{SITE}/{b['slug']}/">
<meta property="og:image" content="{SITE}/og-image.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{SITE}/og-image.jpg">
<style>{BOOSTER_CSS}</style>
<script type="application/ld+json">{json.dumps(faq_ld)}</script>
<script type="application/ld+json">{json.dumps(ORG_LD)}</script>
</head>
<body>
<header><div class="wrap">
<a class="brand" href="/">Match Master <span>Gifts</span></a>
<nav><a href="/">Today's Gifts</a><a href="/free-boosters/">All Boosters</a><a href="/how-to-redeem/">How to Redeem</a></nav>
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
<div class="xlink">🚀 <a href="/free-boosters/">All booster tiers explained</a> · 🪙 <a href="/free-coins/">Free coins guide</a> · 🎁 <a href="/">Today's gifts</a></div>
<h2>Other popular boosters</h2>
<div class="sib">{sib_html}</div>
</div></main>
<footer><div class="wrap">
<a href="/about/">About</a><a href="/methodology/">How We Verify</a><a href="/contact/">Contact</a><a href="/privacy/">Privacy</a><a href="https://www.facebook.com/matchmastergiftslinks/" target="_blank" rel="noopener">Facebook</a>
<p class="disc">{BRAND} is an independent fan site. Not affiliated with Candivore or Match Masters. Booster details follow the game's own descriptions and player guides.</p>
<p class="disc">© 2026 {BRAND}</p>
</div></footer>
</body>
</html>"""

# ---------- reward keys page ----------

KEYS_FAQ = [
    ("What is a Match Masters reward key?",
     "A short text code — usually a word plus digits, like the ones the game drops on social posts and livestreams — that you type into the Reward Keys section of the official Match Masters web hub. Each key gives you an in-game reward: coins, boosters, stickers, or perks."),
    ("Where do I enter a reward key?",
     "On the official Match Masters web hub (matchmasters.com). Open the hub, tap the 'Reward Keys' card, sign in with the QR code shown in your game app (no password needed), paste the key exactly as shown, and hit redeem. The reward lands in your game account."),
    ("How are reward keys different from gift links?",
     "Gift links are tap-to-claim URLs: you tap them on your phone and the game opens with your reward. Reward keys are typed codes: you copy the code and paste it into the Masters Market hub yourself. Same idea — free rewards — different mechanism. Promo codes are a third thing entirely: checkout discounts, not game rewards."),
    ("Why isn't my key working?",
     "Three usual reasons: the key already expired (livestream keys can die within hours), the key was already redeemed on your account (one use per account), or a typo — keys are case-sensitive, so copy-paste instead of retyping. If none of those fit, the key may have hit its redemption cap."),
    ("How long do reward keys last?",
     "It varies a lot. Keys from livestreams often expire within hours or when the redemption cap fills. Keys from social posts usually last a few days. We stamp every key with when we spotted it so you can judge freshness yourself."),
    ("Can I use a key more than once?",
     "No — one redemption per account, same as gift links. If it says already used, that account already claimed it."),
    ("Where do new reward keys come from?",
     "The game's official Facebook and Instagram posts (sometimes hidden in the post image), livestreams, the official Discord server, and the WhatsApp channel. We watch all of them and publish verified keys here."),
    ("Are Match Masters code generators real?",
     "No — every single one is a scam. Real keys are short words dropped on official channels. Any site promising 'unlimited keys', asking for your password, or making you complete surveys to 'unlock' a code is trying to steal your account or install malware. Only redeem keys through the game app or the official Market hub."),
    ("Do reward keys work in my country?",
     "Almost always yes. Like gift links, a small number can be region-locked by the game maker, but most keys work everywhere."),
    ("Why are there no keys listed right now?",
     "Because we only publish keys we've actually seen on official channels — and keys don't drop every day. An empty list means no verified live key exists at this moment, not that we're hiding any. Check back; the page updates whenever a new key is spotted."),
]

KEYS_CSS = """
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
.keycard{background:var(--card);border:1px solid var(--acc2);border-radius:14px;padding:18px;margin-bottom:14px}
.keycard .code{font-family:ui-monospace,monospace;font-size:1.5rem;font-weight:800;letter-spacing:2px;color:var(--acc);background:#0f172a;border:1px dashed var(--acc2);border-radius:10px;padding:10px 16px;display:inline-block;margin:8px 0;cursor:pointer}
.keycard .meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;font-size:.78rem;color:var(--mut)}
.pill{background:#0f172a;border:1px solid #334155;border-radius:999px;padding:2px 10px}
.pill.ok{color:var(--acc);border-color:var(--acc)}
.empty{background:var(--card);border:1px dashed #475569;border-radius:14px;padding:28px;text-align:center;color:var(--mut);margin:18px 0}
.steps{background:var(--card);border:1px solid #334155;border-radius:14px;padding:18px;margin:16px 0}
.steps ol{margin-left:20px}
.steps li{margin-bottom:10px;color:#cbd5e1}
.vs{display:grid;gap:10px;margin:14px 0}
.vs div{background:var(--card);border:1px solid #334155;border-radius:12px;padding:14px 16px}
.vs b{color:var(--acc)}
.warn{background:#451a03;border:1px solid var(--warn);border-radius:12px;padding:14px 18px;font-size:.9rem;color:#fdba74;margin:18px 0}
details{margin:10px 0;background:var(--card);border:1px solid #334155;border-radius:12px;padding:12px 16px}
summary{cursor:pointer;font-weight:700}
details p{margin-top:8px;font-size:.93rem;color:#cbd5e1}
footer{border-top:1px solid #1e293b;margin-top:34px;padding:22px 0 40px;font-size:.82rem;color:var(--mut)}
footer a{color:var(--mut);margin-right:14px;text-decoration:none}
footer a:hover{color:#fff}
.disc{margin-top:12px;font-size:.76rem;color:#64748b}
"""

def key_card(k, now):
    spotted = rel_hours(k.get("spotted_at", ""), now)
    try:
        posted = fmt_date(datetime.fromisoformat(k["posted_at"]).strftime("%Y-%m-%d"))
    except (ValueError, TypeError, KeyError):
        posted = ""
    return f"""
<div class="keycard">
  <div style="font-weight:800">🎁 {esc(k.get('reward') or 'Mystery reward')}</div>
  <div class="code" onclick="navigator.clipboard.writeText(this.innerText);this.style.borderColor='#22c55e'" title="Tap to copy">{esc(k.get('key',''))}</div>
  <div style="font-size:.82rem;color:var(--mut)">Tap the code to copy it, then paste it in the hub's Reward Keys section.</div>
  <div class="meta">
    <span class="pill ok">✓ spotted {esc(spotted)} on {esc(k.get('source','official post'))}</span>
    {f"<span class='pill'>posted {esc(posted)}</span>" if posted else ""}
    {f"<span class='pill'>{esc(k.get('notes',''))}</span>" if k.get('notes') else ""}
  </div>
</div>"""

def build_keys_page():
    """Render reward-keys/index.html from data/keys.json."""
    data = json.loads((ROOT / "data" / "keys.json").read_text())
    now = datetime.now(PKT)
    keys = [k for k in data.get("keys", []) if k.get("status") == "active"]
    expired = [k for k in data.get("keys", []) if k.get("status") != "active"]

    if keys:
        cards = "\n".join(key_card(k, now) for k in keys)
        live_block = f'<div class="dayhead"><h2>Working keys right now</h2><span class="live">{len(keys)} LIVE</span></div>\n{cards}'
    else:
        live_block = """<div class="empty"><b>No verified active keys right now.</b><br>
        We only publish keys we've actually seen on official channels — and keys don't drop every day.
        This page updates the moment a new key is spotted. Meanwhile, <a href="/">today's gift links</a> are live.</div>"""

    exp_block = ""
    if expired:
        items = "".join(f"<li><code>{esc(k.get('key',''))}</code> — {esc(k.get('reward',''))} <span style='color:var(--mut)'>(expired)</span></li>" for k in expired[:10])
        exp_block = f"<h2>Recently expired</h2><ul style='margin-left:20px;color:#cbd5e1'>{items}</ul><p style='font-size:.85rem;color:var(--mut)'>Don't try these — they're shown so you know we tracked them.</p>"

    faq_html = "\n".join(
        f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in KEYS_FAQ)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in KEYS_FAQ]}

    try:
        upd_dt = datetime.fromisoformat(data.get("updated", ""))
        upd_str = upd_dt.strftime("%B %d, %Y at %I:%M %p PKT")
    except Exception:
        upd_str = esc(data.get("updated", ""))

    title = f"Match Masters Reward Keys ({now.strftime('%B %Y')}) – Working Codes"
    desc = ("Working Match Masters reward keys and codes. Every key verified on official channels, "
            "with redemption steps for the Masters Market hub. Updated whenever new keys drop.")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}/reward-keys/">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{SITE}/reward-keys/">
<meta property="og:image" content="{SITE}/og-image.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{SITE}/og-image.jpg">
<style>{KEYS_CSS}</style>
<script type="application/ld+json">{json.dumps(faq_ld)}</script>
<script type="application/ld+json">{json.dumps(ORG_LD)}</script>
</head>
<body>
<header><div class="wrap">
<a class="brand" href="/">Match Master <span>Gifts</span></a>
<nav><a href="/">Today's Gifts</a><a href="/reward-keys/">Reward Keys</a><a href="/how-to-redeem/">How to Redeem</a></nav>
</div></header>
<main><div class="wrap">
<h1>Match Masters Reward Keys</h1>
<p class="sub">Working codes, verified on official channels — updated whenever new keys drop. Last check: {upd_str}.</p>
{live_block}
<h2>How to redeem a reward key (2 minutes)</h2>
<div class="steps"><ol>
<li>Open the official Match Masters web hub at <b>matchmasters.com</b> on your phone or computer.</li>
<li>Tap the <b>"Reward Keys"</b> card on the hub homepage.</li>
<li>Sign in with the <b>QR code</b>: the hub shows a code, you enter the 4-digit number shown in your game app. No password needed — and never enter your password anywhere else.</li>
<li><b>Paste the key exactly</b> as shown (keys are case-sensitive — copy, don't retype) and hit redeem.</li>
<li>Open the game — your reward is waiting in your account.</li>
</ol></div>
<h2>Reward keys vs gift links vs promo codes</h2>
<div class="vs">
<div><b>🎁 Gift links</b> — tap-to-claim URLs. Tap on your phone, the game opens, reward lands. New ones <a href="/">every morning here</a>.</div>
<div><b>🔑 Reward keys</b> — typed codes. Copy the code, paste it into the hub's Reward Keys section yourself. Drop irregularly — livestreams, social posts, events.</div>
<div><b>🏷️ Promo codes</b> — checkout discounts for purchases. A different thing entirely; not game rewards.</div>
</div>
<h2>Where new keys come from</h2>
<p>The game's official Facebook and Instagram posts (sometimes the key is hidden inside the post image), livestreams, the official Discord server, and the WhatsApp channel. Livestream keys are the fastest to die — sometimes within hours or when the redemption cap fills. We watch all of these and publish verified keys at the top of this page.</p>
<div class="warn">⚠️ <b>Code generators are scams.</b> Any site promising "unlimited keys", asking for your password, or making you complete surveys to "unlock" a code is trying to steal your account. Real keys are short words dropped on official channels — and you only ever redeem them in the game app or the official Market hub.</div>
{exp_block}
<h2>Reward keys — FAQ</h2>
{faq_html}
</div></main>
<footer><div class="wrap">
<a href="/about/">About</a><a href="/methodology/">How We Verify</a><a href="/contact/">Contact</a><a href="/privacy/">Privacy</a><a href="https://www.facebook.com/matchmastergiftslinks/" target="_blank" rel="noopener">Facebook</a>
<p class="disc">{BRAND} is an independent fan site. Not affiliated with Candivore or Match Masters. Keys are published only after being spotted on the game's official channels.</p>
<p class="disc">© 2026 {BRAND}</p>
</div></footer>
</body>
</html>"""
    outp = ROOT / "reward-keys" / "index.html"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(page)
    print(f"built reward-keys/ ({len(keys)} active keys)")

def build_booster_pages():
    """Render one HTML page per booster in data/boosters.json, then refresh the sitemap."""
    data = json.loads((ROOT / "data" / "boosters.json").read_text())
    boosters = data["boosters"]
    for b in boosters:
        sibs = [s for s in boosters if s["slug"] != b["slug"]]
        outp = ROOT / b["slug"] / "index.html"
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(render_booster(b, sibs))
        print(f"built booster page {b['slug']}/")
    build_keys_page()
    build_sitemap([b["slug"] for b in boosters])

def build_sitemap(booster_slugs):
    static = [
        ("/", "daily", "1.0"),
        ("/reward-keys/", "daily", "0.9"),
        ("/how-to-redeem/", "monthly", "0.8"),
        ("/free-boosters/", "monthly", "0.8"),
        ("/free-coins/", "monthly", "0.8"),
        ("/methodology/", "monthly", "0.6"),
        ("/about/", "yearly", "0.4"),
        ("/contact/", "yearly", "0.3"),
        ("/privacy/", "yearly", "0.3"),
    ]
    urls = "".join(
        f'  <url><loc>{SITE}{p}</loc><changefreq>{f}</changefreq><priority>{pr}</priority></url>\n'
        for p, f, pr in static)
    for s in booster_slugs:
        urls += (f'  <url><loc>{SITE}/{s}/</loc>'
                 "<changefreq>monthly</changefreq><priority>0.7</priority></url>\n")
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")
    print(f"sitemap.xml written ({len(static) + len(booster_slugs)} urls)")


if __name__ == "__main__":
    build()
