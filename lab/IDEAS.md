# IDEAS.md: contrarian edges (2026-11-21, strategist session)

Scope: legal edges that most teams won't build, ranked by expected effect on **winning qualification
pairings and the KO**, then side and judged prizes. Nothing here edits `bot.py`. Each idea comes with
a knob or experiment to run on a snapshot copy (`lab/snapshot.sh vX`, then edit the snapshot or add a `TUNE` key).

Baseline (lab/results/1121_143959_m_full_v21, v2.1, dev, 20 pairs/opp): 76.2% match win, pairs WW-D-LL
731-490-59. **38% of pairs are draws** and the median match lasts about 70 hands (levels 3-4, before antes).
Against `ext` (13 bots) the mean is 83.9%, WW-D-LL 181-75-4.
Our postflop sizing is fixed: value bets are 0.6 pot (0.75 when eq > 0.8), all bluffs are 0.6 pot (bot.py:508-518),
and raises are 2.5x (bot.py:529). Opponent stats are pooled over the whole match, with no bet-size buckets and no blind level
(bot.py:85-95).

## Evidence gathered this session

### E1. Static response probe (scratchpad `idea_probe.py`, 60 random hands per cell, about ±12 pp)
Each bot is the button in a single-raised pot (2.5x open, call), facing our flop lead of X times the pot. The cells show
Fold%/Call%/Raise%. The last two columns are the bot in the BB facing a 2.5bb SB open at the **same 50bb depth**,
at level 1 (25/50, 2,500 stacks) and level 4 (100/200, 10,000 stacks). A bot that reads `blinds` should not change between them.

| bot | 0.2p | 0.33p | 0.5p | 0.75p | 1.0p | 1.5p | 2.5p | all-in | BB fold L1 | BB fold L4 |
|---|---|---|---|---|---|---|---|---|---|---|
| e_txn_cfr/floorfix/mybot | 8/88/3 | 24/62/13 | 20/69/10 | 42/52/5 | 42/46/11 | 52/39/8 | **93**/6/0 | **98**/1/0 | 60 | 48-55 |
| e_advit_strong | 48/50 | 46/43 | 51/45 | 60/36 | 55/40 | 68/26 | 83/15 | 86/13 | 61 | 51 |
| e_tumble_q1 | 25/71 | 38/45 | 35/53 | 51/43 | 51/35 | 68/20 | 76/16 | 70/30 | **91** | **46** |
| e_tumble_dutch / e_gunslinger | 21/73 | 38/45 | 38/51 | 53/40 | 51/38 | 66/23 | 80/13 | 81/18 | 28 | 15 (gunslinger 3-bets 20% at L1, 35% at L4) |
| e_opp_modeler | 28/68 | 38/46 | 31/56 | 50/45 | 50/40 | 63/25 | 76/16 | 68/31 | 66 | 46 |
| e_adapt_exploit | 5/90 | 21/60 | 21/66 | 45/48 | 41/46 | 56/33 | 70/23 | **98**/0 | **95** | **60** |
| e_range_mc | 28/68 | 35/50 | 38/51 | 40/51 | 45/43 | 38/51 | 53/41 | **98**/1 | 66 | 65 |
| e_lomaan | 56/33 | 55/33 | 55/30 | 61/25 | 55/30 | 61/16 | 80/10 | 95/5 | 78 | 68 |
| e_langchen | 10/78 | 15/73 | **86**/0 | 86/0 | 83/0 | 85/0 | 85/0 | 10/**90** | 86 | 83 |
| e_atharva | 8/91 | 23/76 | 28/71 | 50/50 | 48/51 | 53/46 | 70/30 | 73/26 | **0** | **0** (max think 1,372 ms *locally*) |
| llm_boilerplate_a | 46/53 | 41/58 | 48/51 | **93**/6 | 83/16 | 88/11 | 86/13 | 95/5 | 95 | 86 |
| pot_odds_loose | 46/53 | 41/58 | **88**/11 | 93/6 | 83/16 | 88/11 | 86/13 | 100/0 | 96 | 91 |
| chart_standard | 46/53 | 41/58 | 48/51 | 48/51 | 45/55 | **88**/11 | 86/13 | 95/5 | 95 | 86 |
| mc_balanced (tumbleweed "strong") | 71/23 | 70/20 | 73/23 | 80/13 | 76/13 | 81/15 | 88/6 | 90/10 | 75 | 65 |

What the probe shows:
1. **The fold curves are cliffs, not slopes.** The MC/equity bots fold about the same share from 0.33 to 1.5 pot, then
   80-98% at 2.5 pot or all-in. The rule-based bots (LLM boilerplate, pot-odds, chart) have a hard cliff at a fixed pot fraction:
   0.5p, 0.75p or 1.5p. In llm_boilerplate_a the rule `owed <= pot*0.4`, where `pot` already includes our bet, means it calls
   with a pair up to 0.667p and folds above that (`lab/ext/TimoJanssen1_tumbleweed/field/mid/llm_boilerplate_a/bot.py:285-290`).
2. Our fixed 0.6p sits in the worst place on these curves. As a bluff it folds no more hands than 0.33p and risks about twice
   as much. As a value bet it gets called no more often than 1.0p and wins less.
3. **Hard-coded blinds are real and large.** At the same 50bb depth, a bot's fold-to-open swings by 30-45 pp between
   levels: tumble_q1 91 vs 46, adapt_exploit 95 vs 60.
4. Some bots have single-sized holes. langchen folds 86% to a half-pot bet but **calls 90% of all-ins**. atharva never folds
   its BB to a 2.5bb open.

### E2. Sizing A/B vs `ext` (dev seeds, same seeds as m_full_v21; variants are scratchpad copies of v2_1)
Opponents: gunslinger, txn_floorfix, advit_strong, tumble_dutch. 8 pairs each, so 64 matches per arm: **small sample, direction only**.
The machine was shared with a 7-worker `m_f6C` run, which explains the 2-3 hero timeouts per arm.
Base numbers are the same seeds taken from m_full_v21 (scratchpad `idea_base.py`).

| arm | win% | WW-D-LL | bb/100 gun / txn_ff / advit / dutch | bluff chips/1000h |
|---|---|---|---|---|
| base v2.1 (0.6/0.75 value, 0.6 bluff) | 72 | 15-16-1 | 35.6 / 6.7 / 14.9 / 38.9 | - |
| vA: value 1.0/1.3p | 70 | 13-19-0 | 16.0 / 7.1 / 9.7 / 19.8 | 10,465 |
| vB: vA + bluffs at 0.33p | 69 | 13-18-1 | 17.4 / −8.4 / 7.5 / 30.0 | 6,523 |
(results: lab/results/1121_151907_idea_s_vA, lab/results/1121_152256_idea_s_vB)

**Static upsizing is NOT free: it cost bb/100 against 3 of the 4 bots.** The probe in E1 deals the bot a *random* hand. In a
real hand the bot has already filtered its range preflop, and our value threshold (eq ≥ 0.62 vs range, bot.py:506-510) includes
medium hands that a bigger bet only gets called by better hands. Also, `bet()` turns anything ≥ 0.45 stack into an all-in
(bot.py:545), so large fractions often become shoves. Conclusion: the cliffs are real, but they have to be **learned per
opponent from real responses**, not hard-coded from the probe. That is idea 2 below. The 0.6p default stays.

### E3. Catalogue of bugs and blind spots in hackathon bots (13 public Fullhouse 2026 bots plus the tumbleweed "field")
These repos are public and use this same engine, so **expect forks and clones of them in tonight's field**. They are the
first thing a search for "fullhouse poker bot" returns, and their bugs come along with them.

| # | bug / blind spot | where (examples) | legal exploit |
|---|---|---|---|
| B1 | `BB = 100` / `BIG_BLIND = 100` / `STARTING_STACK = 10000` constants used in decisions (8 of 13 bots) | txn cfrbot/bot.py:41,493,512; advit strong/bot.py:38,578,590; gunslinger/bot.py:28,533,550; atharva/bot.py:15,643-655; adaptive_exploiter/bot.py:29,575,622; lomaan/bot.py:96-103,1047 | Open sizes are fixed in chips: advit opens 220 chips, which is 4.4bb at level 1 and a min-raise at level 4+. Push/fold thresholds are also in chips (atharva: shove only below 1,200 chips; lomaan: "shove or fold" below 1,000 chips), so they play deep-stack poker at 10-20bb. Idea 1. |
| B2 | Hand strength from `eval7.handtype`, so board pairs count as the bot's own pair, and a double-paired board is "Two Pair" that always calls | llm_boilerplate_a/bot.py:281-290; pot_odds_loose/bot.py:244-256; chart_* | On paired boards, value-bet thinner and bigger. Never bluff a double-paired board: these bots call any size there. |
| B3 | Pot-fraction thresholds where `pot` already includes the bet, giving a hard cliff at a fixed size | llm_a:288 (cliff 0.667p), pot_odds_loose:252-256 (`pot_odds<=0.3` gives a cliff at 0.43p) | Bluff just above the cliff and value-bet just below it (idea 2). |
| B4 | Equity vs a random hand, not vs our betting range | atharva `_equity` bot.py:322-344; most MC bots | They call large value bets with "50% vs random" hands, but E2 shows this does not pay statically. Size up only where the learned curve says so (idea 2). |
| B5 | Built for last year's format (400-hand chip-delta scoring, 6-max) | lomaan/bot.py:1500-1512 (`final_hands = hn >= 388`, "scoring is cumulative chip delta") | They don't adjust to freezeout or rising blinds, which reinforces B1. |
| B6 | Opponent stats count posts, antes and `show` entries as actions, which dilutes fold% and raise% | opponent_modeler/bot.py:166-186; atharva `_opp_raise_freq` bot.py:569-580 (only blinds and folds are skipped) | Their read of us is biased toward "passive", so they under-fold to our aggression less than they should. Small effect. |
| B7 | Slow pure-Python MC | atharva probe: max 1,372 ms on one local core, which is over 2 s at 0.5 CPU, so the decision times out and the bot folds | Bet into them on every street: every extra decision in a big pot is another chance of a timeout fold. Free, and our policy already does it. |
| B8 | Stats from `match_action_log` alone with no own memory: 200 entries is only about 20-25 hands with posts | atharva uses `ml[-100:]`, about 10 hands (bot.py:572) | Their read of us is a 10-25-hand sliding window, so our image can be reset by switching gears every level. Low priority. |

---

## Ranked ideas

### 1. Blind-level-aware opponent model plus a "hard-coded BB" detector
- **What:** (a) key preflop opponent stats (`sb_open`, `bb_fold_open`, `bb_3bet`, `fold_to_3bet`) by blind level, or decay them
  hard (×0.3) at each level change. (b) Flag an opponent as `chip_sizer` when its open size *in chips* stays the same across
  levels (for example 220 or 250 chips at both 50 and 200 bb), i.e. its open/bb ratio moves with the level. Against
  `chip_sizer` at level ≥3: their opens are min-raises with a wide range (3-bet and defend wider), and their push/fold logic
  is off by the BB ratio (they play "deep" at 10-20bb), so reshove wider. At level 1 their opens are 4-6bb: tighten
  defence and steal relentlessly, since they fold 91-95% to a 2.5bb open there (tumble_q1, adapt_exploit).
- **Why others won't:** almost every team's own bot assumes the blinds never change. Nobody models that *the opponent's*
  behaviour changes when the level does.
- **Evidence:** B1 (8 of 13 public bots, file:line in E3). E1 BB fold-to-open at the same depth: tumble_q1 91 vs 46,
  adapt_exploit 95 vs 60, opp_modeler 66 vs 46, gunslinger 3-bet 20 vs 35. Our model pools levels (bot.py:85-95), so it
  learns a level-1 opponent and then plays that read at level 3.
- **Impact:** medium-high. Every level change hands us a wrong model for about 10 hands, and matches cross 3-4 levels.
  Guess: +2-4 pp against the ext-like part of the field, and nothing changes against correct bots.
- **Cost/risk:** low (bookkeeping in `_digest_hand`, a `blinds` field per hand from the `big_blind` post amount).
- **Experiment:** add knob `lvl_decay` (1.0 = off, 0.3 = decay). `python -m lab.run --hero "lab/snapshots/vX::lvl_decay=0.3" --opps ext,core --pairs 30 --label lvl`.
  To check the detector offline, re-run `idea_probe.py` with `pre_state` at several levels.
- **Why #1:** the evidence for the bug is the clearest of anything here (30-45 pp swings), the cost is low, and it can't hurt
  against bots that read `blinds` correctly.

### 2. Learned bet-size response curves: "cliff sniping" (highest ceiling, but the static version measured NEGATIVE)
- **What:** keep fold/call/raise counts per opponent by our **bet-size bucket** (≤0.4p, 0.4-0.9p, 0.9-1.7p, >1.7p/all-in).
  Only once a bucket has data (≥6 observations, shrunk to the current 0.6p behaviour), choose the size that maximises
  EV: bluffs EV = f·pot − (1−f)·size, value EV from call% × size. Apply it to **bluffs first**, since bluff EV needs only the
  fold rate. Value sizing also needs to know what calls, so start with value up-sizing only against measured stations and
  "calls all-in" types (langchen: calls 90% of all-ins, folds 86% to 0.5p).
- **Why others won't:** the usual hackathon bot has one or two fixed sizes. Teams that model opponents track VPIP/AF, not
  response *as a function of our size*.
- **Evidence:** E1 shows the cliffs: txn folds 52% at 1.5p and 93% at 2.5p, adapt_exploit and range_mc fold 98% to all-in,
  and the rule bots have exact cliffs at 0.5p, 0.67p and 1.5p (B3). Bluff maths vs txn at 2.5p: 0.93 − 0.07·2.5 = +0.76 pot,
  against about −0.1 pot for a 0.6p bluff that gets 20% folds. **But E2: static value up-sizing cost bb/100 against 3 of 4 ext bots**
  (gunslinger 35.6 → 16.0, dutch 38.9 → 19.8). The probe deals random hands, so it overstates what a real range does. Don't ship
  any size change without a gate.
- **Impact:** potentially the largest (postflop fold lines are −20/−21/−20 bb/100 in m_full_v21), but unproven. Guess:
  +2-5 pp against equity and rule bots if the learned version works.
- **Cost/risk:** medium-high (stat table plus size chooser in `postflop()`, about 2 h). Risk: polarised overbets get
  exploited by strong bots, so cap overbet bluffs at about 1/3 of overbets.
- **Experiment:** first the cheapest single piece, overbet bluffs only (knob `bsize_big=2.5`, used on the bluff line only when
  the learned fold% at >1.7p is ≥ 0.75): `python -m lab.run --hero "lab/snapshots/vX::bsize_big=2.5" --opps ext,core,exploit --pairs 30 --label obluff`.
  Watch `x_overbet` and `x_aggro`, and read the `flop:bluff` and `turn:bluff` lines with `lab.tools.lines`. Then `lab.gate`.

### 3. Duplicate-diff analysis: turn draws into WW (lab tool, no bot change)
- **What:** for every D or LL pair, line up the two matches by `hand_num`. Hand N has the same cards in both, with seats
  swapped, because `hand_seed = derive_seed(seed, "hand", hand_num)` (pokercore/table.py:191) does not depend on earlier
  actions. For each hand compute (our chips with cards X) − (opponent's chips with the same cards X). Rank the hands where the
  opponent's line did better with our cards, grouped by our `dbg.line`. These are the leaks that cost pairings, measured
  against a real alternative line instead of a model.
- **Why others won't:** it needs the duplicate insight plus logging. It is also the methodology behind AIVAT/duplicate
  evaluation in poker-AI research, which makes it a strong judge story.
- **Evidence:** 490/1280 pairs are draws (38%). WW versus D decides qualification. Stacks diverge, so restrict the comparison
  to hands where both matches still have effective stacks within ±30%.
- **Impact:** indirect but large. It finds which lines to fix, where `lines.py` only says which lines lose chips.
- **Cost/risk:** about 1 h of tooling. `lab.run` currently keeps only the 2 worst hands per match (`--keep-hands 2`,
  lab/run.py:206), so the run needs `--keep-hands 999` and the `bb < -15` filter disabled.
- **Experiment:** `python -m lab.run --hero my_bots/redteamers007 --opps ext,core --pairs 20 --keep-hands 999 --label dd`,
  then a new `lab/tools/dupdiff.py <dir>`.

### 4. Explore at level 1, exploit at levels 3-5
- **What:** in hands 1-20 (blinds 25/50) deliberately randomise our open sizes (2x/2.5x/3x/limp) and postflop sizes
  (0.33/0.75/1.5/2.5p) to fill the idea-2 buckets fast. After that, play the argmax. Level-1 pots in chips are about 1/4 of
  level-4 pots for the same bb counts, so mistakes made while exploring are cheap in a freezeout counted in chips.
- **Why others won't:** a bot that plays worse on purpose is counter-intuitive, but chips are chips and most chips change
  hands later (median match about 70 hands).
- **Evidence:** match length (m_full_v21 median about 70 hands). E1 shows every bot has a different cliff, so a fixed default
  cannot hit them all.
- **Impact:** amplifies idea 2, roughly +1-2 pp on top of it. Classification by hand 20: chip_sizer (1b), cliff location
  (2), station vs folder (fold to 0.33p), "calls all-in only" (langchen).
- **Cost/risk:** low once idea 2 exists. Only worth doing after idea 2.
- **Experiment:** knob `explore_hands=20`. Compare to `explore_hands=0` on `--opps ext,core,dataset --pairs 30`.

### 5. Edge-aware risk posture (duplicate freezeout + round robin)
- **What:** once our measured bb/100 against this opponent is strongly positive (after about 30 hands), decline marginal
  deep-stack all-ins (+0.04-0.08 extra equity needed for >40bb stack-offs) because we expect to win the match anyway. Against
  opponents where we are flat or behind (KO stage, strong bots), do the opposite and accept +EV flips.
- **Why others won't:** most bots maximise chip EV per hand. In freezeout what matters is P(win match), and against a weaker
  opponent that rewards lower variance.
- **Evidence:** WW-D-LL 731-490-59: we rarely lose both, but many pairs are 1-1 because one match was lost to a single big pot.
  There is already a static deep-stack margin on preflop all-in calls (EXPERIMENTS v1, item 4). It is not conditioned on edge
  and not applied postflop.
- **Impact:** medium on qualification points (converting D into WW). It also matters in the KO, where the posture flips.
- **Cost/risk:** low. Risk: the edge estimate is noisy early, so shrink it toward a prior.
- **Experiment:** knob `edge_margin` (0, 0.04, 0.08). `python -m lab.run --hero "lab/snapshots/vX::edge_margin=0.06" --opps core,rand20,ext,dataset --pairs 40 --label edge`,
  and read WW and LL, not win%.

### 6. Board-texture traps for `handtype` bots (B2)
- **What:** on paired boards (and especially two-paired or trips boards), value-bet anything above the median of our range
  large or all-in, and never bluff. Rule bots call any size with "Two Pair"/"Trips" that the board gave them
  (llm_boilerplate_a/bot.py:281-284: `call` with no size check).
- **Why others won't:** it only pays against naive bots, and only a team that has read naive bots knows it exists.
- **Evidence:** B2. Over a match, about 17% of flops are paired and the turn/river pair the board often.
- **Impact:** medium against weak and mid bots, which are the bulk of the round robin. Zero against strong bots.
- **Cost/risk:** low if gated by an opponent flag (calls big bets on paired boards, from showdowns).
- **Experiment:** add `field/mid/*` and `field/weak/*` from tumbleweed as set `mid` in `lab/opponents/sets.py`, then
  `--opps mid,ext --pairs 20`.

### 7. 7-2 prize: the metric only counts wins
- **What:** chips won per 7-2 *dealt*, and losses are ignored. So: always open-raise 7-2 from the SB, raise it vs a limp in
  the BB, always c-bet, and at ≤13bb always shove it. Fire the big (cliff) barrel with it when the board helps.
- **Why others won't:** most teams ignore side prizes. The few who try will shove 7-2 at 100bb and give up match equity.
- **Evidence:** ours is 43 chips per 7-2 dealt (2,348 dealt) in m_full_v21. We see about 1 per match, so we reach the 30 needed.
  Cost estimate: opening 72o from the SB instead of folding costs about 0.1-0.2bb each time (well under 0.5 pp of match
  equity), and 72o is close to the Nash SB push range below about 6bb anyway.
- **Impact:** a real chance at $50 for very little match equity. The number to beat is unknown. Track the `7-2 won/dealt`
  counter in summary.md.
- **Experiment:** knob `seven_two=1` in a snapshot, then `lab.gate` to make sure it is neutral, and read the side counters.

### 8. Biggest-bluffer and lowest-winning-showdown, nearly free with idea 2
- **Bluffer:** "chips won" is in chips, not bb, and needs <40% equity vs random at the time of the bet. So (a) put the bluff
  frequency where pots are big in chips (levels ≥3), (b) use overbet bluffs at the cliff (idea 2), which win bigger pots,
  (c) choose pure-air candidates for big bluffs, since draws above 40% vs random don't count. Ours: 7,513 chips/1000h.
- **Lowest showdown:** must win ≥1,000 chips at showdown with a bet on the river, so a high-card win is the target. Against
  measured river over-bluffers (`bet_bluff` rate > 0.5: maniac, random-action and naive-aggressor types) call down with
  ace-high or king-high. Our river call threshold already uses equity; add a floor so that against these opponents any
  unpaired hand beating their shown bluffs calls. Our best so far is a pair of 2s.
- **Cost/risk:** about zero if gated on measured bluff rates.
- **Experiment:** add the knob, then `--opps core,exploit,mid --pairs 20` and read the side counters.

### 9. Make slow and fragile bots decide more often
- **What:** a timeout or crash folds the hand (README "Rules and limits"; runner.py `_BotTimeout` → fold). Against an opponent
  whose think time is near the limit (atharva: 1,372 ms on one local core, which is over 2 s at 0.5 CPU), bet on every street
  in medium and large pots instead of checking back, because each decision they face is another chance of a timeout fold.
  A timed-out `decide()` thread keeps running in the background (runner.py docstring), which steals CPU from their next decision.
- **Why others won't:** it needs the sandbox CPU model and a look at opponent code. It is legal: we only choose legal actions.
- **Evidence:** probe max think times (E1). The lab's in-process opponents never time out (`opp_errors` are empty in all 2,560
  matches), so the lab **cannot see** this effect. A docker run is needed: `python play.py my_bots/redteamers007 lab/ext/Atharva-Mansabdar_FullHouseHack26 --docker --seed 1 --log /tmp/a.jsonl`, then count opponent `error: timeout`.
- **Impact:** small to medium, and only against slow bots. We cannot see their think time live. A proxy is "opponent folds
  facing a bet where it would normally call", which we can't tell apart, so keep it as a passive bias (bet more vs unknown
  bots when it is close).
- **Cost/risk:** about zero.

### 10. Judged prizes: present both from the same bot
- **Best exploitative:** show the E1 table (fold curves per bot) and the B1-B8 catalogue, then the per-opponent adaptation
  (bucketed sizing, level-aware model, chip_sizer flag) with an A/B per idea: with the exploit layer on vs off, by opponent
  class, in bb/100 and WW. Judges value seeing the bot *find* the weakness, so show a per-hand debug trace of the cliff
  being learned on a live match.
- **Best game-theoretic:** with the exploit layer off (one constant, e.g. `EXPLOIT=0`), the base is Nash push/fold ≤13bb,
  range-vs-range preflop from the 169×169 matrix, range-weighted postflop MC, and MDF-style bluff/fold ratios. Show its
  results against the `exploit` set (x_minbet, x_overbet, x_aggro, x_allin, x_threebet) as a low-exploitability check, and
  self-play h2h. One codebase with a single dial is a clean story for both prizes.
- **Cost:** a 1-page doc plus 2 lab runs (`EXPLOIT=0` vs `1`). Ties in with HANDOFF step 5.

## Rejected or not worth it
- Re-testing 3-bet-defence bluff shares (H3 rejected, monotone decline). Idea 2 is a different angle: the error comes from
  *levels*, not from the re-raise range model.
- Image manipulation of window-only opponents (B8): the effect is small and hard to measure.
- Anything that uses another bot's process, cards or code tonight (forbidden), or deliberate timeouts on our side (folds).

