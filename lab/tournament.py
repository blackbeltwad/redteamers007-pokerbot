"""Monte Carlo simulation of the organisers' tournament (README "The tournament").

  python -m lab.tournament --hero my_bots/redteamers007 --field core,ext,dataset --rr 1 --tours 3 --workers 4
  python -m lab.tournament --hero snap:v2_1 --field core --rr 2 --tours 20 --seeds holdout --label v21

Format simulated (assumptions marked *):
  Qualification: full round robin of the field (hero + --field bots). Each pairing = duplicate pair of
    freezeout matches (same seed, seats swapped, standard blinds, 10,000 chips), exactly the match setup
    of lab/run.py (same MatchConfig, same InProcSeat seeding, seat names "hero"/"villain").
    Win both = pairing win (1 pt), 1-1 = draw (*0.5 pt*), lose both = 0. Repeated --rr times with fresh
    seeds. *Ties in points broken by individual match wins, then by a seeded coin flip.*
  Final: top 4 play a knockout, 1v4 and 2v3, then the final. Each KO match = one duplicate pair;
    *if 1-1, further pairs are played (max 5 pairs in total); if still level, the higher qualification
    rank advances.*
  Each of --tours tournaments uses fresh seeds: derive_seed("tour", seeds, tour, ...).

Output: lab/results/<ts>_tour_<label>/{summary.md, results.json, progress.txt}.
--verify N: replays N hero matches through lab.run.play_one and checks winner/hands are identical.
"""
import argparse
import json
import os
import queue
import random
import sys
import time
import traceback
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pokercore import structures  # noqa: E402
from pokercore.seeds import derive_seed  # noqa: E402
from pokercore.table import MatchConfig, play_match  # noqa: E402
from lab.inproc import InProcSeat  # noqa: E402
from lab.opponents.sets import resolve_opps  # noqa: E402
from lab import run as R  # noqa: E402

HERO_LABEL = "HERO"
MAX_KO_PAIRS = 5


class _NullLog:
    """Event sink that keeps nothing (play_match only needs emit + a writable .final)."""
    final = None

    def emit(self, t, **d):
        return None


def play_lean(task):
    """Worker: one freezeout match, same setup as lab.run.play_one but without hand stats.
    task = (key, seed, swap, spec_a, spec_b, tf). Seat A is named R.HERO, seat B R.OPP."""
    key, seed, swap, spec_a, spec_b, tf = task
    t0 = time.perf_counter()
    try:
        sa = InProcSeat(R.HERO, spec_a, derive_seed(seed, "bot", R.HERO), time_factor=tf, capture_debug=False)
        sb = InProcSeat(R.OPP, spec_b, derive_seed(seed, "bot", R.OPP), time_factor=tf, capture_debug=False)
        seats = [sb, sa] if swap else [sa, sb]
        cfg = MatchConfig(mode="freezeout", hands=1500, starting_stack=10_000,
                          structure=structures.parse("standard", 10_000), seed=seed)
        res = play_match(seats, cfg, f"t{'b' if swap else 'a'}", _NullLog())
        winner = next((r["bot"] for r in res["results"] if r["place"] == 1), None)
        ta, tb = sorted(sa.think), sorted(sb.think)
        return {"key": key, "swap": swap, "a_won": winner == R.HERO, "winner": winner, "hands": res["hands"],
                "a_to": sa.timeouts, "b_to": sb.timeouts, "a_err": sa.errors, "b_err": sb.errors,
                "a_p99": ta[int(len(ta) * 0.99)] if ta else 0, "b_p99": tb[int(len(tb) * 0.99)] if tb else 0,
                "a_max": ta[-1] if ta else 0, "wall": time.perf_counter() - t0}
    except Exception:
        return {"key": key, "swap": swap, "a_won": None, "winner": None, "hands": 0,
                "crash": traceback.format_exc()[-1500:], "wall": time.perf_counter() - t0}


# ---------------------------------------------------------------- tournament state machine
class Tour:
    """One simulated tournament. Emits tasks, consumes results."""

    def __init__(self, t, field, a):
        self.t, self.field, self.a = t, field, a
        self.n = len(field)
        self.points = [0.0] * self.n
        self.mwins = [0] * self.n
        self.pending = {}                 # key -> [result, result]
        self.qual_left = 0
        self.pair_log = []                # (phase, i, j, a_wins) a_wins in {0,1,2} or None on crash
        self.rank = None
        self.ko = {}                      # name -> state
        self.semis_winners = {}
        self.final_result = None
        self.done = False
        self.crashes = []

    def spec(self, i):
        return self.field[i][1]

    def pair_tasks(self, key, seed, i, j):
        self.pending[key] = []
        return [(key, seed, sw, self.spec(i), self.spec(j), self.a.tf) for sw in (False, True)]

    def start(self):
        tasks = []
        for r in range(self.a.rr):
            for i in range(self.n):
                for j in range(i + 1, self.n):
                    seed = derive_seed("tour", self.a.seeds, self.t, "rr", r, self.field[i][0], self.field[j][0])
                    tasks += self.pair_tasks((self.t, "q", r, i, j), seed, i, j)
                    self.qual_left += 1
        return tasks

    def on_result(self, res):
        key = tuple(res["key"])
        lst = self.pending[key]
        lst.append(res)
        if len(lst) < 2:
            return []
        del self.pending[key]
        for x in lst:
            if "crash" in x:
                self.crashes.append(x["crash"])
        if any(x["a_won"] is None for x in lst):
            aw = None
        else:
            aw = sum(x["a_won"] for x in lst)
        if key[1] == "q":
            _, _, r, i, j = key
            self.pair_log.append(("q", r, i, j, aw))
            if aw is not None:
                self.mwins[i] += aw
                self.mwins[j] += 2 - aw
                self.points[i] += {2: 1.0, 1: 0.5, 0: 0.0}[aw]
                self.points[j] += {0: 1.0, 1: 0.5, 2: 0.0}[aw]
            else:                          # crash: count as a drawn pairing
                self.points[i] += 0.5
                self.points[j] += 0.5
            self.qual_left -= 1
            if self.qual_left == 0:
                return self.start_ko()
            return []
        # knockout pair
        _, _, name, k, i, j = key
        self.pair_log.append((name, k, i, j, aw))
        st = self.ko[name]
        st["pairs"].append(aw)
        if aw in (0, 2):
            st["winner"] = i if aw == 2 else j
            st["decided_by"] = "pairs"
        elif len(st["pairs"]) >= MAX_KO_PAIRS:
            st["winner"] = i if self.qrank[i] < self.qrank[j] else j
            st["decided_by"] = "qual_rank"
        else:
            return self.ko_pair(name, i, j)
        return self.after_ko(name)

    def start_ko(self):
        rng = random.Random(derive_seed("tour", self.a.seeds, self.t, "tiebreak"))
        coin = [rng.random() for _ in range(self.n)]
        order = sorted(range(self.n), key=lambda i: (-self.points[i], -self.mwins[i], coin[i]))
        self.rank = order
        self.qrank = {b: r for r, b in enumerate(order)}
        top = order[:4]
        if self.n < 4:
            self.done = True
            return []
        return self.ko_pair("sf1", top[0], top[3]) + self.ko_pair("sf2", top[1], top[2])

    def ko_pair(self, name, i, j):
        st = self.ko.setdefault(name, {"i": i, "j": j, "pairs": [], "winner": None})
        k = len(st["pairs"])
        seed = derive_seed("tour", self.a.seeds, self.t, "ko", name, k, self.field[i][0], self.field[j][0])
        return self.pair_tasks((self.t, "ko", name, k, i, j), seed, i, j)

    def after_ko(self, name):
        if name == "final":
            self.done = True
            return []
        if self.ko.get("sf1", {}).get("winner") is not None and self.ko.get("sf2", {}).get("winner") is not None:
            a, b = self.ko["sf1"]["winner"], self.ko["sf2"]["winner"]
            if self.qrank[b] < self.qrank[a]:
                a, b = b, a
            return self.ko_pair("final", a, b)
        return []

    def summary(self):
        names = [f[0] for f in self.field]
        out = {"tour": self.t, "qual_order": [names[i] for i in self.rank],
               "points": {names[i]: self.points[i] for i in range(self.n)},
               "match_wins": {names[i]: self.mwins[i] for i in range(self.n)},
               "ko": {k: {"a": names[v["i"]], "b": names[v["j"]], "pairs": v["pairs"],
                          "winner": names[v["winner"]], "decided_by": v.get("decided_by")}
                      for k, v in self.ko.items()},
               "pairs": [[p[0], p[1], names[p[2]], names[p[3]], p[4]] for p in self.pair_log],
               "crashes": self.crashes[:3]}
        if "final" in self.ko:
            f = self.ko["final"]
            out["champion"] = names[f["winner"]]
            out["runner_up"] = names[f["j"] if f["winner"] == f["i"] else f["i"]]
        return out


# ---------------------------------------------------------------- reporting
def analyse(tours, names):
    n_t = len(tours)
    S = {b: {"rank_sum": 0, "top4": 0, "top2": 0, "win": 0, "pts": 0.0} for b in names}
    hero_rec = defaultdict(lambda: {"WW": 0, "D": 0, "LL": 0, "crash": 0})
    ko_rec = defaultdict(lambda: {"WW": 0, "D": 0, "LL": 0})
    knocked_by = defaultdict(int)
    missed_q_losses = defaultdict(int)
    hero_missed = 0
    for T in tours:
        for r, b in enumerate(T["qual_order"]):
            S[b]["rank_sum"] += r + 1
            S[b]["pts"] += T["points"][b]
            if r < 4:
                S[b]["top4"] += 1
        if "champion" in T:
            S[T["champion"]]["win"] += 1
            S[T["champion"]]["top2"] += 1
            S[T["runner_up"]]["top2"] += 1
        hero_q = HERO_LABEL in T["qual_order"][:4]
        hero_missed += not hero_q
        for ph, _, a, b, aw in T["pairs"]:
            if HERO_LABEL not in (a, b):
                continue
            opp = b if a == HERO_LABEL else a
            hw = None if aw is None else (aw if a == HERO_LABEL else 2 - aw)
            rec = hero_rec[opp] if ph == "q" else ko_rec[opp]
            if hw is None:
                rec["crash"] = rec.get("crash", 0) + 1
            else:
                rec[{2: "WW", 1: "D", 0: "LL"}[hw]] += 1
            if ph == "q" and not hero_q and hw == 0:
                missed_q_losses[opp] += 1
        for k, v in T["ko"].items():
            if HERO_LABEL in (v["a"], v["b"]) and v["winner"] != HERO_LABEL:
                knocked_by[v["winner"]] += 1
    rows = {b: {"mean_rank": s["rank_sum"] / n_t, "mean_pts": s["pts"] / n_t, "p_top4": s["top4"] / n_t,
                "p_top2": s["top2"] / n_t, "p_win": s["win"] / n_t} for b, s in S.items()}
    return {"bots": rows, "hero_qual_record": dict(hero_rec), "hero_ko_record": dict(ko_rec),
            "hero_knocked_out_by": dict(knocked_by), "hero_losses_when_missed_top4": dict(missed_q_losses),
            "hero_missed_top4": hero_missed, "tours": n_t}


def write_summary(outdir, an, meta, perf):
    n = an["tours"]
    L = [f"# Tournament sim `{meta['label']}`  hero={meta['hero']}  field={meta['field']} ({meta['n_bots']} bots)  "
         f"rr={meta['rr']}  tours={n}  seeds={meta['seeds']}  tf={meta['tf']}", "",
         "Assumptions: pairing win=1, draw=0.5, loss=0; qual ties -> match wins -> seeded coin; KO = duplicate "
         f"pairs until one bot wins a pair (max {MAX_KO_PAIRS}), then higher qual rank; 1v4, 2v3, final.", "",
         f"Throughput: {perf['matches']} matches in {perf['elapsed']:.0f}s = **{perf['mps']:.2f} matches/s** with "
         f"{meta['workers']} workers (mean match wall {perf['mean_wall']:.2f}s, {perf['hands_mean']:.0f} hands/match). "
         f"Crashes: {perf['crashes']}. Hero timeouts: {perf['hero_timeouts']}, hero p99 think worst match "
         f"{perf['hero_p99_worst']:.0f} ms (emulated).",
         "Slowest bots (mean wall s per match they play): " + ", ".join(f"{b} {w:.2f}" for b, w in perf.get("slowest_bots", [])),
         ""]
    h = an["bots"].get(HERO_LABEL)
    if h:
        L += [f"**HERO: P(top 4) = {100 * h['p_top4']:.0f}%  P(top 2) = {100 * h['p_top2']:.0f}%  "
              f"P(win) = {100 * h['p_win']:.0f}%  mean qual rank {h['mean_rank']:.1f}**  (n={n} tournaments; "
              f"binomial SE of a probability p is sqrt(p(1-p)/{n}))", ""]
    L += ["| bot | mean qual rank | mean pts | P(top 4) | P(top 2) | P(win) |", "|---|---|---|---|---|---|"]
    for b, r in sorted(an["bots"].items(), key=lambda kv: kv[1]["mean_rank"]):
        L.append(f"| {'**' + b + '**' if b == HERO_LABEL else b} | {r['mean_rank']:.1f} | {r['mean_pts']:.1f} | "
                 f"{100 * r['p_top4']:.0f}% | {100 * r['p_top2']:.0f}% | {100 * r['p_win']:.0f}% |")
    L += ["", "## Hero qualification pairing record (WW-D-LL, all tours and repetitions)", "",
          "| opp | WW | D | LL | pair score |", "|---|---|---|---|---|"]
    rec = an["hero_qual_record"]
    for o, r in sorted(rec.items(), key=lambda kv: (kv[1]["WW"] + 0.5 * kv[1]["D"]) /
                       max(1, kv[1]["WW"] + kv[1]["D"] + kv[1]["LL"])):
        tot = max(1, r["WW"] + r["D"] + r["LL"])
        L.append(f"| {o} | {r['WW']} | {r['D']} | {r['LL']} | {(r['WW'] + 0.5 * r['D']) / tot:.2f} |")
    L += ["", "## Who knocks the hero out", "",
          "KO-stage eliminations of the hero: " + (", ".join(f"{k} x{v}" for k, v in sorted(
              an["hero_knocked_out_by"].items(), key=lambda kv: -kv[1])) or "none"),
          f"Tours where hero missed the top 4: {an['hero_missed_top4']}/{n}; pairing losses (LL) in those tours: " +
          (", ".join(f"{k} x{v}" for k, v in sorted(an["hero_losses_when_missed_top4"].items(),
                                                     key=lambda kv: -kv[1])) or "none"),
          "KO pair record: " + (", ".join(f"{k} {v['WW']}-{v['D']}-{v['LL']}" for k, v in an["hero_ko_record"].items())
                                or "none")]
    txt = "\n".join(L) + "\n"
    (outdir / "summary.md").write_text(txt)
    return txt


def verify(field, a, n):
    """Check play_lean == lab.run.play_one (winner, hands) on n hero matches."""
    bad = 0
    for k in range(n):
        j = 1 + k % (len(field) - 1)
        seed = derive_seed("tour", a.seeds, "verify", k)
        for sw in (False, True):
            lean = play_lean((None, seed, sw, field[0][1], field[j][1], a.tf))
            full = R.play_one((k, seed, sw, field[0][1], field[j][0], field[j][1], a.tf, 0))
            same = lean["winner"] == full["winner"] and lean["hands"] == full["hands"]
            bad += not same
            print(f"verify {field[j][0]} swap={sw}: lean={lean['winner']}/{lean['hands']} "
                  f"full={full['winner']}/{full['hands']} {'OK' if same else 'MISMATCH'}")
    print(f"verify: {2 * n - bad}/{2 * n} identical")
    return bad == 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--hero", default="my_bots/redteamers007")
    ap.add_argument("--field", default="core", help="resolve_opps tokens, e.g. core,ext,dataset")
    ap.add_argument("--rr", type=int, default=1, help="round robin repetitions per tournament")
    ap.add_argument("--tours", type=int, default=1, help="independent tournaments (Monte Carlo)")
    ap.add_argument("--tour-start", type=int, default=0, help="first tournament index (seed namespace)")
    ap.add_argument("--seeds", default="dev")
    ap.add_argument("--label", default="sim")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tf", type=float, default=2.0)
    ap.add_argument("--verify", type=int, default=0, help="first check N hero matches vs lab.run.play_one")
    a = ap.parse_args(argv)

    hero = f"lab/snapshots/{a.hero[5:]}" if a.hero.startswith("snap:") else a.hero
    field = [(HERO_LABEL, hero)] + resolve_opps(a.field)
    names = [f[0] for f in field]
    assert len(set(names)) == len(names), f"duplicate labels in field: {names}"
    if a.verify and not verify(field, a, a.verify):
        sys.exit("verify failed: lean match path differs from lab.run.play_one")

    outdir = ROOT / "lab/results" / f"{time.strftime('%m%d_%H%M%S')}_tour_{a.label}"
    outdir.mkdir(parents=True, exist_ok=True)
    meta = {"label": a.label, "hero": hero, "field": a.field, "n_bots": len(field), "rr": a.rr, "tours": a.tours,
            "tour_start": a.tour_start, "seeds": a.seeds, "tf": a.tf, "workers": a.workers, "argv": sys.argv}
    (outdir / "meta.json").write_text(json.dumps(meta, indent=1))

    tours = {t: Tour(t, field, a) for t in range(a.tour_start, a.tour_start + a.tours)}
    q = queue.Queue()
    n_pairings = len(field) * (len(field) - 1) // 2
    est_total = a.tours * (n_pairings * a.rr * 2 + 3 * 2 * 2)   # KO estimate ~2 pairs per KO match
    print(f"field {len(field)} bots, {n_pairings} pairings, {n_pairings * 2 * a.rr} qual matches/tour, "
          f"{a.tours} tours, ~{est_total} matches, {a.workers} workers -> {outdir}", flush=True)
    done = 0
    walls, hands = [], []
    hero_to, hero_p99 = 0, 0.0
    crashes = 0
    bot_wall = defaultdict(lambda: [0.0, 0])
    t0 = time.time()
    last = t0
    with Pool(a.workers) as pool:
        def submit(tasks):
            for task in tasks:
                pool.apply_async(play_lean, (task,), callback=q.put,
                                 error_callback=lambda e: q.put({"fatal": repr(e)}))
            return len(tasks)

        inflight = 0
        for T in tours.values():
            inflight += submit(T.start())
        while inflight:
            res = q.get()
            if "fatal" in res:
                raise RuntimeError(res["fatal"])
            inflight -= 1
            done += 1
            walls.append(res["wall"])
            hands.append(res["hands"])
            crashes += "crash" in res
            key = res["key"]
            T = tours[key[0]]
            i, j = key[-2], key[-1]
            for b in (i, j):
                bot_wall[names[b]][0] += res["wall"]
                bot_wall[names[b]][1] += 1
            if HERO_LABEL in (names[i], names[j]) and "crash" not in res:
                s = "a" if names[i] == HERO_LABEL else "b"
                hero_to += res[f"{s}_to"]
                hero_p99 = max(hero_p99, res[f"{s}_p99"])
            inflight += submit(T.on_result(res))
            now = time.time()
            if now - last > 15 or not inflight:
                last = now
                el = now - t0
                fin = sum(x.done for x in tours.values())
                msg = (f"{done}/~{est_total} matches  {el:.0f}s  {done / el:.2f} matches/s  "
                       f"tours done {fin}/{a.tours}  eta ~{max(0, est_total - done) / (done / el):.0f}s")
                print(msg, flush=True)
                (outdir / "progress.txt").write_text(msg + "\n")
    el = time.time() - t0
    summaries = [tours[t].summary() for t in sorted(tours)]
    an = analyse(summaries, names)
    perf = {"matches": done, "elapsed": el, "mps": done / el, "mean_wall": sum(walls) / max(1, len(walls)),
            "hands_mean": sum(hands) / max(1, len(hands)), "crashes": crashes, "hero_timeouts": hero_to,
            "hero_p99_worst": hero_p99,
            "slowest_bots": sorted(((b, w / n) for b, (w, n) in bot_wall.items()), key=lambda x: -x[1])[:6]}
    (outdir / "results.json").write_text(json.dumps({"meta": meta, "perf": perf, "analysis": an,
                                                     "tours": summaries}, indent=1, default=str))
    print(write_summary(outdir, an, meta, perf))
    print(f"[{outdir}]")


if __name__ == "__main__":
    main()
