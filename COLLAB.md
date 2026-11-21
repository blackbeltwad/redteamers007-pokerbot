# Working together: two humans, two Claude sessions, one repo

Deadline: **7:00 PM**. Bot freeze **6:00 PM**; final push and fresh-clone validate by **6:30 PM**.

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
External bots (`ext` set) live in gitignored `lab/ext/`; re-clone them with the commits pinned in `lab/EXPERIMENTS.md`, or skip `ext`.

## Suggested split (now → 6 PM)
**Claude A:** gate v2 (bluff prior), then late-game push/fold accuracy (5-20bb with antes), then 3-bet defence vs aggressive bots (gunslinger leak), then freeze.

**Claude B, in priority order:**
1. **Docker** (needs `sudo`; the human runs `brew install --cask docker` and opens it once). Then `make sandbox` and `python play.py my_bots/redteamers007 bots/caller --docker --seed 1`. Report think times and any errors. This is the one check we haven't done.
2. **Stronger exploiter bots** in `lab/opponents/exploiters/`, aimed at our tendencies: we open ~78% from the SB, 3-bet ~15%, and fold to postflop bets ~57/63/66%. Ideas: a 3-bet-everything bot, a river over-bluffer, a check-raiser.
3. **Side-prize analysis:** cost of opening 7-2 from the SB / bluffing with 7-2 (`7-2 won/dealt` is in `summary.md`). Propose it only if the gate says it's free.
4. More public bots from the Fullhouse repos as sparring partners (validate first, pin the commit, add to `EXT` in `lab/opponents/sets.py`).

## Compute etiquette
Each run uses all cores but one. Don't run two big jobs on the same machine at once (it slows both and inflates think-time p99). Run jobs detached and read `summary.md`, not raw logs.
