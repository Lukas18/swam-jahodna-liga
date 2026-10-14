# Handicap simulation — 14 October 2026

Generated: 2026-10-14T22:29:22+02:00. Read-only analysis of normalized Supabase document `main`, revision 2.

No application results, player handicaps, registrations, scorecards or history snapshots were changed. The simulation is separate from the production calculation.

## Scope and assumptions

- Select the five players with most completed tournaments, including ties at the fifth position: six players. Completion requires all scheduled rounds and round numbers. In this source every event has one round and every recorded round has 18 holes; tournament and round counts therefore coincide.
- Use each selected player’s full recorded history across leagues, categories and layouts. Only the most recent 20 completed rounds can supply the simulated estimate; fewer rounds use the score-count selection table. Old rounds are not included just because they are good.
- Assume Course Rating equals each round’s recorded par, Slope Rating = 113 and PCC = 0. Thus the illustrative differential equals recorded throws minus recorded par. These assumptions are not measured course ratings and do not correct differences in layout difficulty.
- Raw scores are uncapped. No net-double-bogey adjustments, exceptional-score reductions or low-index soft/hard caps are applied. Official ratings and hole stroke indices are not stored; this is a WHS-inspired selection-rule comparison, not a complete or official WHS calculation.
- Apply the best-score selection/initial adjustments and a maximum estimate of 54.0. Display the estimate to one decimal using decimal half-up rounding; the adapted integer uses the ceiling of the unrounded estimate, keeping its sign. This integer column follows the league preference rather than golf’s course-handicap rounding.
- The current comparison is recomputed independently as the ceiling of the mean of the latest 10 completed tournament scores relative to recorded par. All six recomputed values match their stored current player handicaps.

## Comparison

| Player | Category | Completed tournaments | Selection | Current HCP | Simulated decimal | Adapted integer | Integer change |
|---|---|---:|---|---:|---:|---:|---:|
| Roman Stefancik | MPO | 21 | Best 8 of latest 20 | 9 | 3.1 | 4 | -5 |
| Michal Kapec | MA3 | 19 | Best 7 of latest 19 | 10 | 8.1 | 9 | -1 |
| Majky Csorba | MPO | 18 | Best 6 of latest 18 | 5 | 0.2 | 1 | -4 |
| Mário Haško | MA3 | 17 | Best 6 of latest 17 | 12 | 7.5 | 8 | -4 |
| Richard Melichar | MPO | 16 | Best 5 of latest 16 | 2 | -2.8 | -2 | -4 |
| Tomas Jusko | MPO | 16 | Best 5 of latest 16 | 2 | -2.6 | -2 | -4 |

All six estimates are lower than the current rule because the simulated method selects the strongest rounds from its window. It estimates demonstrated scoring potential rather than averaging recent performance. The different windows also matter: a player with older good rounds and more recent weaker rounds can have a particularly large difference. A golf-style method will not always be lower: older good scores can expire from its 20-score window.

## Audit of included scores

Signed score values below are throws relative to recorded par. Negative values retain the league sign convention; golf normally describes a better-than-scratch negative index using plus-handicap notation.

### Roman Stefancik

Current rule: latest-10 mean **8.6**, rounded upward → **9**.

Selected scores: **1, 1, 3, 3, 4, 4, 4, 5**. Sum = **25**; divide by **8** (adjustment 0) → **3.125** → displayed **3.1**, adapted integer **4**.

| Date | Tournament | Layout | Recorded category | Throws | Par | Relative score |
|---|---|---|---|---:|---:|---:|
| 2025-05-17 | Sobotnajsie Discgolfove Turnaje (5. turnaj) | Cervena | 0-18 | 65 | 60 | 5 |
| 2025-06-07 | Sobotnajsie Discgolfove Turnaje (8. turnaj) | Cervena | 0-18 | 63 | 60 | 3 |
| 2025-06-14 | Sobotnajsie Discgolfove Turnaje (9. turnaj) | Cervena | 0-18 | 64 | 60 | 4 |
| 2025-06-21 | Sobotnajsie Discgolfove Turnaje (10. turnaj) | Cervena | 0-18 | 63 | 60 | 3 |
| 2025-08-02 | Sobotnajsie Discgolfove Turnaje (15. turnaj) | Cervena | 0-18 | 61 | 60 | 1 |
| 2025-08-23 | Sobotnajsie Discgolfove Turnaje (18. turnaj) | Cervena | 0-18 | 64 | 60 | 4 |
| 2026-05-10 | Nedelny Turnaj Swam Jahodna | Zelena | MPO | 66 | 62 | 4 |
| 2026-09-19 | DG liga SWAM Jahodna Jesen 2026 3. Kolo | Zelena | MPO | 63 | 62 | 1 |

Latest-window scores in chronological order: `9, 13, 5, 9, 3, 4, 3, 12, 9, 1, 4, 14, 8, 14, 4, 12, 9, 7, 1, 13`.

### Michal Kapec

Current rule: latest-10 mean **10**, rounded upward → **10**.

Selected scores: **5, 6, 8, 8, 9, 10, 11**. Sum = **57**; divide by **7** (adjustment 0) → **8.142857142857142857142857143** → displayed **8.1**, adapted integer **9**.

| Date | Tournament | Layout | Recorded category | Throws | Par | Relative score |
|---|---|---|---|---:|---:|---:|
| 2025-07-12 | Sobotnajsie Discgolfove Turnaje (13. turnaj) | Cervena | 0-18 | 70 | 60 | 10 |
| 2026-04-19 | Nedelny Turnaj Swam Jahodna | Cervena | MPO | 68 | 60 | 8 |
| 2026-05-10 | Nedelny Turnaj Swam Jahodna | Zelena | MPO | 68 | 62 | 6 |
| 2026-09-19 | DG liga SWAM Jahodna Jesen 2026 3. Kolo | Zelena | MA3 | 73 | 62 | 11 |
| 2026-09-26 | DG liga SWAM Jahodna Jesen 2026 4. Kolo | Cervena | MA3 | 65 | 60 | 5 |
| 2026-10-03 | DG liga SWAM Jahodna Jesen 2026 5. Kolo | Zelena | MA3 | 70 | 62 | 8 |
| 2026-10-10 | DG liga SWAM Jahodna Jesen 2026 6. Kolo | Cervena | MA3 | 69 | 60 | 9 |

Latest-window scores in chronological order: `21, 13, 15, 21, 19, 16, 14, 10, 13, 13, 16, 12, 8, 6, 12, 11, 5, 8, 9`.

### Majky Csorba

Current rule: latest-10 mean **4.5**, rounded upward → **5**.

Selected scores: **-2, -1, 0, 1, 1, 2**. Sum = **1**; divide by **6** (adjustment 0) → **0.1666666666666666666666666667** → displayed **0.2**, adapted integer **1**.

| Date | Tournament | Layout | Recorded category | Throws | Par | Relative score |
|---|---|---|---|---:|---:|---:|
| 2025-05-10 | Sobotnajsie Discgolfove Turnaje (4. turnaj) | Cervena | 0-18 | 58 | 60 | -2 |
| 2025-05-17 | Sobotnajsie Discgolfove Turnaje (5. turnaj) | Cervena | 0-18 | 62 | 60 | 2 |
| 2025-08-02 | Sobotnajsie Discgolfove Turnaje (15. turnaj) | Cervena | 0-18 | 59 | 60 | -1 |
| 2025-08-23 | Sobotnajsie Discgolfove Turnaje (18. turnaj) | Cervena | 0-18 | 61 | 60 | 1 |
| 2026-05-10 | Nedelny Turnaj Swam Jahodna | Zelena | MPO | 62 | 62 | 0 |
| 2026-06-28 | Nedelny Turnaj Swam Jahodna | Zelena | MPO | 63 | 62 | 1 |

Latest-window scores in chronological order: `5, 4, -2, 2, 4, 6, 9, 7, -1, 8, 1, 6, 11, 0, 6, 1, 9, 4`.

### Mário Haško

Current rule: latest-10 mean **11.4**, rounded upward → **12**.

Selected scores: **4, 6, 7, 8, 9, 11**. Sum = **45**; divide by **6** (adjustment 0) → **7.5** → displayed **7.5**, adapted integer **8**.

| Date | Tournament | Layout | Recorded category | Throws | Par | Relative score |
|---|---|---|---|---:|---:|---:|
| 2025-08-23 | Sobotnajsie Discgolfove Turnaje (18. turnaj) | Cervena | 0-18 | 71 | 60 | 11 |
| 2026-09-05 | DG liga SWAM Jahodna Jesen 2026 1. Kolo | Zelena | MA3 | 70 | 62 | 8 |
| 2026-09-19 | DG liga SWAM Jahodna Jesen 2026 3. Kolo | Zelena | MA3 | 66 | 62 | 4 |
| 2026-09-26 | DG liga SWAM Jahodna Jesen 2026 4. Kolo | Cervena | MA3 | 69 | 60 | 9 |
| 2026-10-03 | DG liga SWAM Jahodna Jesen 2026 5. Kolo | Zelena | MA3 | 68 | 62 | 6 |
| 2026-10-10 | DG liga SWAM Jahodna Jesen 2026 6. Kolo | Cervena | MA3 | 67 | 60 | 7 |

Latest-window scores in chronological order: `26, 19, 16, 15, 20, 20, 23, 11, 18, 17, 20, 14, 8, 4, 9, 6, 7`.

### Richard Melichar

Current rule: latest-10 mean **1.3**, rounded upward → **2**.

Selected scores: **-4, -3, -3, -2, -2**. Sum = **-14**; divide by **5** (adjustment 0) → **-2.8** → displayed **-2.8**, adapted integer **-2**.

| Date | Tournament | Layout | Recorded category | Throws | Par | Relative score |
|---|---|---|---|---:|---:|---:|
| 2025-06-07 | Sobotnajsie Discgolfove Turnaje (8. turnaj) | Cervena | 0-18 | 58 | 60 | -2 |
| 2026-04-19 | Nedelny Turnaj Swam Jahodna | Cervena | MPO | 57 | 60 | -3 |
| 2026-09-05 | DG liga SWAM Jahodna Jesen 2026 1. Kolo | Zelena | MPO | 60 | 62 | -2 |
| 2026-09-19 | DG liga SWAM Jahodna Jesen 2026 3. Kolo | Zelena | MPO | 59 | 62 | -3 |
| 2026-09-26 | DG liga SWAM Jahodna Jesen 2026 4. Kolo | Cervena | MPO | 56 | 60 | -4 |

Latest-window scores in chronological order: `8, 3, 6, -2, 0, 4, 8, -3, 5, 6, 0, -2, -3, -4, 5, 1`.

### Tomas Jusko

Current rule: latest-10 mean **1.1**, rounded upward → **2**.

Selected scores: **-4, -3, -3, -3, 0**. Sum = **-13**; divide by **5** (adjustment 0) → **-2.6** → displayed **-2.6**, adapted integer **-2**.

| Date | Tournament | Layout | Recorded category | Throws | Par | Relative score |
|---|---|---|---|---:|---:|---:|
| 2025-05-31 | Sobotnajsie Discgolfove Turnaje (7. turnaj) | Cervena | 0-18 | 60 | 60 | 0 |
| 2025-07-12 | Sobotnajsie Discgolfove Turnaje (13. turnaj) | Cervena | 0-18 | 57 | 60 | -3 |
| 2026-09-19 | DG liga SWAM Jahodna Jesen 2026 3. Kolo | Zelena | MPO | 58 | 62 | -4 |
| 2026-09-26 | DG liga SWAM Jahodna Jesen 2026 4. Kolo | Cervena | MPO | 57 | 60 | -3 |
| 2026-10-10 | DG liga SWAM Jahodna Jesen 2026 6. Kolo | Cervena | MPO | 57 | 60 | -3 |

Latest-window scores in chronological order: `4, 3, 5, 0, 1, 6, -3, 1, 1, 4, 6, 2, 10, -4, -3, -3`.

## Reproduce

Private source snapshot (ignored by Git, owner-only): `data/backups/handicap-simulation-source-20261014-222638.json`.

SHA-256: `d5edd177db3d4a979411031607757e4d928f4719feffd822ca9eb02b52585471`.

```sh
.venv/bin/python simulate_handicaps.py data/backups/handicap-simulation-source-20261014-222638.json --top 5
```

The script reads only the named local snapshot and writes JSON to standard output. It does not connect to Supabase. A fresh source snapshot is needed to compare later tournament results. Inputs are checked for 18 distinct hole numbers and agreement between round totals and hole snapshots. Attendance ties, incomplete-event exclusion, selection boundaries, the last-20 window, sign-preserving ceiling and non-mutation are covered by automated tests.

## References

- [TheGrint: How to Calculate Your Golf Handicap](https://thegrint.com/range/post/how-to-calculate-a-golf-handicap-2) — formula, score adjustments and limits, updated 7 October 2026.
- [USGA Rule 5.2a: fewer than 20 scores](https://www.usga.org/content/usga/home-page/handicapping/roh/Content/rules/5%202a%20For%20Fewer%20Than%2020%20Scores.htm) — variable score selection counts.
- [USGA: How is a Handicap Index calculated?](https://www.usga.org/content/usga/home-page/handicapping/world-handicap-system/world-handicap-system-usga-golf-faqs/faqs---how-is-a-handicap-index-calculated.html) — lowest 8 of most recent 20 scores.
