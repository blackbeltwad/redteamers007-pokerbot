"""Docker fidelity check: replay a `play.py --docker --log` match in-process (same names/seeds) and compare decisions.

  python play.py my_bots/redteamers007 bots/caller --docker --seed 1 --log /tmp/d1.jsonl
  python lab/tools/fidelity.py my_bots/redteamers007,bots/caller 1 /tmp/d1.jsonl
Prints whether every decision is identical, plus our real-sandbox think times and any errors.
"""
import json, sys
sys.path.insert(0, '.')
from pokercore import structures
from pokercore.seeds import derive_seed
from pokercore.table import MatchConfig, play_match
from lab.inproc import InProcSeat
class L:
    def __init__(s): s.ev=[]
    def emit(s,t,**d): e={"type":t,**d}; s.ev.append(e); return e
bots, seed, dockerlog = sys.argv[1].split(','), int(sys.argv[2]), sys.argv[3]
names=[b.rstrip('/').split('/')[-1] for b in bots]
seats=[InProcSeat(n,b,derive_seed(seed,"bot",n),time_factor=1.0,enforce_time=False) for n,b in zip(names,bots)]
cfg=MatchConfig(mode="freezeout",hands=2000,starting_stack=10000,structure=structures.parse("standard",10000),seed=seed)
lg=L(); play_match(seats,cfg,"local",lg)
fast=[(e["hand"],e["deltas"]) for e in lg.ev if e["type"]=="hand_end"]
dock=[(e["hand"],e["deltas"]) for e in map(json.loads,open(dockerlog)) if e["type"]=="hand_end"]
acts_f=[(e["hand"],e["bot"],e["applied"]["action"],e["applied"]["amount"]) for e in lg.ev if e["type"]=="decision"]
dl=[json.loads(l) for l in open(dockerlog)]
acts_d=[(e["hand"],e["bot"],e["applied"]["action"],e["applied"]["amount"]) for e in dl if e["type"]=="decision"]
think=[e["think_ms"] for e in dl if e["type"]=="decision" and e["bot"]==names[0] and e.get("think_ms") is not None]
errs=[e.get("error") for e in dl if e["type"]=="decision" and e.get("error")]
think.sort()
first_diff=next((i for i,(a,b) in enumerate(zip(acts_f,acts_d)) if a!=b),None)
print(f"seed {seed}: hands fast={len(fast)} docker={len(dock)} | decisions identical={acts_f==acts_d} (first diff idx {first_diff}) | "
      f"our docker think ms mean={sum(think)/max(1,len(think)):.1f} p99={think[int(len(think)*.99)] if think else 0:.0f} max={think[-1] if think else 0:.0f} | errors={errs[:3]}")
