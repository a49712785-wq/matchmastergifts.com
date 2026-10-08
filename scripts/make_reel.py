#!/usr/bin/env python3
"""
make_reel.py — builds the daily Facebook reel for the Match Masters page.

Reads data/links.json, takes the currently-active gift links (last_status=ok,
max 3), picks a rotating base video from brand/reel-base/, burns in dynamic
text overlays (hook -> rewards -> CTA), and writes caption.txt + comment.txt.

Output: brand/reels/daily/YYYY-MM-DD/{reel.mp4,caption.txt,comment.txt}
Exits 0 with "SKIP" message when there are no active links (cron must not post).

Content policy (user decision 2026-10-06, replaces 2026-10-05 rule): FB caption
leads with https://matchmastergifts.com/ (hero CTA) + points to first comment;
first comment carries the DIRECT gift links + site link ("two paths" strategy —
data 2026-10-05: direct-link reel got 217 views, 87% non-follower reach).
Hashtags on every post. Honesty: cards say "checked Xh ago", never
"verified working in-game".
"""
import json, os, subprocess, sys, datetime, glob, re
from zoneinfo import ZoneInfo

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINKS_JSON = os.path.join(REPO, "data", "links.json")
BASE_DIR = os.path.join(REPO, "brand", "reel-base")
OUT_ROOT = os.path.join(REPO, "brand", "reels", "daily")
FONT = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
SITE_URL = "https://matchmastergifts.com/"
HASHTAGS = ("#MatchMasters #MatchMastersFreeGifts #FreeGifts #MatchMastersGifts "
            "#MobileGaming #FreeBoosters #PuzzleGames #GamingRewards")
SEG = 2.5          # seconds per text segment
MAX_REWARDS = 3


def esc(t: str) -> str:
    """Escape drawtext special characters."""
    return t.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")


def fontsize_for(text: str, base: int = 96) -> int:
    n = len(text)
    if n <= 14:
        return base
    if n <= 20:
        return 76
    if n <= 28:
        return 60
    return 48


def active_links():
    with open(LINKS_JSON) as f:
        data = json.load(f)
    out = []
    for day in data.get("days", []):
        for l in day.get("links", []):
            if l.get("last_status") == "ok":
                name = (l.get("amount") or "").strip() or (l.get("label") or "").strip()
                url = (l.get("url") or "").strip()
                if name and url and not any(x["name"] == name for x in out):
                    out.append({"name": name, "url": url, "date": day.get("date", "")})
            if len(out) >= MAX_REWARDS:
                break
        if len(out) >= MAX_REWARDS:
            break
    return out


def draw(text, color, size, y_off, t0, t1, sub=False):
    y = f"(h-text_h)/2{'+' if y_off >= 0 else ''}{y_off}" if y_off else "(h-text_h)/2"
    box = "box=1:boxcolor=black@0.65:boxborderw=26"
    return (f"drawtext=fontfile={FONT}:text='{esc(text)}':fontcolor={color}:"
            f"fontsize={size}:x=(w-text_w)/2:y={y}:{box}:"
            f"enable='between(t,{t0},{t1})'")


def build_caption(rewards, breaking=False):
    n = len(rewards)
    if breaking:
        head = f"\U0001f195 {n} NEW GIFT{'S' if n > 1 else ''} JUST DROPPED in Match Masters!"
    else:
        head = f"\U0001F381 {n} FREE GIFT{'S' if n > 1 else ''} LIVE in Match Masters!"
    lines = [head, ""]
    for r in rewards:
        lines.append(f"\u2705 {r['name']}")
    lines += [
        "",
        f"\U0001F447 2 ways to claim \u2014 pick what's easy:",
        f"\U0001F310 All links on our site: {SITE_URL}",
        "\U0001F4AC OR tap the direct gift links in the FIRST COMMENT",
        "",
        "Follow for DAILY free gifts, reward keys & codes \u2705",
        "",
        HASHTAGS,
    ]
    return "\n".join(lines)


def build_caption_fb(rewards, breaking=False):
    """Facebook caption — engagement-upgraded 2026-10-08 (user request).
    FB-only surface: youtube.txt is built separately and intentionally
    unchanged. Keeps the two-paths policy (site link hero + first-comment
    direct links) and adds comment-driving question, honest urgency
    (links really do expire in ~3 days) and a tag-a-friend prompt."""
    n = len(rewards)
    if breaking:
        head = (f"\U0001F195 JUST DROPPED: {n} NEW GIFT{'S' if n > 1 else ''} in "
                f"Match Masters \u2014 fresh & free, claim FAST! \u23F0")
    else:
        head = (f"\U0001F6A8 {n} FREE GIFT{'S' if n > 1 else ''} "
                f"{'are' if n > 1 else 'is'} LIVE in Match Masters \u2014 "
                f"claim before they expire! \u23F0")
    lines = [head, ""]
    for r in rewards:
        lines.append(f"\u2705 {r['name']}")
    lines += [
        "",
        "\U0001F4AC Which gift do you want most? Tell us in the comments! \U0001F447",
        "",
        f"\U0001F447 2 ways to claim \u2014 pick what's easy:",
        f"\U0001F310 All links on our site: {SITE_URL}",
        "\U0001F4AC OR tap the direct gift links in the FIRST COMMENT",
        "",
        "\U0001F465 Tag a friend who plays Match Masters!",
        "Follow for DAILY free gifts, reward keys & codes \u2705",
        "",
        HASHTAGS,
    ]
    return "\n".join(lines)


def build_comment(rewards):
    n = len(rewards)
    lines = [
        "\U0001F381 Tap to claim (opens in Match Masters):",
    ]
    nums = ["1\uFE0F\u20E3", "2\uFE0F\u20E3", "3\uFE0F\u20E3"]
    for i, r in enumerate(rewards):
        lines.append(f"{nums[i]} {r['name']}: {r['url']}")
    lines += [
        "",
        f"\U0001F310 All daily gifts + reward keys: {SITE_URL}",
        "Links checked daily \u2014 claim fast, they expire! \u23F0",
        "\U0001F4AC Claimed yours? Tell us which gift you got! \U0001F447",
    ]
    return "\n".join(lines)


def build_youtube(rewards, breaking=False):
    n = len(rewards)
    if breaking:
        hook = f"\U0001f195 {n} NEW GIFT{'S' if n > 1 else ''} JUST DROPPED in Match Masters!"
    else:
        hook = f"\U0001F381 {n} FREE GIFT{'S' if n > 1 else ''} LIVE in Match Masters!"
    caption = build_caption(rewards, breaking).replace(
        "\U0001F4AC OR tap the direct gift links in the FIRST COMMENT\n", "")
    return (f"{hook} #shorts\n\n{caption}\n\n"
            f"\U0001F310 {SITE_URL}")


def main():
    rewards = active_links()
    if not rewards:
        print("SKIP: no active links — no reel today")
        return 0

    today = datetime.date.today()
    today_str = today.isoformat()
    # Breaking mode (user decision 2026-10-06 — freshness is key in this niche):
    # reel built at/after 12:00 PKT and carrying links dropped today gets a
    # "JUST DROPPED" hook/caption instead of the morning "LIVE" framing.
    try:
        pkt_hour = datetime.datetime.now(ZoneInfo("Asia/Karachi")).hour
    except Exception:
        pkt_hour = 0
    breaking = pkt_hour >= 12 and any(r.get("date") == today_str for r in rewards)
    out_dir = os.path.join(OUT_ROOT, today.isoformat())
    os.makedirs(out_dir, exist_ok=True)

    bases = sorted(glob.glob(os.path.join(BASE_DIR, "base-*.mp4")))
    if not bases:
        print("ERROR: no base videos in brand/reel-base/", file=sys.stderr)
        return 1
    base = bases[today.timetuple().tm_yday % len(bases)]

    n = len(rewards)
    filters = []
    t = 0.0
    # Hook — engagement upgrade 2026-10-08 (user-approved): pattern-interrupt
    # hooks ROTATE daily so repeat viewers don't tune out; number + urgency
    # up front (sound-off autoplay — the first 2 seconds decide the swipe).
    # Plain ASCII only: the drawtext font has no emoji glyphs.
    if breaking:
        hook_variants = [
            ("JUST DROPPED!", "brand-new gifts \u2014 claim FAST"),
            ("NEW GIFTS LANDED!", "fresh drop \u2014 be quick!"),
        ]
    else:
        hook_variants = [
            ("FREE GIFTS ALERT!", f"{n} gift{'s' if n > 1 else ''} waiting for you"),
            ("WAIT \u2014 FREE GIFTS!", "no catch \u2014 just tap & claim"),
            (f"{n} FREE GIFT{'S' if n > 1 else ''} TODAY!", "claim before they expire"),
        ]
    hook, sub = hook_variants[today.timetuple().tm_yday % len(hook_variants)]
    filters.append(draw(hook, "white", fontsize_for(hook, 88), -140, t, t + SEG))
    filters.append(draw(sub, "#22c55e", 52, 10, t, t + SEG))
    t += SEG
    # Rewards
    for r in rewards:
        filters.append(draw(r["name"].upper(), "#22c55e",
                            fontsize_for(r["name"].upper()), -100, t, t + SEG))
        filters.append(draw("FREE \u2014 tap to claim now", "white", 52, 60, t, t + SEG))
        t += SEG
    # CTA
    filters.append(draw("LINK IN 1st COMMENT", "#22c55e",
                        fontsize_for("LINK IN 1st COMMENT", 88), -140, t, t + SEG))
    filters.append(draw("Follow \u2014 new gifts daily", "white", 52, 10, t, t + SEG))
    t += SEG

    total = t
    vf = "scale=1080:1920," + ",".join(filters)
    out_mp4 = os.path.join(out_dir, "reel.mp4")
    cmd = ["ffmpeg", "-y", "-stream_loop", "2", "-i", base,
           "-vf", vf, "-t", str(total),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-c:a", "aac", "-movflags", "+faststart", out_mp4]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("ERROR: ffmpeg failed\n" + r.stderr[-2000:], file=sys.stderr)
        return 1

    with open(os.path.join(out_dir, "caption.txt"), "w") as f:
        f.write(build_caption_fb(rewards, breaking))
    with open(os.path.join(out_dir, "comment.txt"), "w") as f:
        f.write(build_comment(rewards))
    with open(os.path.join(out_dir, "youtube.txt"), "w") as f:
        f.write(build_youtube(rewards, breaking))

    print(f"OK: reel built -> {out_mp4} ({n} rewards, base={os.path.basename(base)})")
    print("rewards: " + " | ".join(r["name"] for r in rewards))
    return 0


if __name__ == "__main__":
    sys.exit(main())
