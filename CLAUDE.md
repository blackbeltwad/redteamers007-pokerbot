# MISSION: build the best heads-up NLHE bot for the IEEE uOttawa × LARUS poker hackathon

Read `README.md` first (event rules, `game_state` schema, sandbox limits, submission steps). This file is the operating manual. Follow it every session.

You are building two separate things, **from scratch**:
1. **Your own testing lab** (`lab/`): a fast, rigorous way to play huge numbers of matches against many opponents, past datasets and our own earlier versions, and to return analytics.
2. **The competition bot** (`my_bots/<team_name>/`): the thing that gets submitted.

Design both yourself. Don't wait for anyone to hand you a framework. The lab is the main advantage here, so build it first and build it properly.

## 0. Ground rules (non-negotiable, we win hon[118;1:3uourably)

**The shipped bot must obey the sandbox rules.** Python 3.10 stdlib + eval7, numpy, scipy, treys, scikit-learn only. No network or LLM calls, no file writes, no subprocess/os.system, no threads or background work, no eval/exec/compile/`__import__`, no reading other bots' code/cards/runner memory, no collusion. Data files only in `data/` (≤200 MB, no `.py`), read at import time only. 2 s per decision, 0.5 CPU core, 768 MB RAM. Breaking these removes us from the tournament.

**The lab is unrestricted.** It runs on our machine and is never submitted. It may use any library, all CPU cores, the network, other teams' public repos and datasets.

**Integrity:**
- Other teams' public bots and datasets are sparring partners and research only. Don't copy their code into our entry. Ideas we adopt get re-implemented by us, and we must be able to explain every part of our bot at the judged evaluation.
- Respect licences on anything downloaded. Never report numbers as better than they are.
- Never edit `pokercore/` (it is replaced by the organisers' code).
- Only `my_bots/<team_name>/` is collected. Everything else can change freely.

## 1. What we are optimising

1. **Primary: win matches.** Qualification is a round robin of *duplicate pairs* (same cards, seats swapped) of freezeout matches. Score is wins, not chips. The top 4 records go to a knockout bracket ($150/$100/$75/$75). Winning by 1 chip counts the same as crushing the opponent, so optimise reliability and win probability, not margin.
2. **Secondary: cheap side prizes** ($50 each, measured from qualification logs): *biggest bluffer*, *lowest winning showdown*, *most won off 7-2*, *biggest comeback*. Judged ($75 each): best exploitative strategy and best game-theoretic strategy. A clean "sound baseline + exploit layer" with readable code and debug output is what we want to be able to explain.
3. **Never trade primary equity for a side prize** unless the lab shows it's free. Shoving 72 to farm that prize risks match losses, so skip it unless it costs nothing.

Game structure: 10,000 chips each, blinds 25/50 rising every 20 hands (antes from hand 101), so stacks are ~33bb by hand 100 and ~10bb by hand 160. Most matches end between hands 100 and 200, so the late game is effectively **push/fold**, where many bots are weak.

## 2. Build your own lab

Required capabilities, in priority order:

1. **Duplicate-pair match runner.** The unit of measurement is a pair: the same seed played twice with the seats swapped, using tournament blinds (`structures.parse("standard", 10000)`) in freezeout mode. Report match win rate with a confidence interval (e.g. Wilson), WW-D-LL pair records, average hands, and chip results.
2. **Speed.** Use all cores. Playing through `play.py`/`BotProcess` spawns a subprocess per bot, which is slow. Build an in-process seat (subclass `pokercore.seats.Seat`, call the bot's `decide()` directly) and play matches via `pokercore.table.play_match` with your own event sink. Load each bot module fresh per match, since module-level state must last exactly one match, as in the real sandbox.
3. **Fidelity to the real sandbox.** Seed `random` and numpy per decision the way `pokercore/sandbox/runner.py` does, so matches replay exactly. Time every decision and emulate the half-core limit (e.g. multiply local time by ~2), treat over-limit decisions as folds, and count timeouts and exceptions. Run the real Docker path (`make sandbox`, `play.py --docker`) periodically to confirm your fast path matches.
4. **Analytics.** Per matchup and overall, for us and for the opponent: VPIP, PFR, 3-bet %, fold-to-3bet, c-bet %, fold-to-bet by street, aggression factor, showdown win %, all-in frequency, bb/100, think-time mean and p99. Also dump event logs so the biggest losing hands (cards, board, our `debug` output) can be inspected. Add counters for the side prizes (bluff chips per 1,000 hands, 7-2 chips won per deal, weakest winning showdown, lowest chip share in a won match).
5. **Regression gate.** A single command that runs a candidate against the previous best and the opponent set on **fixed hold-out seeds** (never used while developing), and prints PASS/FAIL under the rules in §5.
6. **Opponent set.** Build your own diverse sparring partners: standard archetypes (calling station, maniac, nit, tight-aggressive, loose-aggressive, over-folder, shover, random, trapper), a large set of randomly-parameterised bots to test generalisation, other kit bots, and later the dataset-derived archetypes and external bots from §4. Also build **exploiter bots** designed to attack our known tendencies.
7. **Self-play and versioning.** Snapshot each accepted bot. Always test candidates against previous versions, and support round-robin leagues.

Engine facts you will need (verify them in `pokercore/`): the deck for each hand is derived from the match seed and hand number, not from the seats, so the same seed with swapped seats is a true duplicate. The table accepts any object implementing the `Seat` interface. eval7 only builds on Python 3.10 in the kit's setup (it may install on newer Pythons, but validate on 3.10). Keep an eye on single-core machines: long jobs should be run detached and polled.

Before trusting the lab, sanity-test it: your bots should beat a calling station and random bots easily, duplicate pairs of identical bots should come out near 50%, and fast-path results should agree with `play.py --docker` on a few seeds.

## 2b. The loop (how lab and agent divide the work)

Once the lab exists, it only ever adds testing capability. It never decides anything.

- **The user's computer runs the matches.** The agent launches runs (detached, using all but one core), and they keep going while the agent does other work. Long runs write progress to a file and are resumable, so a crash or closed terminal doesn't lose hours.
- **Every run writes machine-readable output** to `lab/results/<timestamp>_<label>/`: `summary.md` (the table the agent reads first), `results.json` (per-pair and per-match data), and hand/decision logs for drill-down. Analysis never requires re-running a test.
- **The agent reads the analytics, decides what to change, and edits the bot.** The lab does not touch `my_bots/`. The bot does not touch the lab.
- **Cycle:** read last results, form one hypothesis about a leak, change the bot, snapshot it, run screening, run the gate on hold-out seeds if it looks good, log the outcome in `lab/EXPERIMENTS.md`, repeat.
- Adding a new capability (a new external-bot adapter, a dataset-derived opponent set, a new statistic) is just extending the lab. It must not change how existing results are computed, so old and new numbers stay comparable. If a change to the lab does alter results, record that in the log and re-baseline.

## 3. Build order

1. Environment: Python 3.10, `make install`, `make validate`, one `--docker` run. Record real think times.
2. Lab core: runner, in-process seat, statistics, a first opponent set. Sanity-test it (above).
3. A simple, correct baseline bot from `bots/template`, to give the lab something to measure.
4. Analytics, regression gate, exploiter bots, adapters and dataset pipeline (§4).
5. Only then iterate on strategy using the loop in §5.

## 4. Testing against outside bots and datasets

**Other hackathon bots (e.g. MIT Pokerbots winners, other kit bots).** Different competitions use different engines and sometimes different game variants. Never assume a repo plugs in.
- For each external repo, write an adapter under `lab/adapters/<name>/` exposing `decide(game_state)` in *our* format and translating to and from the foreign API (card formats, "raise to" vs "raise by", blinds, any variant rules). Run foreign code in-process in the lab only. It never goes in `my_bots/`.
- **Validate every adapter** before trusting it: it must beat a calling station and random easily, never produce illegal actions, and look sensible in a hand-by-hand replay. If a variant's rules can't be mapped faithfully, say so and exclude it instead of fudging.
- Sandbox-hostile bots (network, heavy dependencies, long think times): run with a generous time limit and label them benchmarks, not legal entries.
- Pin each external repo at a commit hash and record it in the experiment log.

**Datasets (hand histories, past tournament logs).** Ask the user once for the location and format. Then:
- Parse into per-player stats and cluster into archetypes. Generate sparring bots that match the clusters, so we test against realistic populations.
- Mine what the data is good for: preflop frequencies by stack depth, push/fold ranges at 5-20bb, sizing tendencies, showdown ranges to calibrate our opponent-range model.
- Bake learned tables into `my_bots/<team>/data/` (compact; JSON/npz; no `.py`). The shipped bot only reads them at import time.
- Hold out part of the data to confirm a learned table helps, rather than fitting noise.

**Self-play and exploit-hunting.** Run every candidate against earlier versions and the exploiter bots. If an exploiter beats us we have a hole to close. Prefer fixes that keep a sound baseline over fixes that only beat one personality.

## 5. Experiment discipline (this is what keeps us locked in)

- **One change per experiment.** Log each in `lab/EXPERIMENTS.md`: hypothesis, change, command, seeds, result with CI, decision (keep/revert), version snapshot name.
- **Develop on dev seeds, accept on hold-out seeds.** Never tune on the seeds used for the final accept/reject.
- **Common random numbers:** A/B tests use the *same seeds* for both versions so deal luck cancels.
- **Sample sizes:** ~30 pairs per opponent to screen, ≥100 pairs per opponent for any accept decision, and ≥200 pairs when comparing against our own previous version. Don't read tea leaves from small samples.
- **Accept a change only if** (a) vs the previous best it wins ≥50% on hold-out with the point estimate up, (b) no opponent class regresses beyond noise, (c) zero errors/timeouts and p99 think time ≤ 600 ms at the half-core emulation, and (d) `make validate` passes.
- **Don't overfit the opponent set.** Watch the randomly-parameterised bots and dataset clusters. If the main set improves while those fall, revert.
- Snapshot every accepted bot so rollback is always possible.

## 6. Bot design principles (keep it explainable)

- **Sound baseline + exploit layer.** The baseline must be hard to exploit on its own (balanced-ish ranges, push/fold at short stacks, pot-odds-correct calls). The exploit layer adapts to measured tendencies from `match_action_log` (fold-to-bet, aggression, steal and 3-bet frequency, showdown cards from `show` entries) **with shrinkage**: smoothed priors, so it never over-adapts on small samples. Use the baseline until ~20-30 hands of data exist.
- **Timing is a feature.** Cache or precompute anything heavy into `data/`. Every code path needs a cheap fallback when time is low. A timeout is a fold. `decide()` must never raise.
- Log everything decision-relevant in the `debug` field (equity, estimated opponent range, thresholds, chosen line), so leaks are found in logs and not guessed.
- Likely highest-value areas: push/fold accuracy at 5-20bb including antes; preflop defence and 3-bet ranges vs different opening frequencies; opponent range estimation; river value and bluff-catch decisions; bet sizing and mixing so we aren't readable; side-prize shaping only where free.

## 7. Submission readiness (do this early, then again before the deadline)

- Team folder `my_bots/<team_name>/` with `bot.py` (+ `data/`), named exactly as on the submission form (lowercase letters, digits, underscores). Only this folder is collected.
- Submit the form early (team name + repo link) and keep pushing.
- **The repo must be public and `main` must hold the final bot at the deadline.** Later pushes don't count.
- Before the freeze: validate on Python 3.10, run once with `--docker`, re-run the regression gate, push, then verify in a fresh clone that `make validate BOT=my_bots/<team>` still passes.
- Freeze changes well before the deadline. A late untested change is the most common way to lose.

## 8. How to work (agentic engineering standards, applied by default)

**Autonomy and judgment**
- Be autonomous: build, run experiments, read results, decide, iterate. Ask the user only for what you can't discover (dataset location, external repo URLs, team name, deadline). Batch questions into one message.
- Before any non-trivial task, write a short plan (goal, steps, how you'll verify). Then execute. If a plan step fails twice, stop and re-plan instead of thrashing.
- Define "done" before you start, as a check you can run (a test, the validator, the gate, a CI-bounded result). Never declare success on a claim. Show the evidence.
- Treat your own output as untrusted until measured. A change "that should help" is a hypothesis.

**Verification and safety**
- Test the lab before trusting it (§2 sanity checks), and re-run them after any lab change.
- Commit to git after every accepted change with a clear message, and tag accepted bot versions. Never leave the working tree in a state you can't roll back. Never force-push or rewrite history on `main`.
- Keep diffs small and single-purpose. Re-read your own diff before committing.
- Never ship an untested change to `my_bots/<team>/`. Every candidate goes through the gate first.

**Token and context discipline (the user is token-conscious: waste nothing)**
- **Never stream raw simulation output into the conversation.** Runs go detached and write to `lab/results/`. Read `summary.md` first, then drill down with `head`, `tail`, `grep`, or a small script that prints only what you need. Never `cat` a log or print per-hand data unless a specific hand is being debugged, and then print only that hand.
- Cap every command's output (`| head -50`). Print tables, not walls of text. Read only the files and line ranges you need, and don't re-read files you already have in context.
- Poll long runs sparingly (sleep for a sensible interval, then check one progress line). Don't poll in a tight loop.
- Prefer one script that does a whole analysis over many separate tool calls.
- Put durable knowledge in files (`lab/EXPERIMENTS.md`, code comments, `summary.md`), not in the conversation, so a fresh session loses nothing.
- Keep your replies short: a results table with CIs, the decision, the next step. No restating the task, no narrating routine steps.
- **Tell the user when to manage context.** Suggest `/clear` when a task is finished and the next is unrelated (state lives in `lab/EXPERIMENTS.md`). Suggest `/compact` before they step away from a long session. Suggest `/rewind` when the last few turns went nowhere. Don't switch model or effort level mid-task, because it breaks caching, and suggest changing them only at a session start. Mention `/usage` if usage looks high.
- Don't spawn sub-agents or parallel agent teams unless a task is clearly parallelisable and large. Each one has its own context cost.
- Optimise for fewer, better-directed rounds: gather what you need, then act. Don't take a step just to look busy.

**Priorities**
- Do the unglamorous things first: lab correctness, analytics, validation, Docker. A trustworthy measurement loop is the whole advantage.
- Keep `lab/EXPERIMENTS.md` current. It's the memory between sessions. At the start of any session, read it first (and only it, plus what the task needs).
- Say plainly when a result is noise, a test is too small, an adapter is unfaithful, or you're unsure. Honest uncertainty beats a confident wrong answer.
- Poker has variance and nothing guarantees a win. The job is to make the best bot we can *measure*, and to make it reliably legal and fast.
