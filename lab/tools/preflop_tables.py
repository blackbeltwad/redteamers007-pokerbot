"""Build preflop tables used by lab opponents and by our bot.

Outputs (JSON):
  lab/data/preflop.json and my_bots/redteamers007/data/preflop.json
    classes      : 169 hand-class names ("AA", "AKs", "AKo", ...)
    eq_random    : equity of each class vs a uniformly random hand
    eq_matrix    : 169x169 equity of class i vs class j (card removal averaged)
    w_matrix     : 169x169 number of non-conflicting combo pairs
    pushfold     : heads-up push/fold equilibrium (fictitious play) for SB shove / BB call,
                   per ante setting and stack depth: {"ante0": {"S": [...], "push": [[..169]], "call": [[..169]]}, ...}

Run: python -m lab.tools.preflop_tables   (uses all cores, ~1 min)
"""
import itertools
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import eval7
import numpy as np

RANKS = "AKQJT98765432"
SUITS = "shdc"
ROOT = Path(__file__).resolve().parents[2]


def classes():
    out = []
    for i, r1 in enumerate(RANKS):
        for j, r2 in enumerate(RANKS):
            if i == j:
                out.append(r1 + r2)
            elif i < j:
                out.append(r1 + r2 + "s")
            else:
                out.append(r2 + r1 + "o")
    return out


def combos(cls):
    r1, r2 = cls[0], cls[1]
    if len(cls) == 2:
        return [(r1 + a, r2 + b) for a, b in itertools.combinations(SUITS, 2)]
    if cls[2] == "s":
        return [(r1 + s, r2 + s) for s in SUITS]
    return [(r1 + a, r2 + b) for a in SUITS for b in SUITS if a != b]


CLS = classes()
COMBOS = [combos(c) for c in CLS]
ITERS = 6000


def row(i):
    hero_combos = COMBOS[i]
    eq = np.zeros(169)
    w = np.zeros(169)
    for j in range(169):
        tot, wt = 0.0, 0
        for hc in hero_combos:
            hero = [eval7.Card(c) for c in hc]
            vill = [((eval7.Card(a), eval7.Card(b)), 1.0) for a, b in COMBOS[j]
                    if a not in hc and b not in hc]
            if not vill:
                continue
            n = len(vill)
            e = eval7.py_hand_vs_range_monte_carlo(hero, vill, [], max(500, ITERS // len(hero_combos)))
            tot += e * n
            wt += n
        eq[j] = tot / wt if wt else 0.5
        w[j] = wt
    return i, eq.tolist(), w.tolist()


def pushfold(E, W, S, ante, iters=3000):
    """SB shove/fold vs BB call/fold. S = effective stack in bb (before posting),
    ante in bb per player. Returns push[169], call[169] (frequencies)."""
    E = np.asarray(E)
    W = np.asarray(W)
    prior = np.array([len(c) for c in COMBOS], dtype=float)  # combos per class
    push = np.ones(169)
    call = np.ones(169) * 0.5
    push_avg = np.zeros(169)
    call_avg = np.zeros(169)
    for t in range(1, iters + 1):
        # BB best response to push range
        # weights of SB holding j given BB holds i: W[i,j] * push[j]
        wp = W * push[None, :]
        tot_push = wp.sum(1)
        tot_all = W.sum(1)
        # EV of calling for BB with class i: sum_j wp[i,j]*(E[i,j]*2S - S) / tot_push ; fold: -(1+ante)
        ev_call = np.where(tot_push > 0, (wp * (E * 2 * S - S)).sum(1) / np.maximum(tot_push, 1e-9), 0)
        ev_fold_bb = -(1 + ante)
        br_call = (ev_call > ev_fold_bb).astype(float)
        call = call + (br_call - call) / (t + 1)
        # SB best response to call range
        wc = W * call[None, :]     # W symmetric: SB i vs BB j
        p_call = wc.sum(1) / tot_all
        ev_called = np.where(wc.sum(1) > 0, (wc * (E * 2 * S - S)).sum(1) / np.maximum(wc.sum(1), 1e-9), 0)
        ev_push = (1 - p_call) * (1 + ante) + p_call * ev_called
        ev_fold_sb = -(0.5 + ante)
        br_push = (ev_push > ev_fold_sb).astype(float)
        push = push + (br_push - push) / (t + 1)
    return push, call


def main():
    with Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        rows = sorted(pool.map(row, range(169)))
    E = np.array([r[1] for r in rows])
    W = np.array([r[2] for r in rows])
    # symmetrise: E[i,j] + E[j,i] = 1
    E = (E + (1 - E.T)) / 2
    prior = np.array([len(c) for c in COMBOS], dtype=float)
    eq_random = (E * W).sum(1) / W.sum(1)
    S_grid = [round(x, 1) for x in np.arange(1.0, 30.01, 0.5)]
    pf = {}
    for ante_name, ante in (("ante0", 0.0), ("ante10", 0.1)):
        P, C = [], []
        for S in S_grid:
            p, c = pushfold(E, W, S, ante)
            P.append([round(x, 3) for x in p])
            C.append([round(x, 3) for x in c])
        pf[ante_name] = {"S": S_grid, "push": P, "call": C}
        pct = [round(float((np.array(P[k]) * prior).sum() / 1326), 3) for k in range(len(S_grid))]
        print(ante_name, "push% by S:", list(zip(S_grid[::4], pct[::4])), file=sys.stderr)
    out = {"classes": CLS, "eq_random": [round(x, 4) for x in eq_random],
           "eq_matrix": [[round(x, 4) for x in r] for r in E],
           "w_matrix": [[int(x) for x in r] for r in W], "pushfold": pf}
    for p in (ROOT / "lab/data/preflop.json", ROOT / "my_bots/redteamers007/data/preflop.json"):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, separators=(",", ":")))
    top = sorted(range(169), key=lambda i: -eq_random[i])
    print("top10:", [(CLS[i], round(eq_random[i], 3)) for i in top[:10]], file=sys.stderr)


if __name__ == "__main__":
    main()
