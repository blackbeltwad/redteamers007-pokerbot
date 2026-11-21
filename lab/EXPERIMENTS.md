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
