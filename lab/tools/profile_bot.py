"""Profile the hero's decide() in real in-process matches (read-only on the bot).

  python -m lab.tools.profile_bot --hero my_bots/redteamers007 --opps tag,lag,station,maniac,e_gunslinger --matches 6
  python -m lab.tools.profile_bot --matches 4 --flips 5      # also measure Monte Carlo decision instability

Prints: think time (local ms, and x tf = emulated half-core) mean/p50/p99/max per street, the share of the 2 s
budget used, the top 15 hotspots by cumulative time inside the hero's decide(), and (with --flips K) how often
re-running the same postflop decision with K other RNG seeds changes the action (MC noise near thresholds).
Only the hero's decide() calls are profiled; opponents and the engine are not.
"""
import argparse
import copy
import cProfile
import io
import pstats
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from pokercore import structures  # noqa: E402
from pokercore.seeds import derive_seed  # noqa: E402
from pokercore.table import MatchConfig, play_match  # noqa: E402
from lab.inproc import InProcSeat, _seed_rngs  # noqa: E402
from lab.opponents.sets import resolve_opps  # noqa: E402
from lab import run as R  # noqa: E402


class _Null:
    final = None

    def emit(self, t, **d):
        return None


ACTS = []   # every hero action in order (decision fingerprint)


class ProfSeat(InProcSeat):
    """InProcSeat whose module.decide is wrapped with cProfile + per-street timing."""

    def __init__(self, *a, prof, times, flips=0, flip_log=None, **k):
        super().__init__(*a, **k)
        self.prof, self.times, self.flips, self.flip_log = prof, times, flips, flip_log

    def start(self):
        super().start()
        inner = self.module.decide

        def wrapped(gs):
            if gs.get("type") == "warmup":
                return inner(gs)
            snap = copy.deepcopy(gs) if self.flips and gs.get("street") != "preflop" else None
            t0 = time.perf_counter()
            if self.prof is not None:
                self.prof.enable()
            try:
                out = inner(gs)
            finally:
                if self.prof is not None:
                    self.prof.disable()
            self.times[gs.get("street", "?")].append((time.perf_counter() - t0) * 1000)
            ACTS.append((out.get("action"), out.get("amount")))
            if snap is not None:
                # re-decide the same state with other seeds (idempotent: model updates skip seen hands)
                st = (random.getstate(), np.random.get_state())
                acts, eqs = [], []
                for f in range(self.flips):
                    _seed_rngs(derive_seed(self.bot_seed, "flip", gs.get("hand_num"), len(gs.get("action_log") or []), f))
                    o = inner(copy.deepcopy(snap))
                    acts.append(o.get("action"))
                    eqs.append((o.get("debug") or {}).get("eq"))
                random.setstate(st[0])
                np.random.set_state(st[1])
                dbg = out.get("debug") or {}
                self.flip_log.append({"street": gs["street"], "act": out.get("action"), "alts": acts,
                                      "line": dbg.get("line"), "eq": dbg.get("eq"), "need": dbg.get("need"),
                                      "eqs": eqs, "owed": gs.get("amount_owed", 0) > 0})
            return out

        self.module.decide = wrapped


def pct(xs, q):
    return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else 0.0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--hero", default="my_bots/redteamers007")
    ap.add_argument("--opps", default="tag,lag,station,maniac,e_gunslinger")
    ap.add_argument("--matches", type=int, default=6, help="matches per opponent (alternating seats)")
    ap.add_argument("--seeds", default="dev")
    ap.add_argument("--tf", type=float, default=2.0)
    ap.add_argument("--flips", type=int, default=0, help="re-decide each postflop state K times with other seeds")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--noprof", action="store_true", help="timing only (cProfile adds overhead to think times)")
    ap.add_argument("--fix-imports", action="store_true",
                    help="alias sys.modules['eval7.struct'/'eval7.time'] (tests the suggested seed() speedup)")
    a = ap.parse_args(argv)
    if a.fix_imports:
        import struct as _st, time as _tm
        sys.modules["eval7.struct"], sys.modules["eval7.time"] = _st, _tm
    hero = f"lab/snapshots/{a.hero[5:]}" if a.hero.startswith("snap:") else a.hero
    try:
        opps = resolve_opps(a.opps)
    except ValueError:
        opps = resolve_opps(",".join(t for t in a.opps.split(",") if not t.startswith("e_")))
    ext = dict(resolve_opps("ext"))
    opps = [(l, s) for l, s in opps] + [(t, ext[t]) for t in a.opps.split(",") if t in ext and t not in dict(opps)]

    prof = None if a.noprof else cProfile.Profile()
    times = defaultdict(list)
    flip_log = []
    t0 = time.time()
    n_hands = 0
    for label, spec in opps:
        for k in range(a.matches):
            seed = derive_seed("profile", a.seeds, label, k)
            hs = ProfSeat(R.HERO, hero, derive_seed(seed, "bot", R.HERO), time_factor=a.tf, capture_debug=False,
                          enforce_time=False, prof=prof, times=times, flips=a.flips, flip_log=flip_log)
            os_ = InProcSeat(R.OPP, spec, derive_seed(seed, "bot", R.OPP), time_factor=a.tf, capture_debug=False)
            seats = [os_, hs] if k % 2 else [hs, os_]
            cfg = MatchConfig(mode="freezeout", hands=1500, starting_stack=10_000,
                              structure=structures.parse("standard", 10_000), seed=seed)
            res = play_match(seats, cfg, f"prof{k}", _Null())
            n_hands += res["hands"]
        print(f"  {label}: {a.matches} matches done ({time.time() - t0:.0f}s)", flush=True)

    allt = sorted(x for v in times.values() for x in v)
    print(f"\n{len(allt)} hero decisions in {n_hands} hands, {sum(allt) / 1000:.1f}s of decide() time "
          f"(local ms; emulated = x{a.tf})\n")
    print(f"{'street':8} {'n':>6} {'mean':>8} {'p50':>8} {'p99':>8} {'max':>8}   emul p99   budget used (p99/2000ms)")
    for st in ("preflop", "flop", "turn", "river", "ALL"):
        xs = allt if st == "ALL" else sorted(times.get(st, []))
        if not xs:
            continue
        p99 = pct(xs, 0.99)
        print(f"{st:8} {len(xs):6d} {sum(xs) / len(xs):8.2f} {pct(xs, 0.5):8.2f} {p99:8.2f} {xs[-1]:8.2f}"
              f"   {p99 * a.tf:8.1f}   {100 * p99 * a.tf / 2000:.1f}%")
    import hashlib
    print(f"\ndecision fingerprint: {len(ACTS)} actions sha1={hashlib.sha1(repr(ACTS).encode()).hexdigest()[:16]}")
    if prof is not None:
        s = io.StringIO()
        ps = pstats.Stats(prof, stream=s).sort_stats("cumulative")
        ps.print_stats(a.top + 8)
        print("\nTop hotspots by cumulative time (hero decide() only):")
        print("\n".join(s.getvalue().splitlines()[:a.top + 18]))
        s = io.StringIO()
        pstats.Stats(prof, stream=s).sort_stats("tottime").print_stats(12)
        print("\nTop by own (tottime):")
        print("\n".join(s.getvalue().splitlines()[4:30]))

    if flip_log:
        by = defaultdict(lambda: [0, 0])
        close = defaultdict(lambda: [0, 0])
        for r in flip_log:
            flip = any(x != r["act"] for x in r["alts"])
            by[r["street"]][0] += flip
            by[r["street"]][1] += 1
            key = r["line"] or "?"
            close[key][0] += flip
            close[key][1] += 1
        print(f"\nMC decision instability (postflop, {a.flips} re-seeds each): share of decisions whose action changes")
        for st in ("flop", "turn", "river"):
            if by[st][1]:
                print(f"  {st:6} {by[st][0]}/{by[st][1]} = {100 * by[st][0] / by[st][1]:.1f}%")
        sds = [float(np.std([r["eq"]] + r["eqs"])) for r in flip_log if r["eq"] is not None and None not in r["eqs"]]
        fo = [any(x != r["act"] for x in r["alts"]) for r in flip_log if r["owed"]]
        print(f"  facing a bet (no deliberate randomness, flips = pure MC noise): {sum(fo)}/{len(fo)} = "
              f"{100 * sum(fo) / max(1, len(fo)):.1f}%")
        print(f"  equity estimate SD across seeds: mean {np.mean(sds):.4f}  p90 {np.percentile(sds, 90):.4f}")
        print("  by chosen line: " + "  ".join(f"{k}={v[0]}/{v[1]}" for k, v in sorted(close.items())))
        print("  (bluff lines are randomised on purpose; value/call/fold/raise_value flips are MC noise)")


if __name__ == "__main__":
    main()
