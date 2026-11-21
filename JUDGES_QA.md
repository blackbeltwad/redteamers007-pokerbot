# Judges Q&A: redteamers007

Short answers to the questions we expect, with the numbers behind them. The design itself is in `STRATEGY.md`;
every experiment, including rejected ones, is in `lab/EXPERIMENTS.md`.

---

## 1. How does the bot decide?
- **Game-theoretic base.** At 13 big blinds or less it plays a precomputed **Nash equilibrium** push/fold
  strategy, which can't be beaten at those depths. Deeper, it compares its hand against the opponent's likely
  range using a precomputed 169 x 169 **hand-vs-hand equity matrix**. After the flop it runs a **Monte Carlo**
  simulation of the remaining cards against the opponent's narrowed range.
- **Exploit layer.** It tracks the opponent's tendencies (open rate, 3-bet rate, fold to 3-bet/4-bet, fold to bets,
  bluff share at showdown) with **Bayesian shrinkage**: each statistic starts at a typical value and moves toward
  what the opponent actually does. Matches are short (25-80 hands), so this lets it adapt in a few hands without
  overreacting to noise.
- **Every decision is expected value.** It calls, folds, bets or bluffs only when the chips it expects to win beat
  the chips it risks.

## 2. How did you get your analytics?
- We built a test lab that plays our bot against **64 sparring bots**: 10 playing-style archetypes plus the kit's
  2 bots, 20 bots with random styles, 5 "exploiter" bots aimed at our own weaknesses, 13 public bots from a
  previous Fullhouse hackathon (same engine), and 14 profiles of professionals and the Pluribus AI built from
  public hand histories (Pluribus/WSOP data).
- Every decision is logged with its reason (for example "call: equity 0.41 > needed 0.33"). A leak finder
  (`lab/tools/lines.py`) adds up the chips won or lost per type of decision, so we see exactly where we lose.
- A profiler (`lab/tools/profile_bot.py`) measures think time per street and the code hotspots.

## 3. How many games did you simulate, and how?
- **Over 128,000 matches today, about 9 million hands.**
- One **match** follows the tournament rules: heads-up, 10,000 chips each, blinds 25/50 rising every 20 hands,
  antes from hand 101, until one bot has all the chips (about 75 hands on average). One **pairing** is two matches
  with the same cards and the seats swapped.

| Test | Opponents | Setup | Matches | Time |
|---|---|---|---|---|
| Screening | 64 | 20 pairings each, practice deals | 2,560 (~190,000 hands) | ~4 min |
| Single opponent | 1 | 100 pairings | 200 | ~1 min |
| Acceptance gate | 64 + head-to-head | 50 pairings each for both versions + 200 head-to-head pairings, test deals | ~13,200 (~1 million hands) | ~30 min |
| Tournament simulation | 40-bot field | full round robin (780 pairings) + top-4 knockout, 4 tournaments | ~6,300 per version | ~13 min |

**How it's fast enough:**
1. The engine (`pokercore/`) is byte for byte the organisers' code. In the lab we call each bot's `decide()`
   directly in Python instead of starting a Docker container per bot, so there is no start-up or communication
   overhead.
2. 15 worker processes run matches in parallel on 16 CPU cores: **8-15 matches per second**.
3. Our bot decides in about 2-10 ms, so a 300-decision match takes 1-2 seconds.
4. **Fidelity check:** on the same seeds, the fast lab and the real Docker sandbox make the same decision every
   time (`lab/tools/fidelity.py`), so the shortcut doesn't change results.
5. **Timing realism:** the tournament gives each bot half a CPU core, so the lab doubles every measured think time
   (`--tf 2.0`) when checking against the 2-second limit.

## 4. What's the difference between good data and bad data?
| Good data | Bad data |
|---|---|
| Both versions play **the same cards**, so only the bot differs | Different cards: luck gets mistaken for skill |
| **Duplicate pairs** (seats swapped) cancel card luck | Single matches are mostly luck |
| Large samples: 20-100 pairings per opponent, thousands of matches | 5-10 matches: noise |
| Separate **practice** (`dev`) and **test** (`holdout`) deals | Testing on the cards you tuned on: overfitting |
| Many different opponents | One opponent: you learn to beat only that bot |
| Lab verified against the real sandbox | A lab that behaves differently from the tournament |
| Fixed random seeds: every match replays exactly | Unrepeatable results |

## 5. How do you test versions against each other?
1. **Screening:** new vs current version on identical practice deals against all 64 opponents.
2. **Acceptance gate** (`lab/gate.py`): promising versions play **test deals never used for tuning**, against the
   whole field, plus 200 head-to-head pairings against the current best. A version ships only if it beats the
   current best; the rule was fixed in advance.
3. **Tournament simulation** (`lab/tournament.py`): the exact organiser format, several times.
4. **Real sandbox:** Docker matches at half a CPU core with the 2-second limit, and a validator run on a fresh
   clone of the GitHub repo (exactly what the organisers collect).

## 6. What makes a result accurate or not?
- **95% confidence intervals.** "74.0% [72.9-75.1]" means the true value is almost certainly in that range. If two
  versions' ranges overlap, the difference is noise. Example: v3 scored 73.8% vs 74.0% for v2.1 on test deals, a
  noise-level gap, and lost the head-to-head 47.5% [42.7-52.4], so it was **not** shipped even though it beats the
  strongest public bot by 4-7 points.
- **A rule fixed in advance**, not adjusted after seeing the results.
- **Reproducibility.** We found that the `eval7` library seeds its random generator from the clock, which made
  matches impossible to replay. The bot now reseeds it every decision from the sandbox's seeded generator.
- **Honest rejections.** 7 of today's 9 ideas were measured and rejected (logged in `lab/EXPERIMENTS.md`); a method
  that never says no isn't measuring anything.

## 7. How did you use AI agents (agentic practice)?
- We used Claude Code with specialised agents, each with a narrow job and written rules
  (`.claude/agents/perf-coder.md`, `.claude/agents/strategist.md`):
  - a **performance agent** built the tournament simulator and the profiler, and measured that the bot uses only
    ~10% of its time budget and that 8% of close decisions flipped on simulation noise;
  - a **strategist agent** probed public bots for common weaknesses (8 of 13 hard-code the big blind at 100;
    many fold at fixed bet-size "cliffs") and ranked ideas.
- **Agents propose, data decides.** Every idea went through the same screening and gate. Several agent ideas were
  tested and rejected (blind-level decay, bigger value bets, survival margins).
- One shared log (`lab/EXPERIMENTS.md`) keeps both teammates and all agents working from the same facts.
- The agents work inside the rules: they never read other teams' code from this event, and the bot never calls an
  AI or the network.

## 8. Why no machine learning model?
- **Data mismatch:** the only data in our exact format (heads-up no-limit, ACPC competition logs) is a 20 GB
  archive that wasn't available in time to train and validate.
- **Short matches:** with 25-80 hands per match, a pre-trained model mostly predicts the "average" opponent, which
  our Bayesian priors already encode, and the live updates already use each observation efficiently.
- **Risk:** an unvalidated model added in the last hour could make the bot weaker or slower; a timeout folds the hand.
- Our "learning" is the Bayesian opponent model, which updates live every hand.

## 9. How good is the bot?
- Tournament simulation (40-bot field, test deals): **qualified 1st in 7 of 7 simulated tournaments, won the
  final in 6 of 7.**
- Match win rate: 98-100% against simple bots (calling stations, the kit's template), 76-92% against the public
  bots from the previous hackathon, 55-77% against the strongest styles (most of those pairings are 1-1 draws
  decided by the cards).
- 0 crashes and 0 timeouts over 128,000 matches; real-sandbox think time about 10 ms per decision.

## 10. What's missing / next steps?
- **Bet sizing per opponent.** Bet sizes are mostly fixed. Next: learn each opponent's fold rate by bet size and
  bet just above its threshold.
- **CFR (counterfactual regret minimisation)**, the algorithm behind Libratus and Pluribus: compute a near-
  unbeatable strategy for a simplified game offline and ship it as a lookup table, then solve subgames live
  within the unused 90% of the time budget.
- **Multi-street planning and balance:** check-raises and a mix of hand strengths behind each bet size, so strong
  opponents can't read our bets.
- **ACPC data:** fit better starting values for the opponent model from millions of heads-up hands.
