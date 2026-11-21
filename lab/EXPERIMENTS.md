# Experiments log (read this first every session)

Setup: Python 3.10 venv at .venv (`source .venv/bin/activate`). Lab = `python -m lab.run`, gate = `python -m lab.gate`.
Seeds: `dev` for development/screening, `holdout` only for gate decisions. Pair = same seed, seats swapped, standard blinds, freezeout.
Time factor tf=2.0 (local ms x2 ~ half-core). Opp sets: `core` (10 archetypes + kit bots), `randN`, `exploit`, `snap:<v>`.
Snapshots: `lab/snapshot.sh vN` -> lab/snapshots/vN (git-tagged when accepted).

## Lab sanity (2026-11-21)
- archetype TAG vs core 4 pairs: mirror (tag vs tag) = 50% all draws; beats station/kit/random. Throughput ~30 matches/s on 7 workers.
- Docker not yet available (cask install needs sudo) -> fast path vs --docker check pending.

## v0 baseline (2026-11-21)
Nash push/fold <=13bb, range-vs-range preflop from 169x169 matrix, postflop MC vs narrowed range, shrunk opponent stats.
Screen dev 10 pairs vs core: 65.8% [59.6,71.5]; loses to lag 40, tag 45, minraiser 45, overfolder 45. p99 think 160ms.

## v1 = v0 + three fixes (screened on dev, core 4-opp subset 30 pairs then core+rand20+exploit 20 pairs)
1. Range narrowing by measured opp frequencies (bet->top bwc, call->top 1-ftb, raise->top rvb). 47.1 -> 52.9 (4 hard opps).
2. Equity realisation factor on flop/turn calls (0.85-0.95). 52.9 -> 53.8 (noise).
3. **BUG FIX: eval7.py_hand_vs_range_monte_carlo IGNORES weights** -> sample 400 combos by weight. 53.8 -> 62.1.
4. Showdown-calibrated bluff share of opp bets (floor in narrowing), deep-stack margin on preflop all-in calls
   (+0..0.08 eq for S 20..100bb), tighter opens vs frequent 3-bettors. Broad dev: 71.5 -> 73.6 [71.3,75.8].
Snapshot lab/snapshots/v1. Gate vs v0: see below.

## External sparring bots (Fullhouse 2026 public repos, same engine/API) in lab/ext (gitignored), set `ext`
Pinned: txnujk09/fullhouse-poker-bot@4fe1543, advitrocks9/fullhouse-bot@e504793 (bots/strong only; bot/ uses
package import that fails), TimoJanssen1/tumbleweed@38b701d, utsochaudhuri/lomaans-poker-table@5b22793,
Lang-Chen124/poker-bot@98e5c04, Atharva-Mansabdar/FullHouseHack26@c6c8043. All pass validator; grep found no
network/subprocess. Sparring only, never copied. Lab loader now isolates sibling-module imports per bot.
**Gate v1 vs v0 (holdout, 100 pairs x 37 opps + 200 h2h): PASS.** h2h 73.0% [68.4,77.1] (101-90-9);
set 71.8% [70.8,72.8] vs 64.0%; 0 errors/timeouts; p99 worst match 501ms (machine was also running other jobs).

## v1 vs ext (dev, 30 pairs x 13 bots): 84.1% [81.4,86.5], pairs 270-116-4. Weakest gunslinger 67% (3/4-bets a lot).
Leak: postflop over-folding (FtbF/T/R 70/79/85 vs ext).

## H2: over-folding postflop (dev, core+rand20+exploit+ext, 20 pairs, CRN)
Added TUNE dict + configure() hook (lab-only A/B; sandbox never calls it).
base(bluff_prior .15) 75.0 | A(.25) 76.1 | A35(.35) 75.4 | B(realisation .93) 75.3 | A+B 75.3  -- all within noise.
A lowers FtbF/T/R 63/70/73 -> 57/63/66 (less exploitable), core +2, rand +2, ext flat. Chose A -> v2 candidate.
