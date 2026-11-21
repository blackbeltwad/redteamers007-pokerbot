# ext_smoke  hero=snap:v1  seeds=dev  pairs/opp=1  tf=2.0

**Overall match win 0.0% [0.0, 100.0]**  N=0  pairs WW-D-LL 0-0-0  timeouts=0 errors=0 crashes=28  think mean=nanms p99(worst match)=0ms

| opp | win% | 95% CI | WW-D-LL | hands | hero bb/100 | hero VPIP/PFR/3B | hero AF | opp VPIP/PFR/3B | opp FtbF/T/R | opp AF |
|---|---|---|---|---|---|---|---|---|---|---|

Hero result by final line (bb/100 hands contribution, count):   ...  

Hero overall: VPIP=-  PFR=-  3B=-  F3B=-  CB=-  FtbF=-  FtbT=-  FtbR=-  AF=-  WTSD=-  SDW=-  AI/100=-  bb/100=-

Side: bluff chips/1000h=0  7-2 won/dealt=0 (0 dealt)  weakest win SD: None  best comeback share=None

CRASHES:
```
Traceback (most recent call last):
  File "/Users/wad/src/poker-hackathon-kit/lab/run.py", line 187, in play_one
    res = play_match(seats, cfg, f"p{pair}{'b' if swap else 'a'}", rec)
  File "/Users/wad/src/poker-hackathon-kit/pokercore/table.py", line 346, in play_match
    warm = warm_up(seats)
  File "/Users/wad/src/poker-hackathon-kit/pokercore/table.py", line 313, in warm_up
    s.start()
  File "/Users/wad/src/poker-hackathon-kit/lab/inproc.py", line 115, in start
    self.module = load_module(self.spec)
  File "/Users/wad/src/poker-hackathon-kit/lab/inproc.py", line 68, in load_module
    module = importlib.util.module_from_spec(mspec)
  File "<frozen importlib._bootstrap>", line 568, in module_from_spec
AttributeError: 'NoneType' object has no attribute 'loader'

```
