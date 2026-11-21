# Tournament sim `smoke`  hero=my_bots/redteamers007  field=core (13 bots)  rr=1  tours=2  seeds=dev  tf=2.0

Assumptions: pairing win=1, draw=0.5, loss=0; qual ties -> match wins -> seeded coin; KO = duplicate pairs until one bot wins a pair (max 5), then higher qual rank; 1v4, 2v3, final.

Throughput: 328 matches in 59s = **5.53 matches/s** with 4 workers (mean match wall 0.71s, 57 hands/match). Crashes: 0. Hero timeouts: 1, hero p99 think worst match 2671 ms (emulated).

**HERO: P(top 4) = 100%  P(top 2) = 100%  P(win) = 100%  mean qual rank 1.0**  (n=2 tournaments; binomial SE of a probability p is sqrt(p(1-p)/2))

| bot | mean qual rank | mean pts | P(top 4) | P(top 2) | P(win) |
|---|---|---|---|---|---|
| **HERO** | 1.0 | 9.5 | 100% | 100% | 100% |
| overfolder | 2.0 | 8.5 | 100% | 100% | 0% |
| nit | 4.0 | 7.5 | 50% | 0% | 0% |
| tag | 4.5 | 7.5 | 50% | 0% | 0% |
| lag | 5.0 | 7.8 | 50% | 0% | 0% |
| maniac | 6.5 | 6.5 | 50% | 0% | 0% |
| shover | 7.0 | 6.8 | 0% | 0% | 0% |
| minraiser | 8.0 | 5.8 | 0% | 0% | 0% |
| trapper | 8.5 | 6.0 | 0% | 0% | 0% |
| station | 9.0 | 5.0 | 0% | 0% | 0% |
| random | 10.5 | 4.5 | 0% | 0% | 0% |
| kit_caller | 12.0 | 1.8 | 0% | 0% | 0% |
| kit_template | 13.0 | 1.0 | 0% | 0% | 0% |

## Hero qualification pairing record (WW-D-LL, all tours and repetitions)

| opp | WW | D | LL | pair score |
|---|---|---|---|---|
| maniac | 0 | 1 | 1 | 0.25 |
| shover | 0 | 2 | 0 | 0.50 |
| tag | 0 | 2 | 0 | 0.50 |
| nit | 1 | 1 | 0 | 0.75 |
| random | 1 | 1 | 0 | 0.75 |
| trapper | 1 | 1 | 0 | 0.75 |
| lag | 2 | 0 | 0 | 1.00 |
| overfolder | 2 | 0 | 0 | 1.00 |
| station | 2 | 0 | 0 | 1.00 |
| minraiser | 2 | 0 | 0 | 1.00 |
| kit_template | 2 | 0 | 0 | 1.00 |
| kit_caller | 2 | 0 | 0 | 1.00 |

## Who knocks the hero out

KO-stage eliminations of the hero: none
Tours where hero missed the top 4: 0/2; pairing losses (LL) in those tours: none
KO pair record: maniac 1-0-0, overfolder 2-1-0, tag 1-0-0
