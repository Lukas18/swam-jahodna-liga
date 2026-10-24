# Review and migrate the relational store

The handicap rules and deployment status below record the original 14 October migration. The current single golf-style calculation is described in [HANDICAP_METHODS.md](HANDICAP_METHODS.md); the last-10 rules below are no longer active.

The app_data table is retained throughout this historical migration.

## Current cutover status — 2026-10-14

The user installed the SQL in Supabase. The data copy completed and every reconstructed field was verified against the reviewed transformation of legacy revision 50. The new normalized document is revision 1. Local ignored Streamlit secrets now select relational mode; the app at http://127.0.0.1:8502/ runs the real application against Supabase, bound to loopback only. It has replaced the earlier read-only snapshot preview. Hosted deployment has not been updated because code remains uncommitted/unpushed for review; it needs the reviewed code plus the same model setting before it should accept edits against the new store.

The first copy was rejected atomically because Python serialized integral placement points as 10.0; the serializer now emits true JSON integers for SQL integer columns and refuses fractional values. Verified no normalized document remained after that rejected transaction. The corrected copy succeeded, and a repeat migration confirms no writes needed.

Pre-copy backup: data/backups/before-relational-copy-20261014-080526-343087.json. Post-copy normalized backup: data/backups/after-relational-copy-20261014-080703-560080.json. Both have checksums; original app_data remains revision 50 and unchanged. No records were deleted.

## What is ready

- sql/001_relational.sql creates separate tables in league_v2 and two service-role-only RPCs in public (dg_load and dg_save). It never edits app_data. DDL is in one transaction and can be rerun safely for this schema version. It does not implement arbitrary future schema upgrades.
- migrate_relational.py previews and copies existing records, preserving IDs and all hole/score snapshots. It creates retrospective handicap history and original_handicap audit fields. It refuses to overwrite an existing normalized document that differs.
- The app, compatibility database helpers, and import-player/tournament scripts share the versioned Store. They select relational mode with DISCGOLF_STORAGE_MODEL; the default remains legacy JSON until cutover.
- The local app at http://127.0.0.1:8502/ is now the live relational application, not a snapshot preview. Admin saves use the normalized Store.

## Confirmed handicap rules

Score input is relative to recorded par, averaged per round for multi-round tournaments. A completed tournament contributes one sample. Include the latest 10 completed tournaments across seasons/leagues, or all available samples when fewer exist. Total throws remain recorded but do not drive the handicap directly. There are currently no multi-round events in the backed-up source; the per-round convention maintains the app's existing per-round handicap adjustment.

Round the arithmetic mean toward positive infinity: 7.1 becomes 8; -6.8 becomes -6. Do not average previously rounded handicaps. The debut event uses its own relative-to-par score rounded upward as the starting handicap. Every later event uses the preceding event's next handicap; after the current event completes it enters the rolling window. The profile contains the next handicap from the latest chronological event, not the last-imported event.

Players without completed results display a dash. A numeric zero placeholder exists only for legacy domain compatibility and is marked handicap_pending, not treated as an established handicap. Backdated events and corrections rebuild history from original score inputs. Original stored handicaps are preserved as original_handicap, and old normalized history runs are archived rather than physically deleted.

Same-day tournaments for one player require distinct event_order values. The tournament editor exposes Order on the same date. Until that ambiguity is resolved calculation fails rather than guessing event order. Stableford values are NULL/pending_formula, not zero; no formula has been guessed. Scores, layouts and historical pars remain unchanged.

## Migration steps

1. Review the read-only preview. Keep admin edits paused from the final source snapshot until cutover verification completes.
2. In Supabase SQL Editor, run the entire sql/001_relational.sql file. This adds tables/constraints/functions; it does not copy any records yet. The schema is not exposed for anonymous writes. Use a server service-role key in Streamlit secrets; a publishable/anon key cannot call the new RPCs. Never put the secret key in browser code.
3. With local .streamlit/secrets.toml containing SUPABASE_URL and SUPABASE_KEY, preview:

   ```bash
   .venv/bin/python migrate_relational.py
   ```

   An offline preview can use --source-json with a backup document or the table-export envelope. It cannot be combined with --apply.
4. After the preview passes, copy and verify:

   ```bash
   .venv/bin/python migrate_relational.py --apply
   ```

   This takes another owner-only local backup, checks the source revision, creates the new normalized document in one transaction, compares the full read-back and verifies legacy data stayed unchanged. A retry with identical existing normalized data performs no write; a differing existing normalized document stops for review.
5. In Streamlit secrets, add the following top-level key and restart the app using the reviewed local code:

   ```toml
   DISCGOLF_STORAGE_MODEL = "relational"
   ```

   For terminal scripts set the same environment variable, or use the same secrets file (the importer loader reads this key). The local app reads top-level secrets or a supabase section. Avoid conflicting environment/secrets model selections. If relational mode is enabled without the SQL/schema/data, the app reports an error; it does not silently write to legacy storage.
6. Verify Home/League/Tournament handicap columns, the Handicap history screen, admin edits, and an import on staging/disposable data before reopening production admin edits. The new code has not been committed or deployed to hosting; updating secrets alone does not deploy it.

## Writes and data retention

All normalized updates use the global document revision as an optimistic lock. A single RPC updates only changed table rows, marks absent rows archived, and checks related scorecard totals within one transaction. Foreign keys are deferred until commit so a complete entity graph can be copied safely. No DELETE or TRUNCATE is used. The original app_data JSON is neither dual-written nor overwritten in relational mode. Archived rows and original_handicap fields retain the old data; audit metadata is small JSON, while entities, relationships and hole scores are separate relational rows.

The compatibility domain adapter currently assembles the whole document on load. This preserves existing scoring/UI behavior; per-entity querying/concurrency can be optimized later. Independent edits still contend on one document revision, deliberately retaining existing conflict protection in this first migration.

## Rollback

Before new normalized writes, disable relational mode and restart the legacy app if necessary. After any normalized writes, do not simply switch to the old JSON: it will be stale. Export the normalized Store data to a new backup first and reconcile/reverse-export it into a separate reviewed legacy document. Keep both stores and all backups. No cleanup is authorized in this migration.

## Verification performed

- Full Python test suite: 70 tests passed (including isolated UI storage; no test connects to live Supabase).
- Isolated PostgreSQL (PGlite) ran the SQL twice, loaded all 5,238 hole scores and verified every domain field after SQL round-trip. Checked revision conflicts, transaction rollback on invalid totals, service-role/anonymous permissions and archival retention.
- Initial preview: 51 players, 3 leagues, 29 tournaments, 291 scorecards/history snapshots, 1,575 history source links and 291 pending Stableford results. These counts must be refreshed if production data changes.
- Read-only browser verification of Home current handicap and historical before/after handicap rows.

For reproducible SQL testing: generate a JSON payload via league.relational.to_records(migrate_relational.prepare(source)); run tests/verify_relational_sql.mjs with Node, PGLITE_MODULE set to an installed PGlite module path, and the payload file as its first argument. SQL tests use a temporary in-memory database, not Supabase.
