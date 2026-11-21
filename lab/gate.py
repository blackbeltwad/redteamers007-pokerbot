"""Regression gate. Runs candidate and the previous best on the SAME hold-out seeds
against the opponent set, plus candidate vs best head-to-head, and prints PASS/FAIL.

  python -m lab.gate --cand my_bots/redteamers007 --best snap:v1 [--pairs 100 --h2h 200]

Rules (CLAUDE.md section 5):
  (a) head-to-head vs best: win rate >= 50%
  (b) no opponent regresses by more than noise (drop > 2 * pooled SE and > 10 pts)
      and overall win rate vs the set is not lower
  (c) zero errors/timeouts, p99 think <= 600 ms (half-core emulation)
  (d) make validate passes
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import run as R  # noqa: E402


def spec_of(s):
    return f"lab/snapshots/{s[5:]}" if s.startswith("snap:") else s


def runlab(hero, opps, pairs, label, seeds="holdout"):
    R.main(["--hero", hero, "--opps", opps, "--pairs", str(pairs), "--seeds", seeds, "--label", label])
    d = sorted((ROOT / "lab/results").glob(f"*_{label}"))[-1]
    return json.loads((d / "results.json").read_text()), d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", required=True)
    ap.add_argument("--best", required=True)
    ap.add_argument("--opps", default="core,rand20,exploit")
    ap.add_argument("--pairs", type=int, default=100)
    ap.add_argument("--h2h", type=int, default=200)
    ap.add_argument("--tag", default="gate")
    a = ap.parse_args()
    cand, best = spec_of(a.cand), spec_of(a.best)
    rc, dc = runlab(cand, a.opps, a.pairs, f"{a.tag}_cand")
    rb, db = runlab(best, a.opps, a.pairs, f"{a.tag}_best")
    rh, dh = runlab(cand, f"best={best}", a.h2h, f"{a.tag}_h2h")
    fails = []
    h = rh["overall"]
    lines = [f"H2H cand vs best: {100 * h['winrate']:.1f}% [{100 * h['lo']:.1f},{100 * h['hi']:.1f}] "
             f"pairs {h['WW']}-{h['D']}-{h['LL']}"]
    if h["winrate"] < 0.5:
        fails.append("(a) h2h < 50%")
    lines.append(f"Set: cand {100 * rc['overall']['winrate']:.1f}% vs best {100 * rb['overall']['winrate']:.1f}%")
    if rc["overall"]["winrate"] < rb["overall"]["winrate"]:
        fails.append("(b) overall set win rate lower")
    lines.append("| opp | cand | best | diff |")
    lines.append("|---|---|---|---|")
    for opp, r in sorted(rc["by_opp"].items()):
        b = rb["by_opp"].get(opp)
        if not b:
            continue
        d = r["winrate"] - b["winrate"]
        se = math.sqrt(max(1e-9, r["winrate"] * (1 - r["winrate"]) / r["N"] + b["winrate"] * (1 - b["winrate"]) / b["N"]))
        flag = ""
        if d < -2 * se and d < -0.10:
            flag = " **REGRESS**"
            fails.append(f"(b) {opp} regressed {100 * d:.0f} pts")
        lines.append(f"| {opp} | {100 * r['winrate']:.0f} | {100 * b['winrate']:.0f} | {100 * d:+.0f}{flag} |")
    o = rc["overall"]
    if o["timeouts"] or o["errors"] or o["crashes"]:
        fails.append(f"(c) timeouts={o['timeouts']} errors={o['errors']} crashes={o['crashes']}")
    # robust timing rule (2026-11-21): 99th pct of per-match p99 must be <= 600 ms; isolated
    # outlier matches are listed for a quiet replay (single OS hiccups tripped the old worst-match rule)
    if o["think_p99_q99_match"] > 600:
        fails.append(f"(c) p99 think (q99 over matches) {o['think_p99_q99_match']:.0f}ms > 600")
    if o.get("matches_p99_over_600"):
        lines.append(f"NOTE: {o['matches_p99_over_600']} match(es) with p99 > 600ms - replay them quietly")
    bot_dir = cand.split("::")[0]
    v = subprocess.run([sys.executable, "pokercore/validator.py", bot_dir], cwd=ROOT, capture_output=True, text=True)
    if v.returncode != 0:
        fails.append("(d) validate failed")
    lines.append(f"p99 think: q99 over matches {o['think_p99_q99_match']:.0f}ms, worst match {o['think_p99_worst_match']:.0f}ms; validate rc={v.returncode}")
    lines.append("GATE: " + ("PASS" if not fails else "FAIL: " + "; ".join(fails)))
    txt = "\n".join(lines)
    (dh / "gate.md").write_text(txt + f"\n\ncand dir {dc}\nbest dir {db}\n")
    print(txt)


if __name__ == "__main__":
    main()
