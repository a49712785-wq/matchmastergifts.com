# matchmastergifts.com — ops runbook

Static HTML site. No WordPress, no plugins, no build step beyond `scripts/build.py`.

## How daily updates work
1. `scripts/collect.py` (cron, every morning PKT): scans official Match Masters
   Facebook posts + backup fan sources for new gift links.
2. New links appended to `data/links.json` with `posted_at`, `checked_at`,
   `label`, `amount`, `source`. Days older than 3 days are dropped.
3. `scripts/build.py` regenerates `index.html` from the template.
4. `git push` → GitHub Pages serves it on matchmastergifts.com (via CNAME).

## Verification rules (the trust moat)
- Only links from official posts. Never invented, never generator links.
- Every link gets an HTTP liveness check before publish.
- Page shows absolute "Updated ..." timestamps — never fake relative ones.
- Expired links (>3 days) leave the live block automatically.

## Local commands
- `python3 scripts/build.py` — rebuild index.html
- `python3 -m http.server` — preview locally

## Daily ops — gift link collection

`scripts/collect.py` is the gatekeeper between a candidate link and the live page.

**Morning loop (assisted — Facebook blocks unattended scraping):**
1. Open the official Match Masters Facebook page, copy new gift post URLs + reward text.
2. `python3 scripts/collect.py add --url <URL> --label "Free Coins" --amount "500" --source-url <post URL> --posted-at 2026-09-28T09:00`
   - strips tracking params, dedupes, liveness-checks (must resolve on the official link domain)
   - refuses anything that fails — never publishes unchecked links
3. `python3 scripts/build.py` → `git add -A && git commit && git push`
4. `recheck` re-verifies the 3-day window; `prune` trims the archive.

**Honesty rule:** liveness = URL resolves. It is NOT proof of in-game redemption.
Cards show "checked Xh ago", never "verified working in-game".
