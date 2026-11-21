# Tournament sim `real3`  hero=my_bots/redteamers007  field=core,ext,dataset (40 bots)  rr=1  tours=3  seeds=dev  tf=2.0

Assumptions: pairing win=1, draw=0.5, loss=0; qual ties -> match wins -> seeded coin; KO = duplicate pairs until one bot wins a pair (max 5), then higher qual rank; 1v4, 2v3, final.

Throughput: 4718 matches in 2728s = **1.73 matches/s** with 4 workers (mean match wall 2.39s, 76 hands/match). Crashes: 0. Hero timeouts: 0, hero p99 think worst match 893 ms (emulated).

**HERO: P(top 4) = 100%  P(top 2) = 67%  P(win) = 67%  mean qual rank 1.0**  (n=3 tournaments; binomial SE of a probability p is sqrt(p(1-p)/3))

| bot | mean qual rank | mean pts | P(top 4) | P(top 2) | P(win) |
|---|---|---|---|---|---|
| **HERO** | 1.0 | 30.7 | 100% | 67% | 67% |
| e_gunslinger | 3.3 | 25.5 | 100% | 67% | 0% |
| e_advit_strong | 6.0 | 25.0 | 67% | 33% | 33% |
| d_Hattori | 8.3 | 23.3 | 0% | 0% | 0% |
| d_MrBlonde | 10.3 | 23.2 | 33% | 0% | 0% |
| e_opp_modeler | 11.0 | 22.8 | 0% | 0% | 0% |
| d_Eddie | 11.0 | 23.3 | 33% | 0% | 0% |
| d_MrPink | 11.3 | 22.5 | 0% | 0% | 0% |
| overfolder | 11.7 | 22.8 | 33% | 33% | 0% |
| e_tumble_q1 | 11.7 | 22.3 | 0% | 0% | 0% |
| d_Pluribus | 11.7 | 22.7 | 0% | 0% | 0% |
| d_MrWhite | 11.7 | 23.3 | 33% | 0% | 0% |
| d_Bill | 14.0 | 21.8 | 0% | 0% | 0% |
| d_Gogo | 14.0 | 22.3 | 0% | 0% | 0% |
| e_tumble_dutch | 15.0 | 22.0 | 0% | 0% | 0% |
| d_MrOrange | 15.0 | 22.3 | 0% | 0% | 0% |
| e_adapt_exploit | 16.0 | 21.7 | 0% | 0% | 0% |
| lag | 16.7 | 21.7 | 0% | 0% | 0% |
| d_Budd | 16.7 | 21.7 | 0% | 0% | 0% |
| tag | 17.7 | 21.7 | 0% | 0% | 0% |
| e_txn_floorfix | 18.3 | 21.2 | 0% | 0% | 0% |
| d_MrBlue | 18.3 | 21.2 | 0% | 0% | 0% |
| d_MrBrown | 18.3 | 21.3 | 0% | 0% | 0% |
| d_ORen | 19.0 | 21.0 | 0% | 0% | 0% |
| d_Joe | 23.0 | 20.5 | 0% | 0% | 0% |
| e_txn_cfr | 23.7 | 20.2 | 0% | 0% | 0% |
| shover | 27.0 | 19.2 | 0% | 0% | 0% |
| nit | 28.3 | 18.5 | 0% | 0% | 0% |
| minraiser | 29.0 | 18.0 | 0% | 0% | 0% |
| maniac | 29.3 | 18.5 | 0% | 0% | 0% |
| e_txn_mybot | 30.0 | 17.5 | 0% | 0% | 0% |
| e_lomaan | 31.3 | 16.5 | 0% | 0% | 0% |
| e_range_mc | 31.7 | 16.5 | 0% | 0% | 0% |
| e_atharva | 34.0 | 14.7 | 0% | 0% | 0% |
| trapper | 35.3 | 14.2 | 0% | 0% | 0% |
| e_langchen | 36.0 | 12.5 | 0% | 0% | 0% |
| random | 36.7 | 11.2 | 0% | 0% | 0% |
| station | 37.7 | 9.5 | 0% | 0% | 0% |
| kit_caller | 39.0 | 3.5 | 0% | 0% | 0% |
| kit_template | 40.0 | 1.8 | 0% | 0% | 0% |

## Hero qualification pairing record (WW-D-LL, all tours and repetitions)

| opp | WW | D | LL | pair score |
|---|---|---|---|---|
| d_Hattori | 0 | 1 | 2 | 0.17 |
| maniac | 0 | 2 | 1 | 0.33 |
| d_MrPink | 0 | 2 | 1 | 0.33 |
| tag | 0 | 3 | 0 | 0.50 |
| e_langchen | 0 | 3 | 0 | 0.50 |
| d_Gogo | 1 | 1 | 1 | 0.50 |
| lag | 2 | 0 | 1 | 0.67 |
| shover | 1 | 2 | 0 | 0.67 |
| random | 1 | 2 | 0 | 0.67 |
| e_gunslinger | 1 | 2 | 0 | 0.67 |
| d_Bill | 1 | 2 | 0 | 0.67 |
| d_Eddie | 1 | 2 | 0 | 0.67 |
| d_MrWhite | 1 | 2 | 0 | 0.67 |
| d_Budd | 1 | 2 | 0 | 0.67 |
| d_MrBlonde | 1 | 2 | 0 | 0.67 |
| nit | 2 | 1 | 0 | 0.83 |
| trapper | 2 | 1 | 0 | 0.83 |
| e_txn_floorfix | 2 | 1 | 0 | 0.83 |
| e_advit_strong | 2 | 1 | 0 | 0.83 |
| e_range_mc | 2 | 1 | 0 | 0.83 |
| e_opp_modeler | 2 | 1 | 0 | 0.83 |
| d_Pluribus | 2 | 1 | 0 | 0.83 |
| d_MrBlue | 2 | 1 | 0 | 0.83 |
| d_MrOrange | 2 | 1 | 0 | 0.83 |
| d_MrBrown | 2 | 1 | 0 | 0.83 |
| overfolder | 3 | 0 | 0 | 1.00 |
| station | 3 | 0 | 0 | 1.00 |
| kit_template | 3 | 0 | 0 | 1.00 |
| kit_caller | 3 | 0 | 0 | 1.00 |
| minraiser | 3 | 0 | 0 | 1.00 |
| e_txn_cfr | 3 | 0 | 0 | 1.00 |
| e_tumble_q1 | 3 | 0 | 0 | 1.00 |
| e_txn_mybot | 3 | 0 | 0 | 1.00 |
| e_tumble_dutch | 3 | 0 | 0 | 1.00 |
| e_lomaan | 3 | 0 | 0 | 1.00 |
| e_adapt_exploit | 3 | 0 | 0 | 1.00 |
| d_Joe | 3 | 0 | 0 | 1.00 |
| e_atharva | 3 | 0 | 0 | 1.00 |
| d_ORen | 3 | 0 | 0 | 1.00 |

## Who knocks the hero out

KO-stage eliminations of the hero: e_gunslinger x1
Tours where hero missed the top 4: 0/3; pairing losses (LL) in those tours: none
KO pair record: e_gunslinger 2-2-1, d_Eddie 1-0-0, overfolder 1-2-0
