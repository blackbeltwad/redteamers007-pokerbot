# redteamers007: how our bot works

Entry: `my_bots/redteamers007/bot.py`. Heads-up No-Limit Hold'em, pure Python 3.10 (`eval7`, `numpy`).
Average think time is a few milliseconds; p99 is well under 100 ms in the real 0.5-CPU sandbox.

## In one sentence
A game-theoretic baseline that is hard to exploit, with a Bayesian opponent model on top that moves away
from equilibrium only as far as the evidence from the current match justifies.

## 1. Game-theoretic baseline
- **Short stacks (13 big blinds or less): Nash push/fold.** Precomputed equilibrium shove and call ranges
  (antes included). At these depths the equilibrium can't be beaten, so playing it removes our biggest
  source of risk once blinds rise.
- **Deeper stacks: range-vs-range preflop.** A precomputed 169 x 169 matrix of hand-vs-hand equities lets us
  measure every hand against the range the opponent actually plays, not against a random hand.
- **Postflop: Monte Carlo equity against a narrowed range.** Each opponent action narrows its range
  (bet -> top of range, call -> middle, raise -> top), and we simulate run-outs against the remaining
  weighted combinations. We found and fixed a subtle library issue: `eval7`'s range Monte Carlo ignores
  weights, so we sample combinations by weight ourselves.
- **Pot odds, expected value and equity realisation.** Calls require equity above the price, discounted
  when out of position.

## 2. Exploit layer: Bayesian opponent modelling
- Every opponent tendency (open rate, 3-bet rate, fold to 3-bet, fold to 4-bet, fold to bets,
  bets when checked to, bluff share) is a count of events over opportunities, **shrunk toward a prior**
  (empirical Bayes). Matches are short (often 25-80 hands), so this lets the bot adapt within a few
  hands without overreacting to noise.
- **Showdown calibration:** cards revealed at showdown tell us how often the opponent's bets were bluffs,
  and that share feeds directly into how wide we keep its betting range.
- **Examples of exploits that switch on only with evidence:** wider opens against over-folders, tighter
  opens against frequent 3-bettors, shoving wider against bots that under-call shoves, and (new in v3)
  **4-bet bluffs against bots that 3-bet a lot but fold to 4-bets**. The 4-bet bluff fires only when its
  expected value is positive under the measured fold rate, and it is capped by how often the opponent folds
  to our other re-raises, so it stays off against aggressive bots that don't fold.

## 3. How we know it works: a statistically clean lab
- **Duplicate matches** (same cards, seats swapped) and identical deals for both versions in every
  comparison, to cancel card luck.
- **Train/test split:** `dev` seeds for development, separate `holdout` seeds for the acceptance gate, so we
  never tune to the cards we judge on.
- **95% confidence intervals** on every number; no change ships without beating the current best on
  hold-out seeds (`lab/gate.py`).
- **Opponents:** ~130 sparring bots: 10 style archetypes, 20 randomised bots, targeted exploiters, 13 public
  bots from a previous Fullhouse event, and 14 profiles built from Pluribus/WSOP hand histories.
- **Sandbox fidelity:** we verified that our fast in-process lab and the real Docker sandbox make identical
  decisions, decision for decision, on fixed seeds.
- Full log of every hypothesis, result and decision (including rejected ideas): `lab/EXPERIMENTS.md`.

## 4. Results (match win rate, duplicate pairs, dev seeds)
| Version | Change | Whole field | Hardest public bot (gunslinger) |
|---|---|---|---|
| v0 | Nash push/fold + range-vs-range + Monte Carlo | 65.8% | - |
| v1 | weighted sampling fix, frequency-based range narrowing, showdown calibration | 73.6% | 67% |
| v2.1 | less exploitable postflop (fewer folds), reproducible RNG | 76.2% | 69.5% |
| v3 | evidence-gated 4-bet bluffs | 75.9% (flat) | **77.0%** |

Rejected on evidence, kept in the log: modelling opponents' 3-bets as bluff-heavy (lowered the win rate
monotonically from 74.3% to 72.6%), and several postflop tuning variants that were within noise.
