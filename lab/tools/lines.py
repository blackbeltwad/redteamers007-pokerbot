"""Hero result by final decision line for a run dir: python -m lab.tools.lines <dir> [opp] [top]"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lab import run as R
d = Path(sys.argv[1]); opp = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "-" else None
top = int(sys.argv[3]) if len(sys.argv) > 3 else 12
ms = [json.loads(l) for l in open(d / "matches.jsonl")]
ms = [m for m in ms if "crash" not in m and (opp is None or m["opp"] == opp)]
h = R.aggregate(ms)["hero_counters"]; n = h["hands"]
rows = sorted(((k[2:-2], v, h.get(k[:-2] + "|bb", 0)) for k, v in h.items() if k.startswith("L|") and k.endswith("|n")), key=lambda x: x[2])
for k, c, b in rows[:top] + [("...", 0, 0)] + rows[-6:]:
    print(f"{k:30s} n={c:5.0f} bb/100={100*b/n:+7.1f} per={b/max(c,1):+6.2f}")
