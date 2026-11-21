# Notes for Wadley (from Moise's session, 2026-11-21 afternoon)

**`main` still ships v2.1.** Nothing in `my_bots/redteamers007/` changed in this push. The final pick
(v2.1 or v3.1) is made by the tournament simulator before the 17:45 freeze.

## Read these first
- `STRATEGY.md`: how the bot works, for the judges (game theory base, Bayesian exploit layer, lab method, results).
- `lab/EXPERIMENTS.md`: new entries H3-H6 at the bottom (what we tried today, numbers, decisions).
- `lab/IDEAS.md`: ranked outside-the-box ideas (common student-bot bugs, bet-size cliffs, hard-coded BB=100).

## What's new
- **v3** (`lab/snapshots/v3`): evidence-gated 4-bet bluff. gunslinger 69.5% -> 77% (dev), 72% -> 76% (holdout).
  Formal gate vs v2.1 failed narrowly (set 73.8 vs 74.0, h2h 47.5% [42.7,52.4]), so it was not shipped on its own.
- **v3.1** (`lab/snapshots/v3_1`): v3 + `mc_refine=3` (extra Monte Carlo near decision thresholds; 8% of
  facing-bet decisions used to flip on MC noise).
- Rejected with evidence: modelling 3-bets as bluff-heavy (H3), blind-level decay of stats (H5).
- **`lab/tournament.py`**: simulates the real tournament (round robin of duplicate pairs, top 4, knockout).
  v2.1 on holdout, 40-bot field, 4 tournaments: rank 1 and won 4/4.
- **`lab/tools/profile_bot.py`**: think-time per street and hotspots. The bot uses ~10% of the 2 s budget.
- `.claude/agents/perf-coder.md` and `.claude/agents/strategist.md`: reusable Claude Code agents.
- The 13 `ext` sparring bots are fetched and validated on my machine (pinned commits from the log).

## Pushing to `main`
We both push to `main`. Always `git pull --rebase` before pushing, only push gate-passed bot changes, and say in
chat before touching `my_bots/redteamers007/bot.py`.

## Claude co-author line
To stop your Claude session adding `Co-Authored-By: Claude ...` to commits, add this to `~/.claude/settings.json`
and restart Claude Code:

```json
"attribution": { "commit": "", "pr": "" }
```
