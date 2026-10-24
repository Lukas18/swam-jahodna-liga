# Handicap calculation

The application calculates one golf-style handicap history. Completed tournaments are ordered by date and event order across all leagues. Only complete 18-hole scorecards enter the latest-20-round window. From that window, the golf-style selection rule chooses the best rounds, applies its small-sample adjustment, caps the raw estimate at 54, and rounds it upward to an integer. Recorded par substitutes for Course Rating; slope is 113 and PCC is zero. Scores are uncapped, so this is an estimate rather than an official WHS index.

Until a player has three eligible rounds, their `original_handicap` (the HCP recorded when the player was created or imported) is used provisionally. The third eligible round establishes a calculated HCP for the **next** event. Every round in one tournament uses the same pre-event handicap. Incomplete tournaments do not create a history row or enter the calculation. Complete short rounds and totals-only records can create a provisional event row but do not enter the 18-hole window. Backdated edits rebuild later snapshots.

## Storage and migration

The canonical `handicap_run` and `handicap_history` contain only the golf-style method (`relative-par-best-of-20-ceiling-v2`). Player, registration and scorecard `handicap` columns use that method directly. Stableford has one set of points and per-hole allocations. The method switch, parallel `golf_*` fields and last-10 calculation have been removed.

The existing normalized SQL tables and constraints support this shape; no SQL migration is required. On load, the relational adapter identifies golf rows in older dual-method documents and excludes their last-10 rows from the domain document. The first save creates a new golf run, archives old active runs and snapshots through the existing atomic save procedure, and retains archived records for audit. It preserves `original_handicap` as the provisional input. The old `handicap_method` setting is removed on recalculation.

To preview and apply the conversion, run:

```sh
venv/bin/python backfill_handicaps.py
venv/bin/python backfill_handicaps.py --apply
```

The apply step creates checksummed before/after backups in ignored `data/backups/`, checks that recorded player identities and round scores are unchanged, saves with the loaded revision, and verifies the readback. Review the preview before applying to production. Deploy the code and restart Streamlit after conversion.

To inspect current active snapshots in SQL, filter both the run and history rows by `archived = false`:

```sql
SELECT p.first_name, p.last_name, r.algorithm, h.date,
       h.handicap_used, h.handicap_after, h.extra ->> 'provisional' AS provisional
FROM league_v2.handicap_history h
JOIN league_v2.handicap_runs r
  ON r.document_id = h.document_id AND r.id = h.run_id
JOIN league_v2.players p
  ON p.document_id = h.document_id AND p.id = h.player_id
WHERE h.document_id = 'main'
  AND NOT h.archived AND NOT r.archived AND NOT p.archived
ORDER BY p.last_name, p.first_name, h.date DESC;
```
