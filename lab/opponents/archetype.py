"""Parameterised sparring bot (lab only). configure(params) sets the style.

Presets: station, maniac, nit, tag, lag, overfolder, shover, trapper, random, minraiser.
`rand=<k>` draws all parameters at random from seed k (generalisation set).
Any parameter can be overridden: "lab/opponents/archetype.py::preset=tag,bluff=0.5".
"""
import json
import random
from pathlib import Path

import eval7

_PF = json.loads((Path(__file__).resolve().parents[1] / "data/preflop.json").read_text())
_CLS = {c: i for i, c in enumerate(_PF["classes"])}
_ncombo = [6 if len(c) == 2 else (4 if c[2] == "s" else 12) for c in _PF["classes"]]
_order = sorted(range(169), key=lambda i: -_PF["eq_random"][i])
PCT = [0.0] * 169      # fraction of combos strictly better (0 = AA)
_acc = 0
for _i in _order:
    PCT[_i] = _acc / 1326
    _acc += _ncombo[_i]
RANKS = "AKQJT98765432"

PRESETS = {
    "station":    dict(vpip=0.95, pfr=0.05, threebet=0.02, bet_eq=0.80, bluff=0.00, call_margin=1.0, raise_eq=0.95, size=0.5),
    "maniac":     dict(vpip=0.95, pfr=0.85, threebet=0.45, bet_eq=0.35, bluff=0.65, call_margin=0.25, raise_eq=0.60, size=1.0, pf_size=4.0),
    "nit":        dict(vpip=0.22, pfr=0.16, threebet=0.05, bet_eq=0.70, bluff=0.02, call_margin=-0.05, raise_eq=0.85, size=0.6),
    "tag":        dict(vpip=0.50, pfr=0.40, threebet=0.12, bet_eq=0.60, bluff=0.20, call_margin=0.05, raise_eq=0.80, size=0.66),
    "lag":        dict(vpip=0.75, pfr=0.60, threebet=0.25, bet_eq=0.55, bluff=0.35, call_margin=0.10, raise_eq=0.75, size=0.75),
    "overfolder": dict(vpip=0.55, pfr=0.30, threebet=0.05, bet_eq=0.60, bluff=0.15, call_margin=-0.25, raise_eq=0.85, size=0.6),
    "shover":     dict(shove_bb=10_000, shove_range=0.45, vpip=0.45),
    "trapper":    dict(vpip=0.55, pfr=0.20, threebet=0.05, bet_eq=0.75, bluff=0.10, call_margin=0.10, raise_eq=0.70, size=0.6, slowplay=0.7),
    "minraiser":  dict(vpip=0.70, pfr=0.60, threebet=0.20, bet_eq=0.55, bluff=0.30, call_margin=0.05, raise_eq=0.80, size=0.0, pf_size=2.0),
    "random":     dict(random=1),
}
DEFAULT = dict(vpip=0.5, pfr=0.3, threebet=0.1, bet_eq=0.6, bluff=0.15, call_margin=0.0,
               raise_eq=0.8, size=0.66, pf_size=2.5, shove_bb=12, shove_range=0.4,
               slowplay=0.0, random=0)
P = dict(DEFAULT, **PRESETS["tag"])


def configure(params):
    global P
    P = dict(DEFAULT)
    if "rand" in params:
        r = random.Random(int(params["rand"]) * 7919 + 17)
        P.update(vpip=r.uniform(0.15, 0.95), bet_eq=r.uniform(0.4, 0.85), bluff=r.uniform(0, 0.6),
                 call_margin=r.uniform(-0.3, 0.4), raise_eq=r.uniform(0.6, 0.95),
                 size=r.choice([0.33, 0.5, 0.66, 1.0, 1.5]), pf_size=r.choice([2, 2.5, 3, 4]),
                 shove_bb=r.uniform(3, 20), shove_range=r.uniform(0.2, 0.7), slowplay=r.uniform(0, 0.4))
        P["pfr"] = P["vpip"] * r.uniform(0.1, 0.9)
        P["threebet"] = P["pfr"] * r.uniform(0.1, 0.6)
    if "preset" in params:
        P.update(PRESETS[params["preset"]])
    P.update({k: v for k, v in params.items() if k not in ("preset", "rand")})


def hand_pct(cards):
    a, b = cards
    ra, rb = RANKS.index(a[0]), RANKS.index(b[0])
    if ra > rb:
        a, b, ra, rb = b, a, rb, ra
    if ra == rb:
        cls = a[0] + b[0]
    else:
        cls = a[0] + b[0] + ("s" if a[1] == b[1] else "o")
    return PCT[_CLS[cls]]


def eq_random(cards, board, iters=300):
    hero = [eval7.Card(c) for c in cards]
    bd = [eval7.Card(c) for c in board]
    return eval7.py_hand_vs_range_monte_carlo(hero, _ANY, bd, iters)


_ANY = eval7.HandRange("22+,A2+,K2+,Q2+,J2+,T2+,92+,82+,72+,62+,52+,42+,32").hands


def _raise(gs, to):
    to = int(max(gs["min_raise_to"], to))
    if to >= gs["your_stack"] + gs["your_bet_this_street"]:
        return {"action": "all_in"}
    return {"action": "raise", "amount": to}


def _passive(gs):
    return {"action": "check"} if gs["can_check"] else {"action": "fold"}


def _random(gs):
    r = random.random()
    if r < 0.25:
        return _passive(gs)
    if r < 0.6:
        return {"action": "call"}
    if r < 0.9:
        lo, hi = gs["min_raise_to"], gs["min_raise_to"] + gs["pot"]
        return _raise(gs, random.randint(lo, max(lo, hi)))
    return {"action": "all_in"}


def decide(gs):
    if gs.get("type") == "warmup":
        return {"action": "check"}
    if P.get("random"):
        return _random(gs)
    bb = gs["blinds"]["bb"]
    me = gs["seat_to_act"]
    opp_stack = max(p["stack"] + p["bet_this_street"] for p in gs["players"] if p["seat"] != me)
    eff = min(gs["your_stack"] + gs["your_bet_this_street"], opp_stack) / bb
    owed, pot = gs["amount_owed"], gs["pot"]
    if gs["street"] == "preflop":
        pct = hand_pct(gs["your_cards"])
        raises = sum(1 for a in gs["action_log"] if a["street"] == "preflop" and a["action"] in ("raise", "all_in"))
        if eff <= P["shove_bb"]:
            if raises == 0:
                return {"action": "all_in"} if pct < P["shove_range"] else _passive(gs)
            return {"action": "call"} if pct < P["shove_range"] * 0.75 else _passive(gs)
        if raises == 0:
            if pct < P["pfr"]:
                return _raise(gs, P["pf_size"] * bb)
            if pct < P["vpip"]:
                return {"action": "call"}
            return _passive(gs)
        if pct < P["threebet"] / raises:
            return _raise(gs, gs["current_bet"] * 3)
        price = owed / max(1, pot + owed)
        if pct < P["vpip"] * (1.2 - price) or (owed <= bb and pct < P["vpip"]):
            return {"action": "call"}
        return _passive(gs)
    eq = eq_random(gs["your_cards"], gs["community_cards"])
    if owed == 0:
        if eq > P["bet_eq"]:
            if random.random() < P["slowplay"]:
                return {"action": "check"}
            return _raise(gs, max(bb, P["size"] * pot) if P["size"] > 0 else bb)
        if random.random() < P["bluff"] * (1 - eq):
            return _raise(gs, max(bb, (P["size"] or 0.5) * pot))
        return {"action": "check"}
    price = owed / (pot + owed)
    if eq > P["raise_eq"]:
        return _raise(gs, gs["current_bet"] * 2.5 + pot * 0.5)
    if eq >= price + 0.12 - P["call_margin"]:
        return {"action": "call"}
    if random.random() < P["bluff"] * 0.25:
        return _raise(gs, gs["current_bet"] * 3)
    return {"action": "fold"}
