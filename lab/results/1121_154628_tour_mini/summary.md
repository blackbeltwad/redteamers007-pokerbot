# Tournament sim `mini`  hero=my_bots/redteamers007  field=tag,lag,nit,station (5 bots)  rr=1  tours=1  seeds=dev  tf=2.0

Assumptions: pairing win=1, draw=0.5, loss=0; qual ties -> match wins -> seeded coin; KO = duplicate pairs until one bot wins a pair (max 5), then higher qual rank; 1v4, 2v3, final.

Throughput: 34 matches in 18s = **1.88 matches/s** with 4 workers (mean match wall 1.40s, 62 hands/match). Crashes: 0. Hero timeouts: 0, hero p99 think worst match 129 ms (emulated).
Slowest bots (mean wall s per match they play): lag 1.68, HERO 1.64, station 1.49, tag 1.34, nit 0.73

**HERO: P(top 4) = 100%  P(top 2) = 100%  P(win) = 100%  mean qual rank 1.0**  (n=1 tournaments; binomial SE of a probability p is sqrt(p(1-p)/1))

| bot | mean qual rank | mean pts | P(top 4) | P(top 2) | P(win) |
|---|---|---|---|---|---|
| **HERO** | 1.0 | 3.0 | 100% | 100% | 100% |
| tag | 2.0 | 2.5 | 100% | 0% | 0% |
| nit | 3.0 | 2.5 | 100% | 100% | 0% |
| lag | 4.0 | 2.0 | 100% | 0% | 0% |
| station | 5.0 | 0.0 | 0% | 0% | 0% |

## Hero qualification pairing record (WW-D-LL, all tours and repetitions)

| opp | WW | D | LL | pair score |
|---|---|---|---|---|
| tag | 0 | 1 | 0 | 0.50 |
| nit | 0 | 1 | 0 | 0.50 |
| lag | 1 | 0 | 0 | 1.00 |
| station | 1 | 0 | 0 | 1.00 |

## Who knocks the hero out

KO-stage eliminations of the hero: none
Tours where hero missed the top 4: 0/1; pairing losses (LL) in those tours: none
KO pair record: lag 1-3-0, nit 1-1-0
