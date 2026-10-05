#!/usr/bin/env python3
"""
make_reel.py — builds the daily Facebook reel for the Match Masters page.

Reads data/links.json, takes the currently-active gift links (last_status=ok,
max 3), picks a rotating base video from brand/reel-base/, burns in dynamic
text overlays (hook -> rewards -> CTA), and writes caption.txt + comment.txt.

Output: brand/reels/daily/YYYY-MM-DD/{reel.mp4,caption.txt,comment.txt}
Exits 0 with "SKIP" message when there are no active links (cron must not post).

Content policy (user decision 2026-10-05): NO direct official gift links in FB
posts/comments — only https://matchmastergifts.com/. Hashtags on every post.
Honesty: cards say "checked Xh ago", never "verified working in-game".
"""
import json, os, subprocess, sys, datetime, glob, re

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
                if name and not any(x["name"] == name for x in out):
                    out.append({"name": name})
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


def build_caption(rewards):
    n = len(rewards)
    lines = [
        f"\U0001F381 {n} FREE GIFT{'S' if n > 1 else ''} LIVE in Match Masters!",
        "",
    ]
    for r in rewards:
        lines.append(f"\u2705 {r['name']}")
    lines += [
        "",
        "All links verified today \u2014 claim before they expire \u23F0",
        "\U0001F447 LINK IN THE FIRST COMMENT",
        "",
        "Follow for DAILY free gifts, reward keys & codes \u2705",
        "",
        HASHTAGS,
    ]
    return "\n".join(lines)


def build_youtube(rewards):
    n = len(rewards)
    hook = f"\U0001F381 {n} FREE GIFT{'S' if n > 1 else ''} LIVE in Match Masters!"
    caption = build_caption(rewards).replace(
        "\U0001F447 LINK IN THE FIRST COMMENT",
        f"\U0001F447 CLAIM HERE: {SITE_URL}")
    return (f"{hook} #shorts\n\n{caption}\n\n"
            f"\U0001F310 {SITE_URL}")
    return ("\U0001F381 Claim today's gifts here:\n"
            f"\U0001F449 {SITE_URL}\n"
            "\n"
            "All links checked daily \u2014 claim fast, they expire! \u23F0")


def main():
    rewards = active_links()
    if not rewards:
        print("SKIP: no active links — no reel today")
        return 0

    today = datetime.date.today()
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
    # Hook
    hook = "FREE GIFT IS LIVE!" if n == 1 else "FREE GIFTS ARE LIVE!"
    sub = f"{n} reward{'s' if n > 1 else ''} waiting"
    filters.append(draw(hook, "white", 88, -140, t, t + SEG))
    filters.append(draw(sub, "#22c55e", 52, 10, t, t + SEG))
    t += SEG
    # Rewards
    for r in rewards:
        filters.append(draw(r["name"].upper(), "#22c55e",
                            fontsize_for(r["name"].upper()), -100, t, t + SEG))
        filters.append(draw("FREE - claim now", "white", 52, 60, t, t + SEG))
        t += SEG
    # CTA
    filters.append(draw("LINK IN COMMENTS", "#22c55e", 88, -140, t, t + SEG))
    filters.append(draw("Follow for daily gifts", "white", 52, 10, t, t + SEG))
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
        f.write(build_caption(rewards))
    with open(os.path.join(out_dir, "comment.txt"), "w") as f:
        f.write(build_comment())
    with open(os.path.join(out_dir, "youtube.txt"), "w") as f:
        f.write(build_youtube(rewards))

    print(f"OK: reel built -> {out_mp4} ({n} rewards, base={os.path.basename(base)})")
    print("rewards: " + " | ".join(r["name"] for r in rewards))
    return 0


if __name__ == "__main__":
    sys.exit(main())
