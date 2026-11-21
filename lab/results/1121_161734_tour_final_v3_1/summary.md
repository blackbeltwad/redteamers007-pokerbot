# Tournament sim `final_v3_1`  hero=lab/snapshots/v3_1  field=core,ext,dataset (40 bots)  rr=1  tours=4  seeds=holdout  tf=2.0

Assumptions: pairing win=1, draw=0.5, loss=0; qual ties -> match wins -> seeded coin; KO = duplicate pairs until one bot wins a pair (max 5), then higher qual rank; 1v4, 2v3, final.

Throughput: 6298 matches in 822s = **7.66 matches/s** with 15 workers (mean match wall 2.02s, 75 hands/match). Crashes: 0. Hero timeouts: 0, hero p99 think worst match 662 ms (emulated).
Slowest bots (mean wall s per match they play): e_atharva 10.66, e_txn_floorfix 7.64, e_txn_mybot 7.08, e_txn_cfr 7.01, e_advit_strong 1.99, e_range_mc 1.77

**HERO: P(top 4) = 100%  P(top 2) = 75%  P(win) = 75%  mean qual rank 1.0**  (n=4 tournaments; binomial SE of a probability p is sqrt(p(1-p)/4))

| bot | mean qual rank | mean pts | P(top 4) | P(top 2) | P(win) |
|---|---|---|---|---|---|
| **HERO** | 1.0 | 30.5 | 100% | 75% | 75% |
| e_advit_strong | 4.0 | 25.4 | 50% | 50% | 0% |
| e_tumble_dutch | 4.5 | 25.0 | 50% | 50% | 25% |
| e_gunslinger | 4.5 | 25.5 | 50% | 0% | 0% |
| overfolder | 7.0 | 24.5 | 75% | 25% | 0% |
| d_MrBlonde | 9.2 | 23.9 | 50% | 0% | 0% |
| e_opp_modeler | 12.0 | 22.8 | 0% | 0% | 0% |
| d_Bill | 12.8 | 22.8 | 0% | 0% | 0% |
| d_Hattori | 13.5 | 22.4 | 0% | 0% | 0% |
| tag | 13.8 | 22.5 | 25% | 0% | 0% |
| d_Gogo | 13.8 | 22.4 | 0% | 0% | 0% |
| d_Budd | 14.0 | 22.1 | 0% | 0% | 0% |
| d_MrPink | 14.8 | 22.1 | 0% | 0% | 0% |
| e_tumble_q1 | 15.5 | 21.6 | 0% | 0% | 0% |
| d_Eddie | 15.5 | 21.9 | 0% | 0% | 0% |
| d_MrWhite | 15.8 | 21.9 | 0% | 0% | 0% |
| d_MrBlue | 16.2 | 21.5 | 0% | 0% | 0% |
| d_MrOrange | 16.5 | 21.6 | 0% | 0% | 0% |
| d_ORen | 18.8 | 21.0 | 0% | 0% | 0% |
| lag | 19.2 | 21.1 | 0% | 0% | 0% |
| d_Pluribus | 19.5 | 21.0 | 0% | 0% | 0% |
| d_Joe | 20.5 | 20.8 | 0% | 0% | 0% |
| d_MrBrown | 22.2 | 20.4 | 0% | 0% | 0% |
| shover | 23.5 | 19.8 | 0% | 0% | 0% |
| e_txn_floorfix | 24.0 | 20.1 | 0% | 0% | 0% |
| nit | 24.2 | 19.8 | 0% | 0% | 0% |
| minraiser | 24.2 | 18.9 | 0% | 0% | 0% |
| e_txn_cfr | 24.2 | 19.4 | 0% | 0% | 0% |
| e_lomaan | 24.2 | 19.2 | 0% | 0% | 0% |
| e_adapt_exploit | 24.5 | 19.1 | 0% | 0% | 0% |
| e_txn_mybot | 26.0 | 19.0 | 0% | 0% | 0% |
| maniac | 29.8 | 17.2 | 0% | 0% | 0% |
| trapper | 34.0 | 14.6 | 0% | 0% | 0% |
| e_range_mc | 34.0 | 14.5 | 0% | 0% | 0% |
| e_atharva | 34.2 | 14.4 | 0% | 0% | 0% |
| e_langchen | 35.8 | 12.5 | 0% | 0% | 0% |
| random | 36.2 | 11.9 | 0% | 0% | 0% |
| station | 37.5 | 10.4 | 0% | 0% | 0% |
| kit_template | 39.2 | 2.4 | 0% | 0% | 0% |
| kit_caller | 39.8 | 2.4 | 0% | 0% | 0% |

## Hero qualification pairing record (WW-D-LL, all tours and repetitions)

| opp | WW | D | LL | pair score |
|---|---|---|---|---|
| minraiser | 1 | 1 | 2 | 0.38 |
| nit | 0 | 4 | 0 | 0.50 |
| d_Pluribus | 1 | 2 | 1 | 0.50 |
| d_Gogo | 0 | 4 | 0 | 0.50 |
| d_ORen | 0 | 4 | 0 | 0.50 |
| shover | 1 | 3 | 0 | 0.62 |
| lag | 1 | 3 | 0 | 0.62 |
| e_advit_strong | 1 | 3 | 0 | 0.62 |
| d_Bill | 1 | 3 | 0 | 0.62 |
| d_Joe | 1 | 3 | 0 | 0.62 |
| d_Budd | 2 | 1 | 1 | 0.62 |
| overfolder | 2 | 2 | 0 | 0.75 |
| maniac | 2 | 2 | 0 | 0.75 |
| tag | 2 | 2 | 0 | 0.75 |
| e_opp_modeler | 2 | 2 | 0 | 0.75 |
| e_langchen | 2 | 2 | 0 | 0.75 |
| d_MrPink | 2 | 2 | 0 | 0.75 |
| e_tumble_dutch | 2 | 2 | 0 | 0.75 |
| d_MrBlonde | 3 | 0 | 1 | 0.75 |
| d_MrWhite | 2 | 2 | 0 | 0.75 |
| e_txn_cfr | 2 | 2 | 0 | 0.75 |
| random | 3 | 1 | 0 | 0.88 |
| e_tumble_q1 | 3 | 1 | 0 | 0.88 |
| e_lomaan | 3 | 1 | 0 | 0.88 |
| e_gunslinger | 3 | 1 | 0 | 0.88 |
| d_Eddie | 3 | 1 | 0 | 0.88 |
| d_MrOrange | 3 | 1 | 0 | 0.88 |
| d_MrBrown | 3 | 1 | 0 | 0.88 |
| d_MrBlue | 3 | 1 | 0 | 0.88 |
| d_Hattori | 3 | 1 | 0 | 0.88 |
| trapper | 4 | 0 | 0 | 1.00 |
| kit_template | 4 | 0 | 0 | 1.00 |
| station | 4 | 0 | 0 | 1.00 |
| kit_caller | 4 | 0 | 0 | 1.00 |
| e_range_mc | 4 | 0 | 0 | 1.00 |
| e_adapt_exploit | 4 | 0 | 0 | 1.00 |
| e_txn_mybot | 4 | 0 | 0 | 1.00 |
| e_txn_floorfix | 4 | 0 | 0 | 1.00 |
| e_atharva | 4 | 0 | 0 | 1.00 |

## Who knocks the hero out

KO-stage eliminations of the hero: overfolder x1
Tours where hero missed the top 4: 0/4; pairing losses (LL) in those tours: none
KO pair record: overfolder 2-4-1, e_advit_strong 2-0-0, tag 1-4-0, e_tumble_dutch 1-1-0
