# Tournament sim `final_v2_1`  hero=lab/snapshots/v2_1  field=core,ext,dataset (40 bots)  rr=1  tours=4  seeds=holdout  tf=2.0

Assumptions: pairing win=1, draw=0.5, loss=0; qual ties -> match wins -> seeded coin; KO = duplicate pairs until one bot wins a pair (max 5), then higher qual rank; 1v4, 2v3, final.

Throughput: 6278 matches in 774s = **8.11 matches/s** with 15 workers (mean match wall 1.92s, 75 hands/match). Crashes: 0. Hero timeouts: 0, hero p99 think worst match 297 ms (emulated).
Slowest bots (mean wall s per match they play): e_atharva 9.81, e_txn_floorfix 7.56, e_txn_cfr 7.48, e_txn_mybot 6.39, e_advit_strong 1.73, e_tumble_dutch 1.72

**HERO: P(top 4) = 100%  P(top 2) = 100%  P(win) = 100%  mean qual rank 1.0**  (n=4 tournaments; binomial SE of a probability p is sqrt(p(1-p)/4))

| bot | mean qual rank | mean pts | P(top 4) | P(top 2) | P(win) |
|---|---|---|---|---|---|
| **HERO** | 1.0 | 29.9 | 100% | 100% | 100% |
| e_tumble_dutch | 3.5 | 25.6 | 75% | 0% | 0% |
| e_advit_strong | 3.8 | 25.9 | 75% | 75% | 0% |
| e_gunslinger | 4.8 | 25.6 | 50% | 25% | 0% |
| d_MrBlonde | 9.2 | 23.6 | 25% | 0% | 0% |
| overfolder | 9.8 | 24.0 | 25% | 0% | 0% |
| d_Budd | 10.0 | 23.0 | 0% | 0% | 0% |
| tag | 10.2 | 23.0 | 0% | 0% | 0% |
| e_opp_modeler | 11.2 | 22.9 | 0% | 0% | 0% |
| d_MrPink | 12.2 | 22.5 | 0% | 0% | 0% |
| d_ORen | 13.8 | 22.4 | 0% | 0% | 0% |
| d_MrWhite | 14.0 | 22.4 | 0% | 0% | 0% |
| d_Hattori | 14.0 | 21.9 | 0% | 0% | 0% |
| e_tumble_q1 | 15.0 | 22.0 | 25% | 0% | 0% |
| d_Gogo | 15.2 | 22.0 | 0% | 0% | 0% |
| d_Eddie | 15.8 | 22.0 | 0% | 0% | 0% |
| d_MrBlue | 15.8 | 21.5 | 25% | 0% | 0% |
| d_Bill | 16.2 | 21.9 | 0% | 0% | 0% |
| d_MrBrown | 16.2 | 21.8 | 0% | 0% | 0% |
| lag | 19.2 | 21.0 | 0% | 0% | 0% |
| d_Joe | 19.8 | 21.1 | 0% | 0% | 0% |
| d_Pluribus | 20.2 | 20.9 | 0% | 0% | 0% |
| d_MrOrange | 22.0 | 20.9 | 0% | 0% | 0% |
| shover | 24.0 | 19.9 | 0% | 0% | 0% |
| e_txn_cfr | 24.8 | 19.4 | 0% | 0% | 0% |
| e_txn_floorfix | 25.2 | 19.6 | 0% | 0% | 0% |
| e_txn_mybot | 25.2 | 18.8 | 0% | 0% | 0% |
| e_adapt_exploit | 25.2 | 19.6 | 0% | 0% | 0% |
| minraiser | 25.5 | 18.6 | 0% | 0% | 0% |
| nit | 27.2 | 18.8 | 0% | 0% | 0% |
| e_lomaan | 29.8 | 17.5 | 0% | 0% | 0% |
| maniac | 30.0 | 17.4 | 0% | 0% | 0% |
| e_range_mc | 33.0 | 15.6 | 0% | 0% | 0% |
| e_atharva | 33.8 | 14.4 | 0% | 0% | 0% |
| trapper | 34.2 | 14.4 | 0% | 0% | 0% |
| e_langchen | 35.8 | 12.5 | 0% | 0% | 0% |
| random | 37.0 | 11.5 | 0% | 0% | 0% |
| station | 37.2 | 9.8 | 0% | 0% | 0% |
| kit_caller | 39.2 | 2.6 | 0% | 0% | 0% |
| kit_template | 39.8 | 2.1 | 0% | 0% | 0% |

## Hero qualification pairing record (WW-D-LL, all tours and repetitions)

| opp | WW | D | LL | pair score |
|---|---|---|---|---|
| minraiser | 0 | 3 | 1 | 0.38 |
| lag | 0 | 4 | 0 | 0.50 |
| nit | 0 | 4 | 0 | 0.50 |
| d_Pluribus | 0 | 4 | 0 | 0.50 |
| d_Bill | 1 | 2 | 1 | 0.50 |
| d_Gogo | 0 | 4 | 0 | 0.50 |
| shover | 1 | 3 | 0 | 0.62 |
| tag | 1 | 3 | 0 | 0.62 |
| d_Joe | 1 | 3 | 0 | 0.62 |
| d_MrWhite | 2 | 1 | 1 | 0.62 |
| d_Budd | 2 | 1 | 1 | 0.62 |
| d_ORen | 1 | 3 | 0 | 0.62 |
| maniac | 2 | 2 | 0 | 0.75 |
| overfolder | 3 | 0 | 1 | 0.75 |
| e_range_mc | 2 | 2 | 0 | 0.75 |
| e_tumble_dutch | 2 | 2 | 0 | 0.75 |
| e_langchen | 2 | 2 | 0 | 0.75 |
| e_advit_strong | 2 | 2 | 0 | 0.75 |
| e_gunslinger | 2 | 2 | 0 | 0.75 |
| d_MrPink | 2 | 2 | 0 | 0.75 |
| d_MrBlonde | 3 | 0 | 1 | 0.75 |
| kit_caller | 3 | 1 | 0 | 0.88 |
| random | 3 | 1 | 0 | 0.88 |
| e_tumble_q1 | 3 | 1 | 0 | 0.88 |
| e_opp_modeler | 3 | 1 | 0 | 0.88 |
| e_adapt_exploit | 3 | 1 | 0 | 0.88 |
| d_Eddie | 3 | 1 | 0 | 0.88 |
| d_MrOrange | 3 | 1 | 0 | 0.88 |
| d_MrBlue | 3 | 1 | 0 | 0.88 |
| d_Hattori | 3 | 1 | 0 | 0.88 |
| d_MrBrown | 3 | 1 | 0 | 0.88 |
| e_txn_cfr | 3 | 1 | 0 | 0.88 |
| e_atharva | 3 | 1 | 0 | 0.88 |
| station | 4 | 0 | 0 | 1.00 |
| trapper | 4 | 0 | 0 | 1.00 |
| kit_template | 4 | 0 | 0 | 1.00 |
| e_lomaan | 4 | 0 | 0 | 1.00 |
| e_txn_mybot | 4 | 0 | 0 | 1.00 |
| e_txn_floorfix | 4 | 0 | 0 | 1.00 |

## Who knocks the hero out

KO-stage eliminations of the hero: none
Tours where hero missed the top 4: 0/4; pairing losses (LL) in those tours: none
KO pair record: overfolder 1-1-0, e_advit_strong 3-2-0, d_MrBlue 1-0-0, e_gunslinger 2-2-0, e_tumble_q1 1-0-0
