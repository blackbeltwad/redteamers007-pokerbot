"""redteamers007: heads-up NLHE tournament bot.

Design (sound baseline + exploit layer):
  * Preflop tables (data/preflop.json, built offline by lab/tools/preflop_tables.py):
      - 169x169 class-vs-class all-in equity matrix and combo-count matrix
      - heads-up push/fold equilibrium (fictitious play) by stack depth, with/without antes
  * Short stacks (<= PF_BB effective bb): equilibrium push/fold, widened/tightened by the
    opponent's measured calling/shoving frequency (shrunk toward the equilibrium).
  * Deeper preflop: open/3-bet/call decisions by equity of our class vs the opponent's
    estimated range (a top-x% range whose x is the opponent's measured frequency for that
    action, shrunk toward a prior), compared with pot odds.
  * Postflop: Monte Carlo equity (eval7) vs a weighted combo range: preflop range,
    then Bayesian-ish narrowing by the opponent's bets/calls on each street.
    Value-bet / bluff / call / raise thresholds use pot odds; bluff frequency rises with
    the opponent's measured fold-to-bet.
Everything decision-relevant goes in the "debug" field.
"""
import json
import os
import random
from pathlib import Path

import eval7
import numpy as np

# ------------------------------------------------------------------ static tables
_DATA = Path(os.environ.get("BOT_DATA_DIR") or Path(__file__).resolve().parent / "data")
try:
    _PF = json.loads((_DATA / "preflop.json").read_text())
except Exception:  # fall back to the folder next to bot.py
    _PF = json.loads((Path(__file__).resolve().parent / "data" / "preflop.json").read_text())

CLASSES = _PF["classes"]
CIDX = {c: i for i, c in enumerate(CLASSES)}
E = np.array(_PF["eq_matrix"], dtype=np.float64)
W = np.array(_PF["w_matrix"], dtype=np.float64)
EQR = np.array(_PF["eq_random"])
NCOMBO = np.array([6 if len(c) == 2 else (4 if c[2] == "s" else 12) for c in CLASSES], dtype=float)
_ORDER = np.argsort(-EQR)
PCT = np.zeros(169)          # fraction of combos ranked above this class (0 = AA)
_acc = 0.0
for _i in _ORDER:
    PCT[_i] = _acc / 1326.0
    _acc += NCOMBO[_i]
PCT_MID = PCT + NCOMBO / 2652.0
PF_TABLE = {k: (np.array(v["S"]), np.array(v["push"]), np.array(v["call"])) for k, v in _PF["pushfold"].items()}
RANKS = "AKQJT98765432"
SUITS = "shdc"
COMBOS = []
for _c in CLASSES:
    r1, r2 = _c[0], _c[1]
    if len(_c) == 2:
        cs = [(r1 + SUITS[a], r2 + SUITS[b]) for a in range(4) for b in range(a + 1, 4)]
    elif _c[2] == "s":
        cs = [(r1 + s, r2 + s) for s in SUITS]
    else:
        cs = [(r1 + a, r2 + b) for a in SUITS for b in SUITS if a != b]
    COMBOS.append(cs)
CARD = {r + s: eval7.Card(r + s) for r in RANKS for s in SUITS}

PF_BB = 13.0            # push/fold at or below this effective stack (bb)

# Tunables (lab A/B tests call configure(); the tournament never does)
TUNE = {"bluff_prior": 0.25, "real_flop": (0.85, 0.92), "real_turn": (0.90, 0.95)}


def configure(params):
    for k, v in params.items():
        if k in ("real_flop", "real_turn"):
            continue
        TUNE[k] = v
    if "rf" in params:
        TUNE["real_flop"] = (params["rf"], min(1.0, params["rf"] + 0.07))
        TUNE["real_turn"] = (min(1.0, params["rf"] + 0.05), min(1.0, params["rf"] + 0.1))

# ------------------------------------------------------------------ opponent model
OPP = {}                # module state: lasts one match
_seen_hands = set()
BOARDS = {}             # hand_num -> last board we saw (match_action_log has no board)


def _reset_model():
    OPP.clear()
    OPP.update({
        # counts: (events, opportunities)
        "sb_open": [0, 0], "sb_limp": [0, 0], "sb_shove": [0, 0],
        "bb_fold_open": [0, 0], "bb_3bet": [0, 0], "bb_call_shove": [0, 0],
        "fold_to_3bet": [0, 0],
        "fold_to_bet": [0, 0], "bet_when_checked": [0, 0], "raise_vs_bet": [0, 0],
        "bet_bluff": [0, 0],    # opp postflop bets later shown down: (weak at the time, total)
        "hands": 0,
    })


_reset_model()


def rate(key, prior, strength=12.0):
    k, n = OPP[key]
    return (k + prior * strength) / (n + strength)


def _update_model(gs, me_id):
    """Digest completed hands from match_action_log (hands < current)."""
    cur = gs["hand_num"]
    by_hand = {}
    for e in gs.get("match_action_log") or []:
        h = e.get("hand_num")
        if h is None or h >= cur or h in _seen_hands:
            continue
        by_hand.setdefault(h, []).append(e)
    for h in sorted(by_hand):
        _seen_hands.add(h)
        _digest_hand(by_hand[h], me_id)


def _digest_hand(es, me):
    OPP["hands"] += 1
    sb_bot = next((e["bot_id"] for e in es if e["action"] == "small_blind"), None)
    acts = [e for e in es if e["action"] in ("fold", "check", "call", "raise", "all_in")]
    pre = [e for e in acts if e["street"] == "preflop"]
    opp_is_sb = sb_bot is not None and sb_bot != me
    if pre:
        first = pre[0]
        if opp_is_sb and first["bot_id"] != me:
            OPP["sb_open"][1] += 1
            OPP["sb_limp"][1] += 1
            OPP["sb_shove"][1] += 1
            if first["action"] == "raise":
                OPP["sb_open"][0] += 1
            elif first["action"] == "all_in":
                OPP["sb_open"][0] += 1
                OPP["sb_shove"][0] += 1
            elif first["action"] in ("call", "check"):
                OPP["sb_limp"][0] += 1
        if not opp_is_sb and first["bot_id"] == me and first["action"] in ("raise", "all_in"):
            resp = next((e for e in pre[1:] if e["bot_id"] != me), None)
            if resp:
                if first["action"] == "all_in":
                    OPP["bb_call_shove"][1] += 1
                    OPP["bb_call_shove"][0] += resp["action"] in ("call", "all_in")
                else:
                    OPP["bb_fold_open"][1] += 1
                    OPP["bb_3bet"][1] += 1
                    OPP["bb_fold_open"][0] += resp["action"] == "fold"
                    OPP["bb_3bet"][0] += resp["action"] in ("raise", "all_in")
        # opp raised, we re-raised, opp responded
        aggr = [e for e in pre if e["action"] in ("raise", "all_in")]
        for i, e in enumerate(pre):
            if e["bot_id"] == me and e["action"] == "raise" and any(
                    x["bot_id"] != me and x["action"] in ("raise",) for x in pre[:i]):
                resp = next((x for x in pre[i + 1:] if x["bot_id"] != me), None)
                if resp:
                    OPP["fold_to_3bet"][1] += 1
                    OPP["fold_to_3bet"][0] += resp["action"] == "fold"
                break
    # showdown calibration: were the opponent's postflop bets made with weak hands?
    shown = next((e.get("cards") for e in es if e["action"] == "show" and e["bot_id"] != me), None)
    hn = es[0].get("hand_num")
    board = BOARDS.get(hn) or []
    if shown and len(board) >= 3:
        nb = {"flop": 3, "turn": 4, "river": 5}
        for st in ("flop", "turn", "river"):
            if len(board) < nb[st]:
                break
            if any(e["street"] == st and e["bot_id"] != me and e["action"] in ("raise", "all_in") for e in acts):
                OPP["bet_bluff"][1] += 1
                OPP["bet_bluff"][0] += _strength_pct(shown, board[:nb[st]]) < 0.5
    # postflop: opp response to our bets, opp betting when checked to
    for st in ("flop", "turn", "river"):
        sa = [e for e in acts if e["street"] == st]
        for i, e in enumerate(sa):
            if e["bot_id"] == me:
                continue
            prev = sa[i - 1] if i > 0 else None
            if prev is not None and prev["bot_id"] == me and prev["action"] in ("raise", "all_in"):
                OPP["fold_to_bet"][1] += 1
                OPP["fold_to_bet"][0] += e["action"] == "fold"
                OPP["raise_vs_bet"][1] += 1
                OPP["raise_vs_bet"][0] += e["action"] in ("raise", "all_in")
            elif not any(x["action"] in ("raise", "all_in") for x in sa[:i]):
                OPP["bet_when_checked"][1] += 1
                OPP["bet_when_checked"][0] += e["action"] in ("raise", "all_in")


# ------------------------------------------------------------------ helpers
def cls_of(cards):
    a, b = cards
    ra, rb = RANKS.index(a[0]), RANKS.index(b[0])
    if ra > rb:
        a, b, ra, rb = b, a, rb, ra
    if ra == rb:
        return CIDX[a[0] + b[0]]
    return CIDX[a[0] + b[0] + ("s" if a[1] == b[1] else "o")]


def top_range(frac, soft=0.06):
    """Class weights for the top `frac` of hands (by equity vs random), soft edge."""
    frac = min(1.0, max(0.01, frac))
    return np.clip((frac + soft / 2 - PCT_MID) / soft, 0.0, 1.0)


def band_range(lo, hi, soft=0.06):
    return np.clip(top_range(hi, soft) - top_range(lo, soft), 0, 1)


def eq_vs_range(ci, rng):
    w = W[ci] * rng
    s = w.sum()
    return float((w * E[ci]).sum() / s) if s > 0 else 0.5


def pf_lookup(S, ante_bb):
    key = "ante10" if ante_bb > 0.02 else "ante0"
    Sg, P, C = PF_TABLE[key]
    k = int(np.clip(np.searchsorted(Sg, S), 0, len(Sg) - 1))
    return P[k], C[k]


def raise_to(gs, amount):
    amount = int(amount)
    cap = gs["your_stack"] + gs["your_bet_this_street"]
    if amount >= cap * 0.9:
        return {"action": "all_in"}
    return {"action": "raise", "amount": max(gs["min_raise_to"], amount)}


def passive(gs):
    return {"action": "check"} if gs["can_check"] else {"action": "fold"}


# ------------------------------------------------------------------ preflop
def preflop(gs, ctx):
    bb = ctx["bb"]
    ci = ctx["ci"]
    S = ctx["eff_bb"]
    ante_bb = ctx["ante"] / bb
    me = gs["your_bot_id"]
    pre = [a for a in gs["action_log"] if a["street"] == "preflop" and a["action"] in ("raise", "all_in", "call", "check", "fold")]
    opp_aggr = [a for a in pre if a["bot_id"] != me and a["action"] in ("raise", "all_in")]
    my_aggr = [a for a in pre if a["bot_id"] == me and a["action"] in ("raise", "all_in")]
    is_sb = gs["seat_to_act"] == gs["sb_seat"]
    owed, pot = gs["amount_owed"], gs["pot"]
    dbg = ctx["dbg"]
    dbg["cls"] = CLASSES[ci]
    dbg["S"] = round(S, 1)
    push, call = pf_lookup(S, ante_bb)

    # ---- facing an all-in (or a raise that commits us): call by equity vs estimated range
    opp_all_in = any(a["action"] == "all_in" for a in opp_aggr) or ctx["opp_stack_behind"] == 0
    commit = owed >= 0.4 * (gs["your_stack"])
    if opp_aggr and (opp_all_in or commit):
        if not my_aggr:
            # first-in shove from SB, or a big raise
            nash_push = float((push * NCOMBO).sum() / 1326)
            freq = rate("sb_shove", nash_push, 10) if opp_all_in else rate("sb_open", 0.7, 10)
            if not opp_all_in:
                freq *= 0.6
            rng = top_range(max(freq, 0.05))
        else:
            freq = rate("bb_3bet", 0.12, 10) * 0.8
            rng = top_range(max(freq, 0.04))
        eq = eq_vs_range(ci, rng)
        need = owed / (pot + owed)
        # with a skill edge, avoid coin-flips for deep stacks (freezeout: survival matters)
        margin = float(np.clip((S - 20) / 80, 0, 1)) * 0.08
        dbg.update(line="vs_allin", eq=round(eq, 3), need=round(need, 3), margin=round(margin, 3), opp_rng=round(freq, 3))
        if eq >= need + margin:
            return {"action": "call"} if opp_all_in or owed >= gs["your_stack"] else {"action": "all_in"}
        return {"action": "fold"}

    # ---- short-stack push/fold
    if S <= PF_BB:
        if not opp_aggr and is_sb and not my_aggr:
            # widen vs over-folders, tighten vs over-callers (shrunk toward equilibrium)
            nash_call = float((call * NCOMBO).sum() / 1326)
            obs_call = rate("bb_call_shove", nash_call, 15)
            p = push[ci]
            if obs_call < nash_call - 0.1:
                # opponent folds too much: shove anything with positive fold equity EV
                rng = top_range(obs_call)
                eq = eq_vs_range(ci, rng)
                ev = (1 - obs_call) * (1 + ante_bb) + obs_call * (eq * 2 * S - S)
                p = 1.0 if ev > -(0.5 + ante_bb) else p
            dbg.update(line="pf_push", nash=round(float(push[ci]), 2), p=round(p, 2), obs_call=round(obs_call, 2))
            return {"action": "all_in"} if random.random() < p else {"action": "fold"}
        if not opp_aggr and not is_sb:
            # SB limped: shove our push range (iso-shove), else check
            p = push[ci] if PCT_MID[ci] < 0.45 else 0.0
            dbg.update(line="pf_vs_limp", p=round(float(p), 2))
            return {"action": "all_in"} if random.random() < p else {"action": "check"}
        # facing a non-all-in raise at short stack: reshove with call range, else fold
        freq = rate("sb_open", 0.7, 10) if not my_aggr else rate("bb_3bet", 0.15, 10)
        rng = top_range(freq)
        eq = eq_vs_range(ci, rng)
        # reshove EV: fold equity unknown -> assume opponent calls with top 40% of its range
        need = (S - ctx["my_in"] / bb) / (2 * S)
        dbg.update(line="pf_reshove", eq=round(eq, 3), need=round(need, 3))
        if eq >= need - 0.04 or call[ci] > 0.5:
            return {"action": "all_in"}
        return {"action": "fold"}

    # ---- deep preflop
    if is_sb and not opp_aggr and not my_aggr:
        # first in: open top ~X% (wider vs folders, tighter vs 3-bettors)
        fold_open = rate("bb_fold_open", 0.35, 12)
        three = rate("bb_3bet", 0.12, 12)
        width = 0.78 + 0.4 * (fold_open - 0.35) - 0.5 * (three - 0.12)
        if three > 0.3:
            # opponent re-raises a lot: only open what we'd continue with vs its re-raise range
            width = min(width, max(0.12, 0.7 - three))
        width = float(np.clip(width, 0.12, 1.0))
        dbg.update(line="open", width=round(width, 2))
        if PCT_MID[ci] < width:
            size = 2.5 if S > 30 else 2.2
            return raise_to(gs, size * bb)
        return {"action": "fold"}

    if not is_sb and not opp_aggr:
        # SB limped: raise top 35%, else check
        dbg.update(line="vs_limp")
        if PCT_MID[ci] < 0.35:
            return raise_to(gs, 4 * bb)
        return {"action": "check"}

    # facing a raise (open / 3-bet / 4-bet)
    n_opp = len(opp_aggr)
    if not my_aggr:
        freq = rate("sb_open", 0.75, 12)
    else:
        freq = rate("bb_3bet", 0.12, 12) if is_sb else rate("sb_open", 0.75, 12) * 0.35
    freq = max(0.04, freq)
    rng = top_range(freq)
    eq = eq_vs_range(ci, rng)
    need = owed / (pot + owed)
    # realization: in position we realise more, OOP less
    real = 0.95 if is_sb else 0.82
    to_call_frac = (gs["your_bet_this_street"] + owed) / (gs["your_stack"] + gs["your_bet_this_street"])
    dbg.update(line="vs_raise", eq=round(eq, 3), need=round(need, 3), opp_rng=round(freq, 3), n=n_opp)
    # strong vs range: re-raise (value), shove if re-raise would commit us
    value_thr = 0.60 if n_opp == 1 else 0.58
    if eq >= value_thr or PCT_MID[ci] < freq * 0.18:
        tgt = gs["current_bet"] * (3.0 if not is_sb else 2.5) + (0 if n_opp == 1 else pot * 0.3)
        if tgt > 0.35 * (gs["your_stack"] + gs["your_bet_this_street"]) or n_opp >= 2:
            return {"action": "all_in"}
        return raise_to(gs, tgt)
    # light 3-bet bluffs with blockers/suited hands at low frequency
    if n_opp == 1 and not is_sb and 0.35 < PCT_MID[ci] < 0.6 and random.random() < 0.10 * rate("fold_to_3bet", 0.4, 10) / 0.4:
        tgt = gs["current_bet"] * 3.0
        if tgt < 0.3 * gs["your_stack"]:
            dbg["bluff3b"] = 1
            return raise_to(gs, tgt)
    if eq * real >= need or (to_call_frac < 0.2 and eq >= need + 0.03):
        return {"action": "call"}
    return {"action": "fold"}


# ------------------------------------------------------------------ postflop
def opp_preflop_range(gs, me):
    pre = [a for a in gs["action_log"] if a["street"] == "preflop" and a["action"] in ("raise", "all_in", "call", "check", "fold")]
    opp_is_sb = gs["sb_seat"] != gs["seat_to_act"]
    opp_aggr = [a for a in pre if a["bot_id"] != me and a["action"] in ("raise", "all_in")]
    my_aggr = [a for a in pre if a["bot_id"] == me and a["action"] in ("raise", "all_in")]
    if opp_is_sb:
        if not opp_aggr:
            limp = rate("sb_limp", 0.2, 10)
            op = rate("sb_open", 0.7, 10)
            return band_range(min(op, 0.6) * 0.5, min(1, op + limp)) + 0.15 * top_range(op)
        if len(opp_aggr) == 1:
            if my_aggr:  # we 3-bet, opp called
                return band_range(0.03, rate("sb_open", 0.7, 10) * 0.45) + 0.3 * top_range(0.03)
            return top_range(rate("sb_open", 0.7, 10))
        return top_range(rate("sb_open", 0.7, 10) * 0.12)
    # opp is BB
    if not opp_aggr:
        if my_aggr:  # we opened, opp called
            fo = rate("bb_fold_open", 0.35, 10)
            th = rate("bb_3bet", 0.12, 10)
            return band_range(th * 0.6, 1 - fo) + 0.25 * top_range(th * 0.6)
        return band_range(0.30, 1.0) + 0.3 * top_range(0.3)      # BB checked our limp
    return top_range(rate("bb_3bet", 0.12, 10) * (0.8 if len(opp_aggr) == 1 else 0.4))


def build_combos(cls_w, dead):
    out = []
    for i in np.nonzero(cls_w > 0.02)[0]:
        w = float(cls_w[i])
        for a, b in COMBOS[i]:
            if a in dead or b in dead:
                continue
            out.append([a, b, w])
    return out


def _strength_pct(cards, board):
    """Fraction of random villain combos that `cards` beat on `board` (made hand only)."""
    bc = [CARD[c] for c in board]
    mine = eval7.evaluate([CARD[c] for c in cards] + bc)
    dead = set(board) | set(cards)
    deck = [c for c in CARD if c not in dead]
    win = tot = 0
    for i in range(len(deck)):
        for j in range(i + 1, len(deck), 3):     # subsample for speed
            v = eval7.evaluate([CARD[deck[i]], CARD[deck[j]]] + bc)
            win += (mine > v) + 0.5 * (mine == v)
            tot += 1
    return win / max(1, tot)


def narrow(combos, board, keep, floor):
    """Keep villain's top `keep` fraction of (weighted) combos by made-hand strength
    on `board`; weaker combos keep weight `floor` (bluffs / draws). Soft edge."""
    bcards = [CARD[c] for c in board]
    vals = [eval7.evaluate([CARD[a], CARD[b]] + bcards) for a, b, _ in combos]
    order = sorted(range(len(vals)), key=lambda i: -vals[i])   # strongest first
    tot = sum(c[2] for c in combos) or 1.0
    keep = min(1.0, max(0.03, keep))
    soft = 0.08
    acc = 0.0
    for i in order:
        pos = (acc + combos[i][2] / 2) / tot     # 0 strongest .. 1 weakest
        acc += combos[i][2]
        f = min(1.0, max(0.0, (keep + soft / 2 - pos) / soft))
        combos[i][2] *= floor + (1 - floor) * f
    return combos


def postflop(gs, ctx):
    me = gs["your_bot_id"]
    dbg = ctx["dbg"]
    board = gs["community_cards"]
    hole = gs["your_cards"]
    dead = set(board) | set(hole)
    combos = build_combos(opp_preflop_range(gs, me), dead)
    # range narrowing by the opponent's measured action frequencies (shrunk to priors)
    bwc = rate("bet_when_checked", 0.40, 10)
    rvb = rate("raise_vs_bet", 0.12, 10)
    ftb_ = rate("fold_to_bet", 0.45, 10)
    # bluff share of opp bets, calibrated from showdowns (shrunk to a 15% prior)
    b = min(0.6, rate("bet_bluff", TUNE["bluff_prior"], 8))
    streets = ["flop", "turn", "river"]
    n_board = {"flop": 3, "turn": 4, "river": 5}
    narrowed = []
    for st in streets[:streets.index(gs["street"]) + 1]:
        sa = [a for a in gs["action_log"] if a["street"] == st and a["action"] in ("raise", "all_in", "call", "check", "fold")]
        keep = None
        for i, a in enumerate(sa):
            if a["bot_id"] == me:
                continue
            prev_aggr = any(x["action"] in ("raise", "all_in") for x in sa[:i])
            if a["action"] in ("raise", "all_in"):
                k = rvb if prev_aggr else bwc
                keep = k if keep is None else keep * max(k, 0.3)
            elif a["action"] == "call" and prev_aggr:
                k = 1 - ftb_
                keep = k if keep is None else keep * k
        if keep is not None:
            k = min(0.97, keep)
            floor = float(np.clip(b * k / ((1 - b) * (1 - k)), 0.02, 1.0))
            combos = narrow(combos, board[:n_board[st]], keep, floor)
            narrowed.append(round(keep, 2))
    if not combos:
        combos = build_combos(np.ones(169), dead)
    # eval7's Monte Carlo ignores range weights, so sample combos by weight (with replacement)
    ws = np.array([c[2] for c in combos], dtype=float)
    ws = ws / ws.sum()
    idx = np.random.choice(len(combos), size=400, p=ws)
    rng = [((CARD[combos[i][0]], CARD[combos[i][1]]), 1.0) for i in idx]
    n_eff = float(1.0 / (ws ** 2).sum())
    iters = 2500 if gs["street"] != "river" else 1500
    eq = eval7.py_hand_vs_range_monte_carlo([CARD[c] for c in hole], rng, [CARD[c] for c in board], iters)
    owed, pot = gs["amount_owed"], gs["pot"]
    stack = gs["your_stack"]
    street = gs["street"]
    ftb = rate("fold_to_bet", 0.45, 10)
    dbg.update(bluff_b=round(b, 2), eq=round(eq, 3), n_eff=round(n_eff), keep=narrowed, ftb=round(ftb, 2))
    spr = stack / max(1, pot)

    if owed == 0:
        # value bet
        thr = {"flop": 0.62, "turn": 0.64, "river": 0.66}[street]
        if eq >= thr:
            frac = 0.75 if eq > 0.8 else 0.6
            dbg["line"] = "value"
            return bet(gs, frac * pot)
        # bluff / semi-bluff: more vs folders, more with some equity (draws) before river
        if street == "river":
            p_bluff = 0.45 * ftb if eq < 0.25 else 0.0
        else:
            p_bluff = (0.55 if 0.3 <= eq < thr else 0.3) * ftb
        if random.random() < p_bluff:
            dbg["line"] = "bluff"
            return bet(gs, 0.6 * pot)
        dbg["line"] = "check"
        return {"action": "check"}

    need = owed / (pot + owed)
    dbg["need"] = round(need, 3)
    raise_thr = {"flop": 0.72, "turn": 0.75, "river": 0.80}[street]
    if eq >= raise_thr:
        dbg["line"] = "raise_value"
        if spr < 2.5 or owed > 0.35 * stack:
            return {"action": "all_in"}
        return raise_to(gs, gs["current_bet"] * 2.5 + (pot - owed) * 0.3)
    # equity realisation: before the river we still face future bets (worse out of position)
    oop = gs["seat_to_act"] == gs["bb_seat"]
    rf, rt = TUNE["real_flop"], TUNE["real_turn"]
    real = 1.0 if street == "river" else ((rf[0] if oop else rf[1]) if street == "flop" else (rt[0] if oop else rt[1]))
    dbg["real"] = real
    if eq * real >= need:
        dbg["line"] = "call"
        return {"action": "call"}
    dbg["line"] = "fold"
    return {"action": "fold"}


def bet(gs, amount):
    stack = gs["your_stack"]
    amount = max(gs["blinds"]["bb"], amount)
    if amount >= 0.45 * stack:
        return {"action": "all_in"}
    return raise_to(gs, gs["your_bet_this_street"] + amount)


# ------------------------------------------------------------------ entry point
def decide(gs):
    if gs.get("type") == "warmup":
        return {"action": "check"}
    try:
        return _decide(gs)
    except Exception as e:  # never raise: fall back to check/fold
        return dict(passive(gs), debug={"err": repr(e)[:200]})


def _decide(gs):
    me = gs["your_bot_id"]
    if gs["hand_num"] == 0 and not _seen_hands and OPP["hands"] == 0:
        pass
    if gs["community_cards"]:
        BOARDS[gs["hand_num"]] = list(gs["community_cards"])
    _update_model(gs, me)
    bb = gs["blinds"]["bb"]
    opp = next(p for p in gs["players"] if p["bot_id"] != me)
    my_total = gs["your_stack"] + gs["your_bet_this_street"]
    opp_total = opp["stack"] + opp["bet_this_street"]
    ctx = {"bb": bb, "ante": gs["blinds"].get("ante", 0), "ci": cls_of(gs["your_cards"]),
           "eff_bb": min(my_total, opp_total) / bb, "opp_stack_behind": opp["stack"],
           "my_in": gs["your_bet_this_street"], "dbg": {}}
    if gs["street"] == "preflop":
        act = preflop(gs, ctx)
    else:
        act = postflop(gs, ctx)
    act["debug"] = ctx["dbg"]
    return act
