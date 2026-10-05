#!/usr/bin/env python3
"""
collect.py — Match Master Gifts link collector (v1, assisted).

The game publishes gift links on its OFFICIAL social pages (Facebook primary).
Facebook blocks unattended scraping, so v1 is "assisted":

  Morning loop (agent or human):
    1. Open the official Match Masters Facebook page (see SOURCES below).
    2. Copy each new gift post's link URL + reward text.
    3. Run:  python3 scripts/collect.py add --url <URL> --label "Free Coins" \
                 --amount "500" --source "official Facebook post" \
                 --source-url <post URL> --posted-at 2026-09-28T09:00
    4. Script dedupes, liveness-checks the URL, stamps checked_at.
    5. Run:  python3 scripts/build.py   (rebuilds index.html)
    6. Commit + push (GitHub Action can do 5-6 automatically).

Commands:
  add      add one candidate link (dedupe + liveness check + stamp)
  recheck  re-run liveness on all links in the current 3-day window
  prune    drop links older than the expiry window from live buckets
           (they stay visible in the collapsed "previous days" archive)

Liveness != redemption: an HTTP check proves the URL resolves on the game's
official link domain. It CANNOT prove the reward redeems in-app (that would
require playing on someone's account, which we never do). Statuses stay
honest: we show "checked Xh ago", never "verified working in-game".
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "links.json"
PKT = timezone(timedelta(hours=5))

SOURCES = [
    "https://www.facebook.com/MatchMastersGame",   # primary
    # Backups if FB is unreachable: official Instagram / X / Discord posts.
]

OFFICIAL_HOSTS = ("onelink.me", "matchmasters.com")

TRACKING_PARAMS = {"fbclid", "utm_source", "utm_medium", "utm_campaign",
                   "utm_term", "utm_content", "gclid", "mc_cid", "mc_eid"}


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    p = urllib.parse.urlsplit(url)
    qs = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
    qs = [(k, v) for k, v in qs if k.lower() not in TRACKING_PARAMS]
    return urllib.parse.urlunsplit(
        (p.scheme.lower(), p.netloc.lower(), p.path,
         urllib.parse.urlencode(qs), ""))


def liveness_check(url: str, timeout: int = 15):
    """Follow redirects; return (ok, final_url, status)."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; MatchMasterGiftsBot/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            final = r.geturl()
            host = urllib.parse.urlsplit(final).netloc.lower()
            official = any(h in host for h in OFFICIAL_HOSTS)
            return (200 <= r.status < 400 and official, final, r.status)
    except Exception as e:
        return (False, url, f"error: {type(e).__name__}")


def load():
    return json.loads(DATA.read_text())


def save(data):
    data["updated"] = datetime.now(PKT).strftime("%Y-%m-%dT%H:%M")
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def all_urls(data):
    seen = {}
    for d in data.get("days", []):
        for l in d.get("links", []):
            seen.setdefault(normalize_url(l.get("url", "")), l)
    return seen


def cmd_add(a):
    data = load()
    seen = all_urls(data)
    url = normalize_url(a.url)
    if url in seen:
        print(f"DUPLICATE — already in data (label: {seen[url].get('label')}). Skipped.")
        return 1
    ok, final, status = liveness_check(url)
    print(f"liveness: ok={ok} final={final} status={status}")
    if not ok:
        print("REFUSED — link does not resolve on the official link domain. Not published.")
        return 2
    try:
        posted = datetime.fromisoformat(a.posted_at)
    except ValueError:
        print("bad --posted-at (use ISO like 2026-09-28T09:00)."); return 3
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=PKT)
    now = datetime.now(PKT)
    entry = {
        "url": url,
        "label": a.label,
        "amount": a.amount or "",
        "posted_at": posted.astimezone(PKT).strftime("%Y-%m-%dT%H:%M"),
        "checked_at": now.strftime("%Y-%m-%dT%H:%M"),
        "source": a.source or "official post",
        "source_url": a.source_url or "",
    }
    day_key = now.strftime("%Y-%m-%d")
    days = data.setdefault("days", [])
    bucket = next((d for d in days if d.get("date") == day_key), None)
    if bucket is None:
        bucket = {"date": day_key, "links": []}
        days.insert(0, bucket)
    bucket["links"].append(entry)
    data["days"] = sorted(days, key=lambda d: d.get("date", ""), reverse=True)[:4]
    save(data)
    print(f"ADDED to {day_key}: {a.label} ({a.amount}). Now run: python3 scripts/build.py")
    return 0


def cmd_recheck(_a):
    data = load()
    now = datetime.now(PKT)
    cutoff = now - timedelta(days=3)
    changed = 0
    for d in data.get("days", []):
        try:
            day_dt = datetime.fromisoformat(d.get("date", "")).replace(tzinfo=PKT)
        except ValueError:
            continue
        if day_dt < cutoff - timedelta(days=4):
            continue
        for l in d.get("links", []):
            ok, final, status = liveness_check(l["url"])
            l["checked_at"] = now.strftime("%Y-%m-%dT%H:%M")
            l["last_status"] = "ok" if ok else f"dead ({status})"
            changed += 1
            print(f"{'OK  ' if ok else 'DEAD'} {l.get('label')} — {status}")
    save(data)
    print(f"rechecked {changed} links.")
    return 0


def cmd_prune(_a):
    # build.py already hides >3d links from the live block; prune just trims
    # the archive to the last 4 day-buckets (already enforced in add).
    data = load()
    before = len(data.get("days", []))
    data["days"] = sorted(data.get("days", []),
                          key=lambda d: d.get("date", ""), reverse=True)[:4]
    save(data)
    print(f"pruned {before} -> {len(data['days'])} day buckets.")
    return 0


KEYS_DATA = ROOT / "data" / "keys.json"


def load_keys():
    return json.loads(KEYS_DATA.read_text())


def save_keys(data):
    data["updated"] = datetime.now(PKT).strftime("%Y-%m-%dT%H:%M")
    KEYS_DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def cmd_add_key(a):
    """Add a typed reward key spotted on an official channel.

    Keys are NOT URLs — they cannot be HTTP liveness-checked. "Verified"
    here means: a human (or the daily agent) saw this exact code on an
    official Match Masters post/stream/channel. We never invent keys and
    never copy them from fan sites without an official source.
    """
    data = load_keys()
    code = a.key.strip()
    if not code:
        print("empty --key. Skipped."); return 3
    seen = {k.get("key", "").lower() for k in data.get("keys", [])}
    if code.lower() in seen:
        print(f"DUPLICATE — key '{code}' already tracked. Skipped.")
        return 1
    try:
        posted = datetime.fromisoformat(a.posted_at)
    except ValueError:
        print("bad --posted-at (use ISO like 2026-09-28T09:00)."); return 3
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=PKT)
    now = datetime.now(PKT)
    entry = {
        "key": code,
        "reward": a.reward or "",
        "source": a.source or "official post",
        "source_url": a.source_url or "",
        "posted_at": posted.astimezone(PKT).strftime("%Y-%m-%dT%H:%M"),
        "spotted_at": now.strftime("%Y-%m-%dT%H:%M"),
        "status": "active",
        "notes": a.notes or "",
    }
    data.setdefault("keys", []).insert(0, entry)
    save_keys(data)
    print(f"ADDED key '{code}' ({a.reward}). Now run: python3 scripts/build.py")
    return 0


def cmd_expire_keys(_a):
    """Mark keys older than 7 days as expired (keys die fast; livestream
    keys often within hours — the daily agent should expire those manually
    when the source says so)."""
    data = load_keys()
    now = datetime.now(PKT)
    cutoff = now - timedelta(days=7)
    changed = 0
    for k in data.get("keys", []):
        if k.get("status") != "active":
            continue
        try:
            posted = datetime.fromisoformat(k.get("posted_at", "")).replace(tzinfo=PKT)
        except ValueError:
            continue
        if posted < cutoff:
            k["status"] = "expired"
            changed += 1
            print(f"EXPIRED {k.get('key')}")
    save_keys(data)
    print(f"expired {changed} key(s).")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Match Master Gifts link collector")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="add one candidate link")
    p.add_argument("--url", required=True)
    p.add_argument("--label", required=True, help='e.g. "Free Coins"')
    p.add_argument("--amount", default="", help='e.g. "500"')
    p.add_argument("--source", default="official Facebook post")
    p.add_argument("--source-url", default="")
    p.add_argument("--posted-at", required=True, help="ISO, e.g. 2026-09-28T09:00")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("recheck", help="re-verify links in window")
    p.set_defaults(fn=cmd_recheck)

    p = sub.add_parser("prune", help="trim archive buckets")
    p.set_defaults(fn=cmd_prune)

    p = sub.add_parser("add-key", help="add one typed reward key (official source only)")
    p.add_argument("--key", required=True, help="the exact code as shown officially")
    p.add_argument("--reward", default="", help='e.g. "500 coins"')
    p.add_argument("--source", default="official post")
    p.add_argument("--source-url", default="")
    p.add_argument("--posted-at", required=True, help="ISO, e.g. 2026-09-28T09:00")
    p.add_argument("--notes", default="", help='e.g. "livestream key, may cap out"')
    p.set_defaults(fn=cmd_add_key)

    p = sub.add_parser("expire-keys", help="mark keys older than 7 days expired")
    p.set_defaults(fn=cmd_expire_keys)

    a = ap.parse_args()
    sys.exit(a.fn(a))


if __name__ == "__main__":
    main()
