"""Duplicate-pair match runner (lab).

  python -m lab.run --hero my_bots/redteamers007 --opps core --pairs 30 --seeds dev --label base
  python -m lab.run --hero A --opps "v1=snapshots/v1" --pairs 200 --seeds holdout

One pair = one seed played twice in freezeout with seats swapped (standard blinds).
Writes lab/results/<ts>_<label>/{matches.jsonl, progress.txt, summary.md, results.json, hands.jsonl}.
Resumable: re-run with --resume <dir> to skip matches already in matches.jsonl.
"""
import argparse
import json
import math
import os
import sys
import time
import traceback
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import eval7  # noqa: E402
from pokercore import structures  # noqa: E402
from pokercore.seeds import derive_seed  # noqa: E402
from pokercore.table import MatchConfig, play_match  # noqa: E402
from lab.inproc import InProcSeat  # noqa: E402
from lab.opponents.sets import resolve_opps  # noqa: E402

HERO, OPP = "hero", "villain"
ANY = eval7.HandRange("22+,A2+,K2+,Q2+,J2+,T2+,92+,82+,72+,62+,52+,42+,32").hands


def pair_seed(seedset, k):
    return derive_seed("lab", seedset, k)


# ---------------------------------------------------------------- event sink / stats
class Recorder:
    """Builds compact hand records from table events and accumulates stats."""

    def __init__(self, keep_debug=True):
        self.hands = []
        self.cur = None
        self.keep_debug = keep_debug
        self.min_share = {HERO: 1.0, OPP: 1.0}
        self.final = None

    def emit(self, t, **d):
        if t == "hand_start":
            self.cur = {"hand": d["hand"], "blinds": d["blinds"], "stacks": d["stacks"],
                        "hole": d["hole"], "sb": d["sb"], "seats": d["seats"], "acts": [],
                        "board": [], "show": None}
        elif t == "decision":
            st = d["state"]
            a = {"bot": d["bot"], "st": d["street"], "act": d["applied"]["action"],
                 "amt": d["applied"]["amount"], "owed": st["amount_owed"], "pot": st["pot"],
                 "board": st["community_cards"], "ms": round(d.get("think_ms") or 0, 2)}
            if d.get("error"):
                a["err"] = d["error"]
            if self.keep_debug and d["bot"] == HERO and d.get("debug") is not None:
                a["dbg"] = d["debug"]
            self.cur["acts"].append(a)
        elif t == "showdown":
            self.cur["show"] = d["reveal"]
        elif t == "hand_end":
            self.cur["board"] = d["board"]
            self.cur["deltas"] = d["deltas"]
            tot = sum(d["stacks"].values())
            for n, s in d["stacks"].items():
                self.min_share[n] = min(self.min_share[n], s / tot)
            self.hands.append(self.cur)
        return {"type": t, **d}


def _new_counters():
    return defaultdict(float)


def hand_stats(h, me, opp, C, side):
    """Accumulate counters for bot `me` from hand record h."""
    bb = h["blinds"]["bb"]
    delta = h["deltas"].get(me, 0)
    C["hands"] += 1
    C["bb_won"] += delta / bb
    acts = h["acts"]
    pre = [a for a in acts if a["st"] == "preflop"]
    my_pre = [a for a in pre if a["bot"] == me]
    if my_pre:
        C["vpip_opp"] += 1
        if any(a["act"] in ("call", "raise", "all_in") for a in my_pre):
            C["vpip"] += 1
        if any(a["act"] in ("raise", "all_in") for a in my_pre):
            C["pfr"] += 1
    raises, last_aggr = 0, None
    for a in pre:
        if a["bot"] == me:
            if raises == 1 and last_aggr == opp:
                C["3b_opp"] += 1
                if a["act"] in ("raise", "all_in"):
                    C["3b"] += 1
            if raises >= 2 and last_aggr == opp:
                C["f3b_opp"] += 1
                if a["act"] == "fold":
                    C["f3b"] += 1
        if a["act"] in ("raise", "all_in"):
            raises += 1
            last_aggr = a["bot"]
    # c-bet
    flop = [a for a in acts if a["st"] == "flop"]
    if last_aggr == me and flop:
        first_me = next((a for a in flop if a["bot"] == me), None)
        if first_me and first_me["owed"] == 0 and not any(
                x["act"] in ("raise", "all_in") for x in flop[:flop.index(first_me)]):
            C["cbet_opp"] += 1
            if first_me["act"] in ("raise", "all_in"):
                C["cbet"] += 1
    for a in acts:
        if a["bot"] != me:
            continue
        if a["st"] != "preflop":
            if a["owed"] > 0:
                C[f"ftb_{a['st']}_opp"] += 1
                if a["act"] == "fold":
                    C[f"ftb_{a['st']}"] += 1
            if a["act"] in ("raise", "all_in"):
                C["agg_r"] += 1
            elif a["act"] == "call":
                C["agg_c"] += 1
        if a["act"] == "all_in":
            C["allin_acts"] += 1
        C["think_sum"] += a["ms"]
        C["decisions"] += 1
        if a.get("err") == "timeout":
            C["timeouts"] += 1
        elif a.get("err"):
            C["errors"] += 1
    if flop or h["board"]:
        saw_flop = any(a["st"] != "preflop" for a in acts) or (
            not any(a["act"] == "fold" for a in pre) and len(h["board"]) >= 3)
        if saw_flop:
            C["saw_flop"] += 1
    if h["show"]:
        C["sd"] += 1
        if delta > 0:
            C["sd_won"] += 1
    # line attribution (hero only: debug is kept for hero): hand result -> last decision's line
    last = next((a for a in reversed(acts) if a["bot"] == me and isinstance(a.get("dbg"), dict)), None)
    if last is not None:
        key = f"L|{last['st']}:{last['dbg'].get('line', '?')}:{last['act']}"
        C[key + "|n"] += 1
        C[key + "|bb"] += delta / bb
    # side prizes
    hole = h["hole"][me]
    if sorted(c[0] for c in hole) == ["2", "7"]:
        C["72_dealt"] += 1
        if delta > 0:
            C["72_won"] += delta
    if delta > 0 and acts and acts[-1]["bot"] == opp and acts[-1]["act"] == "fold":
        prev = next((a for a in reversed(acts[:-1]) if a["bot"] == me), None)
        if prev and prev["st"] != "preflop" and prev["act"] in ("raise", "all_in"):
            e = eval7.py_hand_vs_range_monte_carlo([eval7.Card(c) for c in hole], ANY,
                                                    [eval7.Card(c) for c in prev["board"]], 1000)
            if e < 0.40:
                C["bluff_chips"] += delta
                C["bluffs"] += 1
    if h["show"] and delta >= 1000 and len(h["board"]) == 5 and any(
            a["st"] == "river" and a["act"] in ("raise", "all_in") for a in acts):
        val = eval7.evaluate([eval7.Card(c) for c in hole + h["board"]])
        if side.get("min_sd_val") is None or val < side["min_sd_val"]:
            side["min_sd_val"] = val
            side["min_sd_hand"] = eval7.handtype(val) + " " + " ".join(hole) + " | " + " ".join(h["board"])


def play_one(task):
    """Worker: play one match. Returns a compact result dict."""
    (pair, seed, swap, hero_spec, opp_label, opp_spec, tf, keep_hands) = task
    try:
        hs = InProcSeat(HERO, hero_spec, derive_seed(seed, "bot", HERO), time_factor=tf)
        os_ = InProcSeat(OPP, opp_spec, derive_seed(seed, "bot", OPP), time_factor=tf,
                         capture_debug=False)
        seats = [os_, hs] if swap else [hs, os_]
        cfg = MatchConfig(mode="freezeout", hands=1500, starting_stack=10_000,
                          structure=structures.parse("standard", 10_000), seed=seed)
        rec = Recorder()
        res = play_match(seats, cfg, f"p{pair}{'b' if swap else 'a'}", rec)
        winner = next((r["bot"] for r in res["results"] if r["place"] == 1), None)
        Ch, Co = _new_counters(), _new_counters()
        side_h, side_o = {}, {}
        worst = []
        for h in rec.hands:
            hand_stats(h, HERO, OPP, Ch, side_h)
            hand_stats(h, OPP, HERO, Co, side_o)
            worst.append((h["deltas"].get(HERO, 0) / h["blinds"]["bb"], h))
        worst.sort(key=lambda x: x[0])
        think = sorted(hs.think)
        out = {"pair": pair, "swap": swap, "seed": seed, "opp": opp_label, "winner": winner,
               "hero_won": winner == HERO, "hands": res["hands"], "stopped": res["stopped"],
               "hero_final": next(r["final_stack"] for r in res["results"] if r["bot"] == HERO),
               "hero": dict(Ch), "opp_stats": dict(Co), "side_hero": side_h,
               "hero_min_share": rec.min_share[HERO], "opp_min_share": rec.min_share[OPP],
               "think_p99": think[int(len(think) * 0.99)] if think else 0,
               "think_max": think[-1] if think else 0,
               "hero_errors": hs.error_list[:5], "opp_errors": os_.error_list[:3],
               "worst": [{"bb": round(b, 1), **h} for b, h in worst[:keep_hands] if b < -15]}
        return out
    except Exception:
        return {"pair": pair, "swap": swap, "seed": seed, "opp": opp_label, "crash": traceback.format_exc()[-2000:]}


# ---------------------------------------------------------------- aggregation
def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0, 1)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, max(0, c - m), min(1, c + m))


def ratio(C, a, b):
    return C.get(a, 0) / C[b] if C.get(b) else float("nan")


def style_row(C):
    af = ratio(C, "agg_r", "agg_c")
    return {"VPIP": ratio(C, "vpip", "vpip_opp"), "PFR": ratio(C, "pfr", "vpip_opp"),
            "3B": ratio(C, "3b", "3b_opp"), "F3B": ratio(C, "f3b", "f3b_opp"),
            "CB": ratio(C, "cbet", "cbet_opp"), "FtbF": ratio(C, "ftb_flop", "ftb_flop_opp"),
            "FtbT": ratio(C, "ftb_turn", "ftb_turn_opp"), "FtbR": ratio(C, "ftb_river", "ftb_river_opp"),
            "AF": af, "WTSD": ratio(C, "sd", "saw_flop"), "SDW": ratio(C, "sd_won", "sd"),
            "AI/100": 100 * ratio(C, "allin_acts", "hands"), "bb/100": 100 * ratio(C, "bb_won", "hands")}


def aggregate(matches):
    by_opp = defaultdict(list)
    for m in matches:
        if "crash" not in m:
            by_opp[m["opp"]].append(m)
    rows = {}
    tot = {"W": 0, "N": 0, "WW": 0, "D": 0, "LL": 0}
    hero_all, think_p99, crashes = _new_counters(), [], [m for m in matches if "crash" in m]
    side = {"bluff_chips": 0, "hands": 0, "72_won": 0, "72_dealt": 0, "min_sd_val": None,
            "min_sd_hand": None, "best_comeback": None}
    for opp, ms in sorted(by_opp.items()):
        pairs = defaultdict(list)
        for m in ms:
            pairs[m["pair"]].append(m)
        ww = d = ll = 0
        for p, two in pairs.items():
            if len(two) != 2:
                continue
            w = sum(x["hero_won"] for x in two)
            ww += w == 2
            d += w == 1
            ll += w == 0
        W = sum(m["hero_won"] for m in ms)
        N = len(ms)
        Ch, Co = _new_counters(), _new_counters()
        for m in ms:
            for k, v in m["hero"].items():
                Ch[k] += v
                hero_all[k] += v
            for k, v in m["opp_stats"].items():
                Co[k] += v
            think_p99.append(m["think_p99"])
            sh = m["side_hero"]
            if sh.get("min_sd_val") is not None and (side["min_sd_val"] is None or sh["min_sd_val"] < side["min_sd_val"]):
                side["min_sd_val"], side["min_sd_hand"] = sh["min_sd_val"], sh["min_sd_hand"]
            if m["hero_won"] and (side["best_comeback"] is None or m["hero_min_share"] < side["best_comeback"]):
                side["best_comeback"] = m["hero_min_share"]
        p, lo, hi = wilson(W, N)
        rows[opp] = {"W": W, "N": N, "winrate": p, "lo": lo, "hi": hi, "WW": ww, "D": d, "LL": ll,
                     "pair_score": (ww + 0.5 * d) / max(1, ww + d + ll),
                     "avg_hands": sum(m["hands"] for m in ms) / N, "hero": style_row(Ch), "opp": style_row(Co),
                     "timeouts": Ch.get("timeouts", 0), "errors": Ch.get("errors", 0)}
        for k, v in (("W", W), ("N", N), ("WW", ww), ("D", d), ("LL", ll)):
            tot[k] += v
    side.update(bluff_chips=hero_all.get("bluff_chips", 0), hands=hero_all.get("hands", 0),
                **{"72_won": hero_all.get("72_won", 0), "72_dealt": hero_all.get("72_dealt", 0)})
    p, lo, hi = wilson(tot["W"], tot["N"])
    think_p99.sort()
    overall_counters = dict(hero_all)
    overall = {**tot, "winrate": p, "lo": lo, "hi": hi, "hero": style_row(hero_all),
               "timeouts": hero_all.get("timeouts", 0), "errors": hero_all.get("errors", 0),
               "think_mean": ratio(hero_all, "think_sum", "decisions"),
               "think_p99_worst_match": think_p99[-1] if think_p99 else 0,
               "think_p99_median_match": think_p99[len(think_p99) // 2] if think_p99 else 0,
               "think_p99_q99_match": think_p99[int(len(think_p99) * 0.99)] if think_p99 else 0,
               "matches_p99_over_600": sum(x > 600 for x in think_p99),
               "crashes": len(crashes)}
    return {"overall": overall, "hero_counters": overall_counters, "by_opp": rows, "side": side, "crash_samples": [c["crash"] for c in crashes[:3]]}


def fmt(x, pct=True):
    if isinstance(x, float) and math.isnan(x):
        return "-"
    return f"{100 * x:.0f}" if pct else f"{x:.1f}"


def write_summary(outdir, agg, meta):
    o = agg["overall"]
    h_all = agg.get("hero_counters", {})
    L = [f"# {meta['label']}  hero={meta['hero']}  seeds={meta['seeds']}  pairs/opp={meta['pairs']}  tf={meta['tf']}", "",
         f"**Overall match win {100 * o['winrate']:.1f}% [{100 * o['lo']:.1f}, {100 * o['hi']:.1f}]**  "
         f"N={o['N']}  pairs WW-D-LL {o['WW']}-{o['D']}-{o['LL']}  timeouts={o['timeouts']:.0f} errors={o['errors']:.0f} "
         f"crashes={o['crashes']}  think mean={o['think_mean']:.1f}ms p99(worst match)={o['think_p99_worst_match']:.0f}ms", "",
         "| opp | win% | 95% CI | WW-D-LL | hands | hero bb/100 | hero VPIP/PFR/3B | hero AF | opp VPIP/PFR/3B | opp FtbF/T/R | opp AF |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for opp, r in sorted(agg["by_opp"].items(), key=lambda kv: kv[1]["winrate"]):
        h, p = r["hero"], r["opp"]
        L.append(f"| {opp} | {100 * r['winrate']:.0f} | {100 * r['lo']:.0f}-{100 * r['hi']:.0f} | {r['WW']}-{r['D']}-{r['LL']} | "
                 f"{r['avg_hands']:.0f} | {fmt(h['bb/100'], False)} | {fmt(h['VPIP'])}/{fmt(h['PFR'])}/{fmt(h['3B'])} | {fmt(h['AF'], False)} | "
                 f"{fmt(p['VPIP'])}/{fmt(p['PFR'])}/{fmt(p['3B'])} | {fmt(p['FtbF'])}/{fmt(p['FtbT'])}/{fmt(p['FtbR'])} | {fmt(p['AF'], False)} |")
    h = o["hero"]
    lines = sorted(((k[2:-2], v, h_all.get(k[:-2] + "|bb", 0)) for k, v in h_all.items() if k.startswith("L|") and k.endswith("|n")),
                   key=lambda x: x[2])
    hands_all = max(1, h_all.get("hands", 1))
    L += ["", "Hero result by final line (bb/100 hands contribution, count): " + "  ".join(
        f"{k}={100 * b / hands_all:+.0f}({n:.0f})" for k, n, b in lines[:8]) + "  ...  " + "  ".join(
        f"{k}={100 * b / hands_all:+.0f}({n:.0f})" for k, n, b in lines[-5:])]
    L += ["", "Hero overall: " + "  ".join(f"{k}={fmt(v, k not in ('AF', 'AI/100', 'bb/100'))}" for k, v in h.items())]
    s = agg["side"]
    L += ["", f"Side: bluff chips/1000h={1000 * s['bluff_chips'] / max(1, s['hands']):.0f}  "
              f"7-2 won/dealt={s['72_won'] / max(1, s['72_dealt']):.0f} ({s['72_dealt']:.0f} dealt)  "
              f"weakest win SD: {s['min_sd_hand']}  best comeback share={s['best_comeback']}"]
    if agg["crash_samples"]:
        L += ["", "CRASHES:", "```", agg["crash_samples"][0][-800:], "```"]
    (outdir / "summary.md").write_text("\n".join(L) + "\n")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--hero", required=True)
    ap.add_argument("--opps", default="core")
    ap.add_argument("--pairs", type=int, default=30)
    ap.add_argument("--seeds", default="dev", help="dev | holdout | any string (seed namespace)")
    ap.add_argument("--start", type=int, default=0, help="first pair index")
    ap.add_argument("--label", default="run")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--tf", type=float, default=2.0, help="time factor emulating half a core")
    ap.add_argument("--keep-hands", type=int, default=2)
    ap.add_argument("--resume")
    a = ap.parse_args(argv)

    opps = resolve_opps(a.opps)
    if a.hero.startswith("snap:"):
        a.hero = f"lab/snapshots/{a.hero[5:]}"
    if a.resume:
        outdir = Path(a.resume)
    else:
        outdir = ROOT / "lab/results" / f"{time.strftime('%m%d_%H%M%S')}_{a.label}"
    outdir.mkdir(parents=True, exist_ok=True)
    meta = {"label": a.label, "hero": a.hero, "opps": a.opps, "pairs": a.pairs, "seeds": a.seeds,
            "start": a.start, "tf": a.tf, "argv": sys.argv}
    (outdir / "meta.json").write_text(json.dumps(meta, indent=1))
    mpath = outdir / "matches.jsonl"
    done = set()
    matches = []
    if mpath.exists():
        for line in mpath.read_text().splitlines():
            m = json.loads(line)
            matches.append(m)
            done.add((m["opp"], m["pair"], m["swap"]))
    tasks = []
    for k in range(a.start, a.start + a.pairs):
        seed = pair_seed(a.seeds, k)
        for label, spec in opps:
            for swap in (False, True):
                if (label, k, swap) not in done:
                    tasks.append((k, seed, swap, a.hero, label, spec, a.tf, a.keep_hands))
    # interleave so partial results cover all opponents
    tasks.sort(key=lambda t: (t[0], t[4], t[2]))
    total = len(tasks) + len(done)
    t0 = time.time()
    with open(mpath, "a") as mf, open(outdir / "hands.jsonl", "a") as hf, Pool(a.workers) as pool:
        for i, r in enumerate(pool.imap_unordered(play_one, tasks, chunksize=1)):
            worst = r.pop("worst", [])
            for w in worst:
                hf.write(json.dumps({"opp": r["opp"], "pair": r["pair"], "swap": r["swap"], **w}) + "\n")
            mf.write(json.dumps(r) + "\n")
            mf.flush()
            matches.append(r)
            if i % 20 == 0 or i == len(tasks) - 1:
                el = time.time() - t0
                (outdir / "progress.txt").write_text(
                    f"{len(done) + i + 1}/{total} matches  {el:.0f}s  eta {el / (i + 1) * (len(tasks) - i - 1):.0f}s\n")
    agg = aggregate(matches)
    (outdir / "results.json").write_text(json.dumps({"meta": meta, **agg}, indent=1, default=str))
    print(write_summary(outdir, agg, meta))
    print(f"\n[{outdir}]")


if __name__ == "__main__":
    main()
