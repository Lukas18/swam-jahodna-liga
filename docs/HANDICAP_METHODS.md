# Parallel handicap methods

Both methods are calculated after each completed tournament. They have separate runs and snapshots in the existing normalized Supabase tables; no SQL migration is needed.

- **Original · last 10 tournaments**: mean score relative to recorded par across the latest ten completed tournaments (or available events), with equal event weighting. Round scores within each event are averaged. Round upward, retaining the sign.
- **Golf-style · best rounds**: the simulation’s lowest-score selection from the latest twenty eligible 18-hole rounds. Apply the fewer-than-twenty selection counts/adjustments, cap the estimate at 54, then round the unrounded estimate upward. Recorded par substitutes for Course Rating; slope is 113 and PCC is zero. Raw hole scores are uncapped. This remains a golf-inspired estimate, not a complete WHS calculation.
- Before three eligible rounds, use the original handicap **provisionally**, as requested. Completed short rounds and totals-only records still contribute to the original method but do not enter the golf 18-hole window. Profiles without any completed event remain pending.

A tournament uses the previous completed tournament’s next handicap. A player’s third eligible round establishes a golf estimate for the next event, not retroactively for the third event itself. The debut uses the existing original bootstrap. Multiple rounds in one event are only added after the event is complete; all rounds of that event use the same pre-event handicap. Corrections, deletions and backdated results rebuild both chronological histories.

## Administration and public display

**Administration → Settings → Active handicap method** chooses the method used by profiles, current HCP columns and handicap-adjusted results. Save settings to apply. Both histories and the comparison table remain available when switching back. The public Handicap history screen has its own read-only method selector and marks golf snapshots that are provisional. Raw/par scores and placement points based on par are not changed by a method switch. Stableford’s formula remains unimplemented.

The active setting is `handicap_method` in `league_v2.app_settings.extra`: `legacy` or `golf`. Missing settings retain the original method. Supabase core `handicap` columns continue storing original-method values. The app projects the selected method into its in-memory view; every save recomputes canonical original fields before writing. Cached player/entry/scorecard `extra.golf_handicap`, `golf_handicap_pending`, `golf_provisional` and `golf_handicap_snapshot_id` hold the parallel result and pointer. New settings edits preserve unrelated settings.

## Normalized storage

- `league_v2.handicap_runs.algorithm` distinguishes `relative-par-last-10-ceiling-v1` from `relative-par-best-of-20-ceiling-v1`.
- `league_v2.handicap_history` has separate rows/run IDs for each method, with ordinary integer `handicap_before`, `handicap_used`, `handicap_after` fields. The original history is not replaced by a golf history.
- `league_v2.handicap_sources` stores selected source tournaments. When several selected rounds come from the same event, their mean occupies its unique event-source row; exact round IDs/numbers/scores are retained in that snapshot’s `extra.selected_rounds`.
- Golf snapshot metadata in `extra` includes the one-decimal index, unrounded index, window count, actual selection count, adjustment, provisional status and whether the handicap used was provisional. The existing SQL `sample_count` field holds the selected count (1–8); provisional records use a 1 placeholder and expose their actual zero selection count separately. Public golf history shows the actual selection count.
- Normal save semantics retain previous calculation runs/rows as archived records. Run hashes and snapshot pointers may refresh when existing source inputs have changed; original numerical handicap values/history, raw scores and other league records are checked before initial backfill. Existing archived records and the original legacy `app_data` document are never deleted by this feature.

Example read-only SQL to inspect both histories:

```sql
SELECT p.first_name, p.last_name, r.algorithm,
       h.date, h.handicap_used, h.handicap_after,
       h.extra ->> 'provisional' AS provisional
FROM league_v2.handicap_history h
JOIN league_v2.handicap_runs r
  ON r.document_id = h.document_id AND r.id = h.run_id
JOIN league_v2.players p
  ON p.document_id = h.document_id AND p.id = h.player_id
WHERE h.document_id = 'main'
  AND NOT h.archived AND NOT r.archived AND NOT p.archived
ORDER BY p.last_name, p.first_name, h.date DESC, r.algorithm;
```

## Initial backfill and backup

Deploy the new application code and reboot Streamlit so all imported modules refresh, then run:

```sh
.venv/bin/python backfill_handicaps.py
.venv/bin/python backfill_handicaps.py --apply --activate legacy
```

Preview is read-only. Apply saves owner-only before/after backups with checksum sidecars under ignored `data/backups/`, verifies existing values, saves using the loaded revision (atomic conflict protection), then loads back and compares the entire canonical document. Repeating a completed backfill makes no write. By default the backfill retains the current method. Initial deployment keeps the original active; select Golf-style in Admin when ready. `--activate legacy` selects the original method while retaining golf calculations. Normal app result edits then maintain both histories automatically. The simulator and SQL schema are unchanged except that the offline simulator now shares the selection-rule helper.
