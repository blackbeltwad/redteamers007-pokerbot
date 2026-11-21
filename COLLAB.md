# Working together: two humans, two Claude sessions, one repo

Deadline: competition starts **7:00 PM** (end of coding possibly later, up to 10 PM: unconfirmed).
`main` ALWAYS holds a gate-passed, working bot, so a surprise cutoff is safe. Freeze ~1 h before the confirmed cutoff.

## Current state (keep this block updated)
- **Shipped on `main`: v2.1** (tag `v2.1`) = v2 + eval7 RNG seeding (exact replays). History: v0 -> v1 (h2h 73%) -> v2 (h2h 52%, less exploitable) -> v2.1.
- v2 hold-out: 76.6% vs core+rand20+exploit+ext, 71.2% vs dataset bots, 0 errors/timeouts.
- Weakest real matchup: `e_gunslinger` (~67%, heavy 3-bet/4-bet). Over-folding to 3-bets is the next leak.
- Docker: DONE on Claude A's machine. Sandbox p99 <= 31ms, 0 errors; lab fast path == docker decision-for-decision.

## Roles
| | Claude A (owner, this machine) | Claude B (teammate's machine) |
|---|---|---|
| Owns | `my_bots/redteamers007/`, `main`, gate decisions, `lab/run.py` / `lab/gate.py` core | new opponents, adapters, analysis tools, side-prize research, Docker check |
| Writes to | `main` (only gated bot changes) | branches `exp/<topic>` only, never `main` |
| Experiments | strategy changes to the bot | proposes bot changes as a branch plus evidence |

**Only Claude A merges into `main` and ships `my_bots/redteamers007/`.** That rule prevents two people overwriting the bot 20 minutes before the deadline.

## Protocol
1. **Start of each session:** `git pull`, then read `lab/EXPERIMENTS.md` (the shared memory) and this file.
2. **One hypothesis per branch:** `git checkout -b exp/<topic>`. Change one thing, screen on `dev` seeds:
   `python -m lab.run --hero my_bots/redteamers007 --opps core,rand20,exploit,ext --pairs 20 --label <topic>`
3. **If it looks good:** append an entry to `lab/EXPERIMENTS.md` (hypothesis, command, result with CI), push the branch, and tell the other human "exp/<topic> ready".
4. **Claude A** snapshots it, runs the gate on **hold-out** seeds vs the current best:
   `python -m lab.gate --cand snap:vN --best snap:vN-1 --opps core,rand20,exploit,ext`
   It merges and tags `vN` only on PASS.
5. **Don't tune on `holdout` seeds**, ever. Don't edit `pokercore/`.
6. **Lab extensions** (new stats, opponents) must not change how existing numbers are computed; if they do, say so in the log.

## Setup on the second machine
```
git clone git@github.com:blackbeltwad/redteamers007-pokerbot.git && cd redteamers007-pokerbot
uv python install 3.10 && uv venv --seed -p 3.10 .venv && source .venv/bin/activate
make install PYTHON=python
python -m lab.tools.preflop_tables      # rebuilds lab/data/preflop.json (~2 min) if missing
```
Gitignored data you must fetch yourself (commits pinned in `lab/EXPERIMENTS.md`):
- `lab/ext/`: public Fullhouse bots for the `ext` set. `git clone --depth 1` each repo listed in `EXT` in
  `lab/opponents/sets.py` into `lab/ext/<owner>_<repo>`, then `git checkout` the pinned commit. Or skip `ext`.
- `lab/datasets/phh-dataset/`: `git clone --depth 1 --filter=blob:none --sparse https://github.com/uoftcprg/phh-dataset lab/datasets/phh-dataset`
  then `cd` into it and `git sparse-checkout set data/pluribus data/wsop`. Only needed to rebuild
  `lab/data/dataset_profiles.json`, which is committed, so the `dataset` set works without it.

## Opponent sets (`--opps`, comma separated)
| token | what | count |
|---|---|---|
| `core` | 10 archetypes (station, maniac, nit, tag, lag, overfolder, shover, trapper, random, minraiser) + 2 kit bots | 12 |
| `rand20` | random-parameter archetypes (generalisation check) | 20 |
| `exploit` | bots aimed at our habits (`lab/opponents/exploiters/`) | 5 |
| `ext` | public Fullhouse 2026 bots, same engine | 13 |
| `dataset` | archetypes fitted to real players (Pluribus + 13 pros) by `lab/tools/phh_stats.py` | 14 |
| `snap:vN` | our own snapshots | - |
Standard full test: `--opps core,rand20,exploit,ext,dataset`.

## Useful tools
- `python -m lab.tools.lines <results dir> [opp]`: chips won/lost by our decision line (find leaks).
- `python -m lab.tools.phh_stats <dir with .phh files>`: streams any size of hand-history data into player profiles.
- A/B without editing the bot: `--hero "lab/snapshots/vN::bluff_prior=0.3"` (bot exposes `TUNE` + `configure()`, lab-only).
- Gate: `python -m lab.gate --cand snap:vNEW --best snap:vOLD --opps core,rand20,exploit,ext,dataset`.

## Suggested split (now → 6 PM)
**Claude A:** 3-bet defence vs aggressive bots (gunslinger leak), late-game push/fold accuracy (5-20bb with antes), `PRESENTATION.md`, then freeze.

**Claude B, in priority order:**
1. ~~Docker~~ done by Claude A (re-run `play.py --docker` once before the freeze).
2. **Stronger exploiter bots** in `lab/opponents/exploiters/`, aimed at our tendencies: we open ~78% from the SB, 3-bet ~15%, and fold to postflop bets ~57/63/66%. Ideas: a 3-bet-everything bot, a river over-bluffer, a check-raiser.
3. **Side-prize analysis:** cost of opening 7-2 from the SB / bluffing with 7-2 (`7-2 won/dealt` is in `summary.md`). Propose it only if the gate says it's free.
4. More public bots from the Fullhouse repos as sparring partners (validate first, pin the commit, add to `EXT` in `lab/opponents/sets.py`).
5. If the 20 GB Zenodo archive is available: unzip only the ACPC heads-up NLHE part and run `lab/tools/phh_stats.py` on it (heads-up, so no 2.3x widening needed: set `HU_SCALE = 1.0`). Commit only the small profiles JSON.

## Compute etiquette
Each run uses all cores but one. Don't run two big jobs on the same machine at once (it slows both and inflates think-time p99). Run jobs detached and read `summary.md`, not raw logs.
