# Stableford

Implemented for **Jesenna SWAM Liga** only. Home, League and Tournament screens offer the original relative-to-par standings and a separate Stableford view. Other leagues and both existing handicap histories remain unchanged.

## Scoring

Net score = actual throws minus allocated handicap strokes. Points per hole are `max(0, 2 + par - net score)`: bogey 1, par 2, birdie 3, eagle 4, albatross 5, four under 6. An ace is scored by its net relation to par; it has no independent bonus. See [R&A Rule 21.1](https://www.randa.org/rog/the-rules-of-golf/rule-21).

The app uses **100% of its existing integer tournament handicap**, as requested. This is a disc-golf adaptation, not a certified WHS competition: [the 95% allowance commonly recommended for individual golf Stableford](https://www.usga.org/content/usga/home-page/handicapping/roh/Content/rules/Appendix%20C%20Handicap%20Allowances.htm) is not applied. Positive handicaps receive strokes hardest-first; negative handicaps return strokes easiest-first. For example, HCP 20 receives one stroke on all 18 holes and another on stroke indices 1–2. HCP −2 gives one back on indices 18 and 17. This repeats for larger magnitudes. Each round uses the handicap recorded for the player at that tournament, under the selected handicap method.

## Difficulty and historical snapshots

The initial snapshot uses **all currently recorded hole results** and ranks pooled mean throws relative to par from hardest to easiest. Matching nonzero length and par within a course share one difficulty rating across layouts, including renumbered holes. Holes with unknown distance remain separate by layout and number. Identical measured configurations are treated as the same shared group; verify the initial mapping in Administration → Hole difficulty if two physically distinct holes have identical measurements.

Administration → Hole difficulty lets the administrator edit each shared configuration's priority: lower = harder. Each layout/profile converts that order into unique indices 1–18 (or its own hole count). Thus shared ratings are identical, while their index can differ where the layouts contain different other holes. Tied ratings use stable identity order, then hole number for repeated configurations; unobserved configurations follow observed ones.

Every tournament keeps its own frozen index lists for each actual historical layout/tee configuration. Historical backfill intentionally uses today's pooled difficulty, not a reconstructed difficulty from past dates. Later score imports update calculated points and historical handicaps but do not change an existing event's difficulty snapshot. New events capture the current administrator-configured order. Select events explicitly in the difficulty editor to replace their snapshots and recalculate their Stablefords. Recalculation does not alter raw scores or handicap formulas.

Incomplete events or totals-only scorecards stay `pending_inputs` and are excluded; missing hole scores are not guessed to be pickups. With the current importer, a pickup cannot be distinguished from missing data.

## Standings and storage

Highest Stableford total wins each tournament; competition ties share places (1, T2, T2, 4). League standings award the existing configured placement points from those Stableford places, using the league's category and tie rules. League grids also show total Stableford points. Home keeps the compact points/attendance/current-HCP columns. Original score standings remain available.

Existing normalized `league_v2.stableford_results` stores one result per tournament/player. Its `points` column remains the original-method projection; the row's `extra.methods` retains both calculated methods and per-hole allocations. The app projects the active method, so switching handicap methods is reversible without recalculating raw scores. Difficulty configuration lives in the owning course's extra metadata, and frozen index lists live on each tournament. No SQL migration is needed; existing core entity tables, foreign keys and atomic revision checks remain in use.

`backfill_stableford.py` previews by default. `--apply` saves owner-only checksummed before/after backups, checks that every original entity/score/handicap remains unchanged, uses atomic revision comparison, and verifies exact readback. Other leagues' result rows are preserved exactly. Backups are ignored by Git.

After deploying, **reboot the Streamlit application** so Python reloads the new calculation module and imports.
