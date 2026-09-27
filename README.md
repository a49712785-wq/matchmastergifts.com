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
