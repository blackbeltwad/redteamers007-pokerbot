"""Stream PHH hand histories -> per-player stats -> archetype sparring-bot params.

  python -m lab.tools.phh_stats lab/datasets/phh-dataset/data [--min-hands 300]

Never loads more than one hand at a time; works on any size of dataset (e.g. the 20 GB Zenodo
archive once unzipped). Only no-limit hold'em ('NT') hands are used.
Writes lab/data/dataset_profiles.json (small) and prints a short table.

Mapping to heads-up: the source is mostly 6-max, where ranges are much tighter than heads-up.
Preflop frequencies are widened by a fixed factor (HU_SCALE) - an approximation, stated plainly.
Postflop tendencies (fold-to-bet, bet-when-checked-to, aggression) are used as measured.
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HU_SCALE = 2.3


def parse_phh(text):
    d = {}
    for line in text.splitlines():
        if " = " not in line:
            continue
        k, v = line.split(" = ", 1)
        v = v.strip().replace("true", "True").replace("false", "False")
        try:
            d[k.strip()] = eval_literal(v)
        except Exception:
            pass
    return d


def eval_literal(v):
    import ast
    return ast.literal_eval(v)


def hand_stats(h, S):
    if h.get("variant") != "NT" or "players" not in h:
        return
    names = h["players"]
    n = len(names)
    blinds = list(h.get("blinds_or_straddles", [0] * n)) + [0] * n
    contrib = {i: blinds[i] for i in range(n)}          # this street
    cur = max(blinds[:n]) if any(blinds[:n]) else 0
    street = 0
    raises = 0
    pre_raiser = None
    vp, pr = set(), set()
    seen_bet_street = False
    for a in h.get("actions", []):
        parts = a.split()
        if parts[0] == "d":
            if parts[1] == "db":
                street += 1
                contrib = {i: 0 for i in range(n)}
                cur = 0
                seen_bet_street = False
            continue
        if not parts[0].startswith("p"):
            continue
        i = int(parts[0][1:]) - 1
        if i >= n:
            continue
        p = names[i]
        act = parts[1]
        owed = cur - contrib.get(i, 0)
        if street == 0:
            if raises == 1 and act in ("cbr", "cc", "f"):
                S[p]["3b_opp"] += 1
                if act == "cbr":
                    S[p]["3b"] += 1
        else:
            if owed > 0:
                S[p]["ftb_opp"] += 1
                if act == "f":
                    S[p]["ftb"] += 1
                elif act == "cc":
                    S[p]["calls"] += 1
                elif act == "cbr":
                    S[p]["raises"] += 1
            elif not seen_bet_street:
                S[p]["bwc_opp"] += 1
                if act == "cbr":
                    S[p]["bwc"] += 1
                    S[p]["raises"] += 1
        if act == "cbr":
            amt = int(parts[2])
            contrib[i] = amt
            cur = amt
            if street == 0:
                raises += 1
                pr.add(p)
                vp.add(p)
                pre_raiser = p
            else:
                seen_bet_street = True
        elif act == "cc":
            if street == 0 and owed > 0:
                vp.add(p)
            contrib[i] = cur
    for i, p in enumerate(names):
        S[p]["hands"] += 1
    for p in vp:
        S[p]["vpip"] += 1
    for p in pr:
        S[p]["pfr"] += 1


def r(S, a, b, prior, k=20):
    return (S[a] + prior * k) / (S[b] + k)


def to_params(S):
    vpip6 = S["vpip"] / S["hands"]
    pfr6 = S["pfr"] / S["hands"]
    tb = r(S, "3b", "3b_opp", 0.07)
    ftb = r(S, "ftb", "ftb_opp", 0.45)
    bwc = r(S, "bwc", "bwc_opp", 0.35)
    af = (S["raises"] + 2) / (S["calls"] + 2)
    vpip = min(0.95, HU_SCALE * vpip6)
    return {
        "vpip": round(vpip, 3), "pfr": round(min(vpip, HU_SCALE * pfr6), 3),
        "threebet": round(min(0.4, 2.0 * tb), 3),
        "call_margin": round(max(-0.3, min(0.4, (0.45 - ftb) * 0.8)), 3),
        "bluff": round(max(0.0, min(0.6, bwc - 0.2)), 3),
        "bet_eq": round(max(0.45, min(0.85, 0.75 - 0.5 * (bwc - 0.3))), 3),
        "raise_eq": round(max(0.65, min(0.92, 0.88 - 0.05 * (af - 1))), 3),
        "size": 0.66, "pf_size": 2.5, "shove_bb": 8, "shove_range": 0.45,
    }, {"vpip6": round(vpip6, 3), "pfr6": round(pfr6, 3), "3b": round(tb, 3), "ftb": round(ftb, 3),
        "bwc": round(bwc, 3), "af": round(af, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--min-hands", type=int, default=300)
    a = ap.parse_args()
    S = defaultdict(lambda: defaultdict(int))
    nfiles = 0
    for dp, _, fs in os.walk(a.root):
        for f in fs:
            if not f.endswith(".phh"):
                continue
            try:
                hand_stats(parse_phh(Path(dp, f).read_text(errors="ignore")), S)
                nfiles += 1
            except Exception:
                pass
    prof = {}
    for p, st in S.items():
        if st["hands"] >= a.min_hands:
            params, raw = to_params(st)
            prof[p] = {"hands": st["hands"], "raw": raw, "params": params}
    out = ROOT / "lab/data/dataset_profiles.json"
    out.write_text(json.dumps({"source": a.root, "files": nfiles, "hu_scale": HU_SCALE, "profiles": prof}, indent=1))
    print(f"{nfiles} hands parsed, {len(prof)} players with >= {a.min_hands} hands -> {out}")
    print(f"{'player':12s} {'hands':>6s} vpip6 pfr6  3b   ftb  bwc   af")
    for p, v in sorted(prof.items(), key=lambda kv: -kv[1]["hands"]):
        x = v["raw"]
        print(f"{p[:12]:12s} {v['hands']:6d} {x['vpip6']:.2f} {x['pfr6']:.2f} {x['3b']:.2f} {x['ftb']:.2f} {x['bwc']:.2f} {x['af']:.1f}")


if __name__ == "__main__":
    main()
