# Change log

## 2026-10-24 — Single golf-style handicap history

- Removed the last-10 tournament handicap calculation and the parallel method selector. The best-of-20 golf-style result now occupies the canonical handicap run, history, player, entry and scorecard fields.
- The player's original HCP is used provisionally until three eligible 18-hole rounds are complete. Stableford uses one historical handicap and one result per player/tournament.
- Older dual-method relational records load only the golf history; a recalculation and save archive the former active runs and snapshots under existing SQL retention rules. Updated the backfill preview, documentation and regression tests.

## 2026-10-08T13:59:12+02:00 — Codebase familiarization

- Reviewed app.py, all 11 Jinja templates, README.md, requirements.txt, and the folder structure.
- Identified a Flask / Flask-SQLAlchemy monolith with SQLite storage in instance/discgolf.db, inline CSS, and vanilla JavaScript.
- Mapped courses, holes, category par overrides, global players, event entries, rounds, and hole scores; reviewed registration and scoring flows.
- Existing database contains 1 course, 18 holes, 8 players, 1 event, 8 category par overrides, and no event entries or scores. SQLite integrity_check returned ok.
- Parsed Python source and verified 10 existing GET pages returned HTTP 200 with Flask test_client. No business records were changed.
- Found round selector parameter mismatch: templates/log_scores.html submits round_number but app.py GET handling reads round.
- Noted missing event ownership checks in entry edit/remove and score routes, minimal server-side input validation, missing database uniqueness constraints, leaderboard sorting of unplayed entries as zero, and historical score recalculation from current pars/categories/handicaps.
- No automated test suite, migrations, authentication, or CSRF protection present; development startup uses a hardcoded secret and debug mode.
- README player-registration description predates the global player registry. An apparently accidental empty directory named {templates,static/css,static also exists.
- Device Hub simulator was unavailable in the exposed tools; simulator and visual behavior verification could not be performed.
- This folder has no Git repository or configured remote, so the requested commit and push cannot be performed.
- Added this log only; application source and database contents remain unchanged.

## 2026-10-08T14:00:34+02:00 — Run local web app

- Started the Flask development server at http://127.0.0.1:5000 using python3 app.py.
- User waived Device Hub verification and deferred GitHub setup.
- No application source changes.

## 2026-10-08T14:41:43+02:00 — Streamlit league application

- Added streamlit_app.py with public Home, League leaderboard, Tournament results/scorecards, Courses → Layouts, and Players screens, plus a password-protected Admin area and eight-hour admin sessions. All persistence actions check admin access; public screens have no edit controls.
- Added framework-independent league/domain.py: editable categories, player uDisc usernames, multiple layouts per course, default/category-specific hole counts/pars/lengths, leagues, tournaments, per-round score snapshots, raw/relative-to-par/handicap ranking, category or overall points, configurable places/points, ties and completed-round eligibility.
- User confirmed category rankings, season point accumulation, and shared occupied-place points for ties. Implemented this default and an optional same-place tie rule. New leagues use an editable initial points schedule.
- Added layout/category summary statistics and per-hole averages/outcome percentages. Ace classification is exclusive; totals-only results do not fabricate hole scores. Distinct historical tee configurations are separate rows and chart labels.
- Added league/imports.py and the admin import screen for Excel .xlsx and CSV, sheet/header selection, explicit username/category/handicap/round/hole/total mappings, atomic preview, unknown-user and duplicate checks, total reconciliation and acknowledged replacements. Real uDisc export verification remains pending a sample.
- Added league/storage.py with atomic local JSON saves, stale-version checks, validated backups/restores, and optional GitHub Contents API persistence using a separate private data repository, SHA conflict protection and a 1 MB size limit. GitHub storage is implemented and mock-tested but not connected to a live account.
- Added migrate_legacy.py and migrated the existing read-only SQLite data to data/league.json: 1 course and original layout, 8 players, 1 tournament, and a Local league. Original Flask source, templates and SQLite contents were preserved. New usernames are blank; unknown lengths are 0 metres.
- Added requirements, Streamlit dark theme configuration, example deployment secrets, .gitignore, and comprehensive README setup/scoring/import/storage documentation. Created an ignored local secrets file containing a randomly generated admin password (not logged here).
- Installed Streamlit/pandas/openpyxl into a project-local .venv and started the new server on http://127.0.0.1:8501. The original Flask server remains available on port 5000.
- Added 16 automated tests covering ties/category points, cutoff ties and league accumulation, completion eligibility and replacements, validation, snapshots, statistics, junior imports, CSV/Excel parsing, unknown/duplicate users, total mismatches, local storage conflicts, mocked GitHub SHA saves, and public/admin Streamlit flows. All passed. Tests use disposable data, leaving real league results untouched.
- Visually verified the Streamlit home and Courses → Layouts screens in the in-app browser, kept the app tab open, and saved streamlit-preview.jpg. No Device Hub checks per the user’s waiver.
- No Git initialization, commit, push or cloud deployment: GitHub setup remains deferred per the user’s instruction.

## 2026-10-08T15:44:18+02:00 — Admin organization and leaderboard improvements

- Removed exclusive league ranking-mode configuration. Relative-to-par, raw throws and handicap-adjusted scoring are independent leaderboard view options; points are calculated from the selected view. Legacy ranking_metric fields remain readable but no longer control the league.
- Moved all create/edit forms, player management, course/layout management, manual scores and uDisc imports under the authenticated Admin page, with sections for Players, Courses & layouts, Leagues, Tournaments & scores, Categories, and Backup & restore. Public navigation now contains Home, Leagues, Tournaments and Admin only. League/tournament result pages remain read-only even while the administrator is signed in.
- Added explicit Number of holes controls for new/existing default and category layout configurations. Resize preserves retained hole pars/lengths and supplies valid new holes. Junior overrides can have independent counts without resizing the default; creating a junior override first leaves an 18-hole default.
- Combined tournament and league tables preserve per-category competition places. An FPO winner does not shift the second-place MPO player to third. Overall-points league settings still award points across all players while displayed places remain category ranks.
- Added subtle category background tints to leaderboard rows; CSV exports retain values without presentation styles.
- Added clickable tournament and league names on Home, with navigation callbacks opening the relevant results screen and preselecting the clicked record.
- Updated README workflow and migration instructions for the new Admin organization and leaderboard semantics. Added regression coverage for combined ranks, independent modes, layout resizing, admin-only management, navigation callbacks and category row styling.
- All 24 automated domain/import/storage/UI tests passed, using temporary fixtures. Verified both Home navigation links and actual tournament results in the in-app browser, including category tints and MPO places 1/2 alongside FPO place 1. Updated streamlit-preview.jpg and left the app open at http://127.0.0.1:8501.
- Existing league data, player edits and score records were not changed. Device Hub remains waived and GitHub/commit/push setup remains deferred as requested.

## 2026-10-08T16:23:37+02:00 — Tournament registration, score grids and theme fixes

- Changed handicap-adjusted tournament scores and league points to integer calculation/output types, including CSV downloads. Fractional adjusted scores round to nearest integer with halves away from zero; shared tie points round to nearest whole point (halves up). League placement point editors now accept integer steps and save integer schedules. Existing player handicap inputs retain half-step support.
- Added tournament registrations independent of scores: admin can add multiple players, use defaults or category overrides, edit registration category/handicap before scores, and remove unscored registrations. Recorded players from older backups appear automatically without modifying existing files. Score imports register newly matched players and respect existing tournament metadata. Legacy migration now includes unscored event entries.
- Replaced single-player vertical score forms with category-specific multi-player grids: players in rows, numbered holes in columns, pinned player names, blank unplayed cells, existing score snapshots, Save checkboxes and per-category batch saves. Batch validation rejects the entire selection if any selected player has missing/invalid scores. Retained round removal and historical par/length preservation. Junior grids show only the played holes; players sort consistently by name.
- Protected global player deletion for registered players, locked tournament layout/category/round settings while entries exist, and added validation for duplicate/invalid registrations and score-registration consistency.
- Replaced fixed dark category row colours with translucent tints that blend into the native theme. Removed forced dark background/text settings; native score controls, tables and chart colours follow the selected light/dark theme.
- Updated README registration/grid/rounding/theme behavior and added tests for integer rounding, fractional ties, registrations without scores, atomic multi-player saves, junior grids, historical edits and backward-compatible registration inference. All 27 automated tests passed using disposable data.
- Visually verified actual tournament results in both light and dark themes, including integer adjusted-score rendering and readable category tints. Saved streamlit-preview-light.jpg and streamlit-preview-dark.jpg; restored the original Custom Theme selection. Opened a fresh preview tab after the earlier tab stopped responding.
- Existing player, tournament and score data were not altered by this work. Device Hub remains waived; GitHub, commit and push remain deferred by the user.

## 2026-10-08T16:31:47+02:00 — Public tournament and all-time statistics

- Added a public Statistics navigation page with All time / Tournament scope and course, layout and category filters. Existing Admin → Courses & layouts statistics remain available.
- Added statistics to the public Tournament overview, filtered to its tournament and selected category and independent of leaderboard ranking/completion filters.
- Added league/statistics.py with scope selection, round/player/tournament/hole sample counts, average throws and relative-to-par, course/category and layout/category overview tables, and per-hole average/outcome percentages with CSV exports and a difficulty chart.
- Hole samples are grouped by layout ID, category, hole number and historical par/length to avoid merging unrelated layouts or tees. Averages use actual hole samples; totals-only results contribute to round summaries but do not invent hole scores. Empty scopes show an explicit no-results message.
- Updated README and added regression tests for multi-tournament scopes, course/layout isolation, category denominators, totals-only data, historical configurations, public access and tournament statistics. All 30 tests passed with disposable fixtures.
- Verified actual all-time Statistics in the browser: course/layout overviews and per-hole statistics rendered from current recorded results. Saved statistics-preview.jpg and left the public Statistics page open. Existing business data was not modified.
- Device Hub remains waived. GitHub setup, commits and pushes remain deferred per the user’s instruction.

## 2026-10-08T20:16:30+02:00 — Category statistics, heat map and Home standings

- Added a dedicated category selector to Tournament statistics, independent of the combined ranking category. Public all-time statistics also require a single category; no all-category statistics view is offered. Course/layout filters and historical score snapshots remain supported.
- Added a theme-aware hole heat map across tournament, all-time and Admin layout statistics. Averages within ±0.25 throws of par remain neutral; three green/orange tint strengths use 0.75 and 1.50 deviation boundaries. Below-par and above-par outcome percentages use >0–25%, >25–50%, >50% bands, with Par and zero percentages neutral. Numeric CSV exports retain unstyled values.
- Added Home standings for one active league, with separate category headings and exactly Name, Total points, Tournaments attended columns. Category places 1–3 receive gold/silver/bronze medals, including shared medals for ties. Points follow the selected ranking view; attendance counts unique events with recorded rounds, including incomplete events and excluding unplayed registrations. Added stable player IDs to league aggregation to avoid conflating duplicate names.
- Default title is SWAM Jahodna liga in Home, sidebar and browser tab. Admin → Settings can save the title and single active league; older backups work without settings and default to the first league. Added settings validation and read-only fallback without changing existing business data.
- Updated README and added regression coverage for category isolation, heat map bands/neutral cells, incomplete-event attendance, league isolation, editable persisted title and active-league selection. All 34 automated tests passed with disposable fixtures.
- Verified the actual Home category standings/medals and tournament heat map in the in-app browser. Changing stats from MPO to FPO changed averages while the ranking selector stayed All. Saved home-standings-preview.jpg and hole-heatmap-preview.jpg; left Home open at http://127.0.0.1:8501/.
- Device Hub remains waived by the earlier user instruction; GitHub setup, commits and pushes remain deferred. This folder has no Git repository.

## 2026-10-08T20:35:34+02:00 — Visible tied ranks and poster-inspired colours

- Added Place to Home overall standings. Category ties display T-prefixed competition ranks, e.g. 1, 2, T3, T3, 5. League and tournament tables/CSV exports use the same notation. Numeric domain ranks and points calculations remain unchanged; players from different categories are not considered tied with one another.
- Applied the user-provided poster palette: forest green page/sidebar/control backgrounds, cream text and accents, cream Home leaderboard rows, brown player names, and green place/points/attendance values. Retained top-three medals and native light/dark theme selection.
- Updated README and regression tests. All 36 tests passed using temporary fixtures, including five-player tied standings and category-isolated labels. Visually verified the running app and saved green-standings-preview.jpg; left Home open.
- No stored player, tournament or score data was changed. GitHub setup/commit/push remain deferred; this folder has no .git directory. Device Hub remains waived for this web app as previously requested.

## 2026-10-08T20:58:04+02:00 — Slovak localization and simplified public results

- Added league/localization.py with Slovak as the default language, an English alternative in the sidebar, and translated navigation, public/admin labels, help text, table/editor headers, scorecards, status/action values and validation messages. Golf outcome terms and category codes are retained. Stable internal values, record IDs, editor keys and stored business data are unchanged. Keyed selections survive language changes; native Streamlit toolbar/uploader labels retain vendor wording.
- Removed Raw throws from every leaderboard view selector (Home, League and Tournament), retaining relative-to-par and handicap views. Stale raw-view session selections fall back to relative-to-par. Raw totals remain available as factual score columns and in statistics; domain compatibility is retained for existing data/tests.
- Removed Home's four count tiles. Made each League tournaments row a full-width navigation button that opens and preselects its tournament. Converted placement points text into a Place/Points table. Removed both requested league captions about ranking/category changes and rounded tied points.
- Centralized download-button gating to authenticated admin sessions, covering result and statistics CSV exports. Public pages also hide the table's native Download as CSV toolbar button; signing out or session expiry hides exports again.
- Updated README and tests for Slovak defaults, language switching, localized admin save, stable score/view selection, removed tiles/raw option, placement table values, league-to-tournament navigation and public/admin export visibility. All 41 automated tests passed on disposable fixtures.
- Verified default Slovak Home, translated table headers, no public CSV controls, league points table and clickable tournament navigation in the in-app browser. Verified English switching and restored Slovak. Saved slovak-home-preview.jpg and slovak-league-preview.jpg; left the fresh preview tab open.
- No real player, tournament or score records were modified. GitHub setup, commits and pushes remain deferred; no Git repository exists in this folder. Device Hub remains waived for this web app as previously requested.

## 2026-10-08T21:23:51+02:00 — More prominent leaderboards and compact placement points

- Changed Home, League and Tournament standings to styled display tables with 21 px bold cell text, 15 px headings, generous padding, a 2 px cream border and rounded corners. Scoped CSS also styles the nested Markdown text so the actual rendered font is 21 px. Retained category tints, cream Home rows, medals, tied ranks, Slovak headings and admin-only CSV exports. Narrow layouts can scroll wide tables horizontally.
- Moved Bodovanie podľa umiestnenia below league player standings, reduced its heading to a caption and constrained the two-column table to 240 px with height based on the number of point entries.
- Updated README and existing UI assertions for the display-table rendering and caption. All 41 automated tests passed with temporary data. Visually verified Home and League; browser computed text size confirmed 21 px. Saved large-leaderboard-preview.jpg and compact-league-preview.jpg and left the League screen open.
- No stored business data was changed. GitHub/commit/push setup remains deferred and no Git repository exists; Device Hub remains waived for this web app as previously requested.

## 2026-10-08T21:30:41+02:00 — Consistent centred table text and no points scrollbar

- Replaced the mismatched 21 px body / 15 px header styling with consistent 17 px typography and line height across Home, League and Tournament standings and the points table. Centred every header and value horizontally, allowed text wrapping and adjusted padding to prevent crowded column headings.
- Replaced the fixed-height points grid with a compact 240 px static table below the standings. It grows naturally to display every configured placement, without a horizontal or vertical table scrollbar. Retained localized headers and integer points.
- Updated README and the existing points UI assertion for the display table. All 41 automated tests passed using temporary data. Browser inspection confirmed centred 17 px headers/values, all eight points rows and identical client/content dimensions (238 px width, 276 px height), verifying no points-table overflow. Saved centered-league-preview.jpg and left the League screen open.
- No business records changed. GitHub/commits/push remain deferred (no Git repository exists); Device Hub remains waived for this web app as previously requested.

## 2026-10-08T21:44:01+02:00 — Vertical alignment, bottom clearance and stronger theme contrast

- Removed horizontal centring from leaderboard and placement-points tables, restoring normal left-aligned text and right-aligned numbers. Kept consistent 17 px text and explicit middle vertical alignment. Set rows to at least 48 px and added 4–8 px container padding.
- Found the clipping cause in Streamlit’s nested Markdown container: a -16 px bottom margin made text extend beyond rows. Reset this margin inside the display tables. Browser geometry now shows balanced 11–11.5 px above/below cell text and 11 px between the final row and outer border. The points table still grows naturally without a table scrollbar.
- Added league/presentation.py for category palettes. Replaced low-opacity washes with distinct solid category fills and explicit dark text. Light uses softer colours; Dark and the custom forest-green theme use stronger colours, selected from Streamlit’s reported theme at render time. Both remain readable if theme context is temporarily stale; Refresh results applies the reported palette after an appearance change.
- Updated hole_heat_styles to three stronger solid green/orange levels per direction with readable text and separate light/dark palettes. Retained all deviation/percentage thresholds and neutral cells around par and for zero/Par percentages. Applied to public and Admin layout statistics.
- Updated README and palette assertions; added colour-contrast coverage for all category colours and heat-map levels, requiring at least 4.5:1 text/background contrast. All 42 automated tests passed on temporary fixtures.
- Visually verified category colours in Custom and Light, and hole heat maps in Light, Dark and Custom. Restored Custom Theme and left League open. Saved contrast-league-light.jpg, contrast-league-custom.jpg, contrast-heatmap-light.jpg, contrast-heatmap-dark.jpg and contrast-heatmap-custom.jpg.
- No stored business data changed. GitHub/commits/push remain deferred and no Git repository exists. Device Hub remains waived for this web app as previously requested.


## 2026-10-08T22:06:54+02:00 — Approved roster reset and preparation for real uDisc exports

- Resolved the contradictory deletion instruction with the user: delete all tournaments, retain league/course/layouts. Removed both tournaments, all 7 recorded rounds, 3 registrations and 9 previous players. Kept leagues, courses, layouts, categories and existing settings exactly unchanged. Used Store validation and expected-version checking for the atomic save, then reloaded and compared preserved collections.
- Created the requested roster with 24 unique players at handicap 0: 8 MPO, 5 FPO and 11 MA3. Per user clarification, consolidated Pali Kozák/Pavol Kozák as Pavol Kozák, username palikk. Preserved requested accents, usernames and categories. Allowed an empty surname for the requested single-name players Tomas and Viktor while retaining required first names and unique uDisc usernames; added localized validation and surname help text.
- Saved full JSON backups before reset under data/backups/league-before-roster-reset-20261008-220338.json and data/backups/league-before-approved-roster-reset-20261008-220507.json. Added the backup directory to .gitignore to keep local user data out of future commits.
- Inspected the supplied 2026-09-19 uDisc XLSX read-only. Its Event results worksheet has 19 player rows and username/division/round_total_score/round_relative_score/hole_1 through hole_18 columns. It has no per-hole par metadata: hole_2 contains throws. The exported totals imply par 62 for all categories; existing green default par is 62 but FPO override is 64. User chose importer preparation only and to wait for corrected per-hole pars. No tournament was created and no workbook scores were saved; layouts were not modified.
- Prepared automatic column defaults for this export format, optional relative-score mapping and validation of exported total par against each category's selected layout, in addition to existing sum-of-hole checks. Unknown usernames, duplicate rounds and par conflicts block confirmation. Added a localized explanation that layout selection cannot be inferred from throw counts. Updated README.
- A dry run on an isolated copy of the new roster matched all 19 usernames, validated 15 result rows and correctly rejected all four FPO par mismatches. All 45 automated tests passed, including mononyms, this uDisc column format, category par checks and source-state preservation. Verified the reset public Home and zero handicaps/usernames in Admin Players in the in-app browser; saved roster-reset-preview.jpg.
- GitHub/commit/push remain deferred by the earlier user instruction; this folder has no Git repository. Device Hub remains waived for this web app as previously requested.


## 2026-10-08T22:14:29+02:00 — Explicit import layout and calculated relative scores

- Added a required course/layout selector to the uDisc Excel/CSV import after the source preview. No mapping preview or confirmation appears before a layout is chosen. Hole mapping and preview par now use the selected layout's category profile. Preview includes Layout and calculated Score relative to par.
- Confirming an import updates the tournament layout and records the scores together through the existing atomic/version-checked save. Previews operate on a copy and never change the live data. A tournament with existing scores must retain its layout; invalid layout IDs are rejected.
- Removed relative-score column mapping and the previous exported-par mismatch check. Both event_relative_score and round_relative_score are ignored, including invalid values; relative-to-par scores are calculated from absolute throws and selected category pars. Absolute total versus sum-of-hole validation remains in place.
- Added Slovak labels/help/errors and updated README. Updated import tests to assert ignored exported relative values, category par recalculation, atomic layout selection, source-state preservation, invalid layouts and existing-score layout protection. All 46 tests passed.
- Verified the required layout selection, automatic username/division/total/hole mappings, enabled preview and confirmation with the actual supplied XLSX in a disposable local preview on port 8502. No import was confirmed. Saved import-layout-preview.jpg, closed the test browser, stopped the temporary server and returned to the real app on port 8501.
- Verified live data still has 24 players, zero tournaments and zero rounds. No league/course/layout/player data was changed. GitHub/commits/push remain deferred by the earlier user instruction (no Git repository exists). Device Hub remains waived for this web app as previously requested.


## 2026-10-08T22:58:54+02:00 — Simplified statistics and sortable league standings

- Removed Course, Ace % and Albatross or better % columns from displayed/exported hole statistics in public Statistics, Tournament statistics and Admin layout statistics. Retained all original recorded outcomes, denominator calculations, category filtering and heat-map colours. Updated captions so they no longer claim the displayed percentages sum to 100% when some outcomes are hidden.
- Removed course and layout overview sections/exports, both hole-statistics bar charts and the redundant public course selector. Retained all-time/tournament scopes, layout/category filters, round averages and per-hole statistics. Backend course/layout overview functions and source data remain available.
- Temporarily removed leaderboard metric selectors on Home, League and Tournament. Cleared stale metric selections and forced relative-to-par ranking for current public results. Hid HCP adjusted/Handicap columns from result tables and result CSV exports. Retained handicap editing and backend ranking calculations for future use.
- Changed the League standings display to a native sortable grid: click a column header to reorder displayed rows without changing category ranks or points. Retained tied-place labels, category colours, integer points, admin-only downloads and compact static points table below. Set row height to 48 px and grid height to fit every result plus clearance.
- Added Slovak captions and updated README. Updated existing UI assertions for hidden view controls and simplified scope filters, and added coverage for omitted columns/charts/overview sections, sortable native league results, retained relative scores, category styling and admin layout statistics. All 47 tests passed using temporary data.
- Visually verified native player-name sorting (ascending arrow and alphabetically reordered rows), hidden handicap/view controls and simplified hole heat map in an isolated local preview. Saved sortable-league-preview.jpg and simplified-statistics-preview.jpg. Closed the disposable preview, stopped its server, and opened the real app at port 8501 in a retained tab. Verified the real JSON file's SHA-256 is unchanged from the start of verification and remains valid.
- GitHub/commit/push setup remains deferred by the earlier user instruction; no Git repository exists. Device Hub remains waived for this web app as previously requested.


## 2026-10-08T23:09:41+02:00 — Hide tournament completion column and format hole lengths

- Removed Complete (Slovak Dokončené) from result table columns and CSV exports. Retained completed-players filtering and backend completion/points eligibility rules.
- Applied zero-decimal metre formatting to length columns in Admin layout editors/read-only hole tables, Admin layout statistics, public all-time/tournament hole statistics and tournament round scorecards. Layout total-length metrics also display no decimals. Editor lengths use a step of one metre; stored measurements and historical snapshots remain unchanged.
- Updated README. All 47 existing automated tests passed. Verified the actual Tournament screen has no Dokončené column and its hole statistics show lengths such as 133, 134 and 52 without decimal suffixes. Saved tournament-columns-preview.jpg and integer-hole-lengths-preview.jpg; retained the app tab.
- No business records were changed. GitHub/commits/push remain deferred by the earlier user instruction (no Git repository exists). Device Hub remains waived for this web app as previously requested.


## 2026-10-08T23:21:55+02:00 — Retained categories and combined, layout-specific statistics

- With explicit deletion approval, reduced stored/default categories to MPO, FPO and MA3; removed unused FA3, MJ18, MJ15 and FJ15 from the category list and tournament enabled-category lists. Confirmed no player/round/registration used a removed category. Preserved all 24 players, 60 rounds and 60 registrations, plus leagues, courses, layouts and profile snapshots. Saved a full backup at data/backups/league-before-category-cleanup-20261008-231831.json before an atomic expected-version save.
- Added All (Celkovo in Slovak) to public all-time, Tournament and Admin layout statistics. Combined views aggregate by layout and hole number only, giving exactly one set of holes across playing categories and historical tee configurations. Each recorded hole score has equal weight. Outcomes and relative scores use that score's recorded par, so differing category pars are respected; displayed Par is a weighted average formatted to two decimals. Known positive lengths are averaged and displayed as whole metres; unknown zero lengths do not lower combined distance. Individual-category views retain historical tee separation.
- Removed All layouts from public statistics; selecting a specific layout is required. Tournament scope limits the layout selection to its tournament's layout; the Tournament screen and Admin layout stats are already scoped to one layout. Empty layout collections show an availability message.
- Added localized combined-statistics labels/captions and updated README. Preserved language switching by capturing the formatter language for each widget render. Kept junior-profile coverage in explicit disposable test fixtures while new app defaults use only the requested three categories.
- All 49 automated tests passed, including per-score weighting, differing pars, historical tees, separate layouts, unknown lengths, combined English/Slovak labels, per-category selection and public/Admin statistics. Verified actual stored results yield exactly holes 1–18 for each of Cervena and Zelena in combined mode. Verified category options Celkovo/MPO/FPO/MA3 and layout options Cervena/Zelena only in the browser; saved combined-category-statistics-preview.jpg and retained the Statistics tab.
- GitHub/commits/push remain deferred by the earlier user instruction (no Git repository exists). Device Hub remains waived for this web app as previously requested.


## 2026-10-08T23:26:30+02:00 — Alternating Home leaderboard row colours

- Toned down odd rows (1, 3, 5…) to #DED9C7, alternating with the existing #EAE4D0 cream background. Alternation starts again in each category leaderboard. Preserved fonts, vertical alignment, medals, rankings and numeric emphasis.
- Verified Python syntax and contrast of both row backgrounds against the brown name and green numeric text (at least 4.5:1). Visually checked the running Home page and saved home-striped-rows-preview.jpg. No business data changed.
- GitHub/commits/push remain deferred by the earlier user instruction (no Git repository exists). Device Hub remains waived for this web app as previously requested.


## 2026-10-08T23:28:13+02:00 — Initial GitHub repository

- User authorized creating a new repository and pushing all changes. Initialize main and create private Lukas18/swam-jahodna-liga; include application source, legacy templates/migration, tests, configuration examples, documentation and current data/league.json. Keep actual secrets, virtual environment, runtime caches, local backups, legacy SQLite database and browser verification screenshots excluded.
- Updated README with repository/data inclusion details. All 49 automated tests passed before the initial commit. Browser verification of the current Home row styling was completed in the preceding change; Device Hub remains waived for this web application.


## 2026-10-08T23:42:41+02:00 — Remove explanatory result captions

- Removed public read-only sidebar label and explanatory captions for Home standings, league points scope, tournament rankings, round averages, layout profiles and hole statistics (heat-map thresholds, combined weighting and per-category methodology). Retained section labels, event metadata, empty-state messages and admin form instructions.
- Verified all 49 tests passed and actual Home/Statistics views no longer contain the removed captions. Saved clean-statistics-preview.jpg. Confirmed local admin password exists without exposing it; documented that cloud deployments require their own top-level admin_password in Streamlit Secrets. Authentication behaviour and business records remain unchanged.
- Commit and push these changes to main in the private GitHub repository. Device Hub remains waived for this web application.


## 2026-10-13T23:49:27+02:00 — Bulk create missing CSV players

- Added import_players.py for username/name CSV pairs, Supabase document loading and a single atomic revision-checked save with --apply. Default mode previews only; optional --preview-json performs an offline preview. Credentials load from environment or an ignored secrets file and are never printed. Existing username/name matches and repeated rows are skipped without modifying players. New players use HCP 0, FPO for final name words ending ova/ová (case-insensitive and Unicode normalized), otherwise configurable MPO default. Missing fields/categories abort before saving.
- Added four focused tests covering suffixes/diacritics/surname-only names, existing player preservation/idempotence, missing categories and BOM/delimiter/empty fields. All four pass. Supplied CSV dry run against local snapshot finds 27 additions and 19 skips; no app data written. Full 53-test suite attempted: 19 errors and one failure in existing storage/UI tests with current Supabase configuration (missing SUPABASE_URL/KEY).
- Updated usage documentation. Preserve the pre-existing uncommitted streamlit_app.py edit. CLI behavior verified with tests and dry run; Device Hub remains waived for this web application.


## 2026-10-14T00:21:10+02:00 — Historical tournament workbook batch

- Added import_tournaments.py to derive titles, dates and red/green layouts from filenames, preview all workbooks, resolve players/categories, import through existing score validation, and save one revision-checked Supabase update. Supports explicit league/year assignments, creating/reusing named leagues with copied scoring rules, missing-layout overrides and explicit exclusions. Existing identical rounds retain original IDs/snapshots; conflicting existing scores abort without overwrite. Creates an ignored pre-save backup and verifies persisted JSON.
- User confirmed 2025 events belong to Discgolf Liga Jahodna 2025; create Discgolf Liga Jahodna 2026 Jar/Leto for 2026. Copied existing 2025 points rules for the new league without changing active-league configuration. User confirmed 28 June 2026 is Zelena; skip Martin Kellner result (missing username), Monika and Tothova (no hole scores).
- Inspected 23 workbooks / 208 source entries and imported 23 new tournaments / 205 scored rounds, including registrations: 17 tournaments for 2025 and 6 for 2026. Saved Supabase revision 50 and verified exact read-back. Backup: data/backups/before-tournament-import-20261014-002009-242186.json. A second preview gives zero additions; existing players, courses, layouts, league settings, tournaments, rounds and registrations remain unchanged. Dates use canonical ISO storage.
- Six tournament-import tests and four player-import tests passed; 29 existing domain/import/ranking/statistics/presentation/localization tests passed. Broader storage/UI suite remains dependent on Supabase test configuration as noted in the preceding change. CLI dry-run and actual persisted records verify behavior; Device Hub remains waived for this web app. Updated README; preserve unrelated uncommitted parseDGdata.py and streamlit_app.py edits.


## 2026-10-14T00:33:11+02:00 — Statistics number formatting

- Format Par as an integer in public/Tournament/Admin layout hole statistics, including combined category views. Convert the presentation frame Par to whole integers with half-up rounding; round average and percentage columns to two decimal places so exports and table data have no excess precision. Retain NumberColumn two-decimal formatting for averages/percentages, including trailing zeros. No changes to stored pars, aggregation or scoring rules.
- Verified presentation transformation, integer dtype, half-up rounding, two-decimal values and unchanged input data. Seven existing statistics/presentation/localization tests pass. Streamlit AppTest with a read-only Supabase snapshot verifies Slovak and English Statistics screens render without exceptions and contain integer Par and rounded average/percentage data. No application data written.
- Preserve unrelated existing parseDGdata.py and streamlit_app.py CSS edits; commit/push only this formatting change and documentation. Device Hub remains waived for this web application.


## 2026-10-14T00:40:10+02:00 — Relational data-model proposal and backup

- User requested a reviewable proposal before deciding and prohibited commits before verification. Added docs/DATA_MODEL_PROPOSAL.md with normalized PostgreSQL tables, required junctions, historical score snapshots, transactional writes, access rules and an additive migration/rollback plan. No SQL executed and no application/storage behavior changed.
- Took read-only export of the complete app_data table (one document, revision 50), verified JSON read-back equality and SHA-256, and saved owner-only backup data/backups/supabase-app-data-before-schema-review-20261014-003911-361394.json with checksum sidecar. Baseline: 51 players, 3 leagues, 29 tournaments, 1 course, 2 layouts, 291 entries/scorecards and 5,238 hole scores. Export covers application records, not database DDL or unrelated tables. No Supabase data modified or deleted.
- No commit or push performed per current instruction. Preserve existing unrelated local modifications. Proposal verification used code relationships and current records; no UI behavior changed.


## 2026-10-14T00:50:27+02:00 — Handicap history and Stableford model extension

- Extended docs/DATA_MODEL_PROPOSAL.md with versioned handicap calculation runs, per-player/event before/used/after snapshots, explicit rolling-window source events, player current-handicap pointer and nullable per-tournament/player Stableford results. Defined first-event score bootstrap, chronological last-10 update for the next event, retrospective recalculation dependencies and audited preservation of original imported handicaps.
- Added display requirements for event-specific handicap, current handicap on aggregate standings and a dedicated history table. Stableford stays pending until its formula and handicap allocation rules are agreed. Score basis and handicap rounding are awaiting user clarification. Proposed completed-event and multi-round conventions are explicitly marked for review.
- Verified the worked example and the 10-event cutoff. Inspected the existing verified backup: no multi-round events or same-day per-player event ambiguities in revision 50. No new Supabase read/write, schema migration or data changes; existing verified backup preserved. No commit or push per review constraint.


## 2026-10-14T01:09:26+02:00 — Relational implementation and automatic historical handicaps (uncommitted review build)

- User authorized implementation and confirmed relative-to-par scoring with integer upward rounding (7.1 → 8, −6.8 → −6). Added league/handicaps.py: first-event bootstrap, last-10 completed-event rolling means, per-event handicap used/next snapshots, cross-league chronological ordering, multi-round event normalization, explicit same-day ordering, pending debut profiles, immutable original_handicap audit values and Stableford pending_formula placeholders. Corrections/backdated data rebuild the versioned history deterministically; original throws/pars/lengths remain unchanged.
- Added league/relational.py adapters, generated sql/001_relational.sql and generator, and migrate_relational.py. Separate schema tables store entities, profiles/holes, relationships, scorecards/hole scores, handicap runs/history/window sources, Stableford results and settings. Foreign keys/uniqueness, global optimistic revision lock, atomic batch saves, server-role-only RPCs, changed-row upserts and archival retention. No DELETE/TRUNCATE, no legacy app_data writes in relational mode. Adapter preserves optional fields, original timestamp representations, numeric text precision and extra metadata. Migration previews and refuses differing existing normalized documents; fresh backup, source-revision checks, full read-back verification and final legacy-source equality checks protect cutover.
- Updated Streamlit Home/League/Tournament/player views with current/event-specific integer handicap columns, adjusted scores and pending Stableford; added Slovak/English Handicap history page and automatic read-only profile handicap. Added same-day tournament order control. Unified old database helpers with versioned Store; CLI importer config honors relational model secrets/environment. Existing JSON backend remains default until migration/cutover. Updated example secrets, README, proposal and detailed docs/RELATIONAL_MIGRATION.md.
- Took verified owner-only backup data/backups/before-relational-implementation-20261014-005633-787725.json (revision 50) and SHA sidecar before implementation. Final live read confirms app_data rows exactly equal that backup. No production SQL/data migration performed: user elected to execute the prepared SQL in Supabase; completion is pending. Nothing deleted or committed/pushed.
- All 69 Python tests pass after replacing obsolete GitHub/file backend assumptions with isolated Supabase RPC mocks and file-backed UI fakes (tests cannot write to production). New coverage includes ceiling/negative scores, first-event bootstrap, rolling 10 cutoff, backdated corrections, pending/incomplete/multi-round events, same-date ambiguity, idempotence and lossless adapters. PostgreSQL/PGlite integration ran additive SQL twice on an isolated in-memory database, copied all 5,238 holes and verified every reconstructed domain field, stale-write rejection, rollback on bad totals, anon/service-role permissions and archive retention.
- Read-only review Streamlit server runs on port 8502 using the backup and rejects every save; browser verified Home integer handicaps and Richard Melichar's historic used/next snapshots. Saved handicap-history-preview.jpg and retained the preview tab. Device Hub remains waived for this web app. Preserved unrelated parseDGdata.py and pre-existing Streamlit CSS changes.


## 2026-10-14T08:08:09+02:00 — Supabase relational copy and local cutover

- User confirmed the SQL was installed and authorized updating the rest. Attempted the additive migration; PostgreSQL rejected integral legacy placement points encoded as 10.0 for integer columns. Verified the whole failed transaction rolled back (no normalized document existed) and legacy app_data still exactly matched the pre-implementation backup. Corrected the serializer to emit genuine JSON integers for integer columns and reject fractional values instead of truncating; added a regression test. No schema changes were required.
- Retried migration successfully: 51 players, 3 leagues, 29 tournaments, 291 entries/scorecards, 5,238 holes, 291 handicap snapshots, 1,575 source-window links and 291 Stableford placeholders. Compared every reconstructed domain field with the reviewed legacy transformation, including original score snapshots. Normalized document revision 1; original JSON remains revision 50 and unchanged. Repeat migration reports already migrated/verified with no further writes.
- Created verified owner-only pre-copy backup data/backups/before-relational-copy-20261014-080526-343087.json and post-copy normalized backup data/backups/after-relational-copy-20261014-080703-560080.json, with SHA-256 sidecars. No data deleted. Set ignored local secrets DISCGOLF_STORAGE_MODEL to relational without exposing or changing credentials.
- Replaced our prior read-only preview server on port 8502 with the actual app. Automatic approval review rejected the initial restart command because its default binding could expose data to LAN/internet; successfully used the safer explicit 127.0.0.1 loopback binding. Browser reloaded and verified Home integer handicaps against the live store; saved relational-live-preview.jpg and retained the tab. All 70 Python tests passed. Updated migration/proposal/README status.
- Hosted deployment has not been changed: it needs the reviewed code and matching storage-model setting. No commit or push per the review instruction. Preserved unrelated local edits.


## 2026-10-14T09:33:19+02:00 — Scoring trends, player search and statistics readability

- Added Stats chronological scoring trend per selected course/layout/category and existing all-time/tournament scope. Includes all players, an individual player, fixed Top 3 and fixed Top 5 cohorts. Default top selection uses best mean relative-to-par event score; each event's combined point equally weights each player's mean round score. Cohort names are shown; exact ranking uses rational averages with deterministic name/ID tie-breaks. Missing participation is omitted rather than scored zero. Selected-layout trends remain isolated; a separate Whole course graph mode explicitly combines the course’s layouts while hole-statistics tables remain layout-specific. Recorded pars are used, and the chart has a neutral par baseline, green below-par/orange above-par points, theme-aware line and two-decimal display/tooltips. Added a course selector only for multiple-course data.
- Added accent-insensitive case-folded player search fields to public history/individual trend and Admin editing/registration. Both accented/unaccented input match either spelling; Admin can also search usernames. Empty/no-match queries do not crash selectors. Preserve previously selected registration players when narrowing another search. Stored names and identifiers are not changed.
- Sorted handicap-history rows by event date/order descending and placed current handicap beside the player controls. The user's placement sentence was incomplete; requested clarification and used the suggested beside-selector placement after a reasonable response interval. Requested top-cohort criterion clarification and used the suggested best-average criterion, documented in UI help. Both remain adjustable if the user specifies otherwise.
- Changed all public/Tournament/Admin layout percentage tables and exports to whole-number half-up display values; averages remain two decimals. No database/schema writes. Existing no-commit instruction remains active; no commit or push performed. Updated README.
- Added tests for accent normalization in both directions, username visibility, trend chronology/player filtering/equal weighting/layout isolation, fixed top cohorts and missing events, whole-percentage values with two-decimal averages, newest-first history and search/no-match UI. Full suite passes 76 tests. Streamlit 1.50 uses use_container_width for Altair; verified actual live Stats Top 3 graph and integer percentages in browser. Saved scoring-trend-preview.jpg. Browser verified Mar matches Mário Haško, newest date 2026-10-10 appears first, current handicap sits beside controls, and percentages are integers. Saved handicap-search-preview.jpg; retained the app tab. Two final targeted UI tests also passed after chart-display rounding. Device Hub remains waived for this web app.


## 2026-10-14T10:02:58+02:00 — Smooth trend approximation

- Replaced point-to-point trend line and raw point markers with a broader local-regression (LOESS) approximation, bandwidth 0.6, rendered with a smooth basis spline and slightly stronger stroke. Preserved all course/layout/player/top-cohort filters, theme colours and neutral par baseline. Tooltips now label fitted estimates instead of implying an actual event score.
- Average same-day event values for the visual fit; use a fitted straight line with 2–4 unique dates and an informative message when fewer than 2 dates exist. No extrapolation beyond the observed period. Underlying event scores, statistics, rankings and handicaps remain unchanged; no Supabase writes. Updated existing UI regression fixtures to provide two actual dates where a trend is asserted and expect no trend for a single date.
- All 76 tests passed. Validated the final spline chart schema and Python syntax; browser verified the broad approximation and absence of raw markers on actual Top 3 data. Updated README. No commit/push per the review restriction; Device Hub remains waived for this web app.


## 2026-10-14T10:52:03+02:00 — Category-specific trends and faster result reads

- Added an independent localized Trend category selector. All/Celkovo and individual categories apply to all-player, individual-player and fixed Top 3/Top 5 graphs, with category-scoped player choices. Hole-statistics category remains independent; recorded historical categories are preserved.
- Profiled read-only live Supabase retrieval: roughly 2.6 MB, 1,005 ms fetch, 227 ms reconstruction and 19 ms redundant handicap recalculation. Reused clients by configuration identity; added isolated shared snapshot caching (10-second TTL, eight entries), current-algorithm handicap reuse and precomputed player/event/layout/category trend summaries. Successful UI/compatibility saves and manual refresh clear snapshots; external writes refresh after expiry. Database revision conflict protection remains active. No Supabase tables or data were changed.
- Replaced repeated nested relational scans/sorts with indexed child collections. Exact full-domain roundtrip verified on the current 291-scorecard dataset; median reconstruction 28.31 ms over ten runs. Warm cached snapshot median 1.30 ms over twenty reads with one underlying load. Existing chart weighting/top cohorts exactly match compact summaries; kept the smooth approximation.
- Added cache reuse/copy isolation, save/refresh invalidation, backend/document isolation, current handicap reuse and client reuse/configuration-change tests. Added multi-round summary/category equivalence and independent chart category/cohort UI regressions. Updated README with cache freshness and future SQL-summary tradeoff. No commit/push per the existing review restriction; Device Hub remains waived for this web app.
- Verification completed: all 82 tests passed; git diff --check clean. Live browser confirmed FPO selects Petra Melicharová, Michaela Malešová and Regina White for Top 3, changes the fitted graph, and leaves the hole table on Celkovo. Saved category-trend-preview.jpg and retained the localhost app tab.


## 2026-10-14T11:42:39+02:00 — Prevent clipped trend axis captions

- Increased the trend chart height from 310 to 350 pixels and added explicit left/right/top/bottom padding inside its responsive fit. Added axis label/title spacing, unrestricted title length and inward-aligned edge date labels with overlap avoidance, keeping the full Slovak captions and ticks within the chart bounds.
- Verified the live browser chart at localhost:8502: full vertical “Priemerné skóre voči paru na kolo”, horizontal “Dátum”, tick labels and bottom spacing are visible. Saved trend-axis-preview.jpg. All 82 tests passed; git diff --check clean. No database changes. Left changes uncommitted per the review instruction; Device Hub remains waived for this web app.


## 2026-10-14T15:16:17+02:00 — Statistics section order and reviewed Git release

- Moved the hole-statistics summary/table above the evolution-of-scores graph on the public Stats page, keeping existing layout, category and tournament filters. Verified the new section order in the live browser; saved stats-order-preview.jpg.
- All 82 tests passed, Python source compilation passed using a temporary bytecode cache, and git diff --check is clean. Scanned the 29 changed/new files for private-key/JWT/GitHub/Supabase secret patterns: no matches. Ignored real secrets, database backups and browser screenshots remain outside Git.
- User explicitly authorized committing and pushing everything, superseding the earlier review hold. Include all accumulated relational-schema/migration, handicap history, search, statistics/trend/cache, importer preprocessing, documentation and test changes in this release. No Supabase writes for this reorder or release. Device Hub remains waived for this web app.


## 2026-10-14T15:54:01+02:00 — Keep the Place header visible across Streamlit table versions

- Found broad CSS hiding the first header cell in every leaderboard/placement table. Local Streamlit 1.50 renders a blank index header before Poradie; newer Streamlit defaults may omit a default RangeIndex, making Poradie the first header and exposing the selector bug. Replaced positional/header-wide selectors with explicit Pandas blank/index-heading classes, preserving data headers and data row headings.
- All 82 tests pass and git diff --check is clean. Browser verified the blank index header remains hidden and Poradie has computed display table-cell; saved place-header-preview.jpg. The public deployment was not inspected directly. No database or secrets changes. Commit/push under the user's standing instruction; Device Hub remains waived for this web app.


## 2026-10-14T17:08:59+02:00 — Compact hole-statistics headers and independent trend layouts

- Removed heatmap styling from Eagle/Birdie/Bogey/Double bogey/Triple bogey or worse percentage columns (Par percentages remain neutral). Retained the three-step below/above-par heatmap solely for score averages across public, tournament and Admin layout tables.
- Shortened displayed average headers to Ø throws / Ø +/− par, localized as Ø hody / Ø voči paru, with full-label hover help. Internal statistic keys and export precision remain unchanged.
- Added a localized, independent Layout grafu selector inside the scoring-trend section. It no longer receives or reuses the hole table's selected layout. Selected-layout mode uses the graph picker; Whole course uses its course; tournament scope restricts layouts to the selected event. Existing category, individual-player and Top 3/Top 5 filters remain active.
- Added a UI regression that switches graph/table layouts independently and checks the fitted chart's available dates and table scope. Updated heatmap tests to ensure outcome percentages are neutral in both themes. All 83 tests passed; git diff --check clean. No database writes. Device Hub remains waived for this web app.
- Live browser verified compact Ø headings and neutral outcome percentage cells. Changed Layout grafu to Jahodna / Zelena while the upper hole-statistics picker/table remained Cervena; saved compact-hole-stats-preview.jpg and retained the app tab.


## 2026-10-14T17:13:41+02:00 — Compact Home standings and horizontal placement points

- Renamed only the Home handicap column to Current HCP / HCP Aktuálne. Kept other handicap profile/history/leaderboard labels unchanged. Home rank/points/attendance/handicap columns now shrink to their content and readable header words, while Name fills the remaining width. Prevented character-by-character header wrapping; retained vertical alignment, zebra shading and tie labels.
- Transposed the league placement-points legend into place-number headers and one points row. Applied explicit Pandas index hiding and existing index-specific CSS, retaining the intended Poradie/Body labels. Changed its container from a 240-pixel vertical box to content width with a maximum of the available page width.
- Updated English/Slovak Home and horizontal-points UI regression expectations and README. All 83 tests passed; git diff --check clean. Browser confirmed Home columns approximately 79/492/81/96/87 pixels, with names taking the remaining space. Verified the scoring legend shows places 1–8 and points 10/8/6/5/4/3/2/1, with its generated header/index cells hidden. Saved home-compact-columns-preview.jpg and horizontal-points-preview.jpg. No database writes; Device Hub remains waived for this web app.


## 2026-10-14T17:24:50+02:00 — Unified result-table headers, alignment and outlines

- Replaced displayed placement headers with # on Home, tournament/league results and the horizontal points legend. Escaped the symbol only in static Markdown-rendered tables to avoid its being interpreted as an empty heading; sortable grids use the literal header. Stored fields and CSV keys remain unchanged.
- Centred styled-table cell/header content horizontally and vertically. Home numeric columns now fit their complete single-line headers; Name fills remaining width. Removed decorative yellow borders/padding from leaderboard and placement-points containers, retaining neutral native table grid lines.
- Added a shared static result-table renderer for hole statistics in Stats/Tournament/Admin layout and for handicap history. Reused Home's 17px header typography, neutral header shade, spacing/alignment and index hiding. Preserved Ø labels, two-decimal averages, integer par/percentages/handicaps, average-only heatmap, exports, filtering and descending history order. Full rows render directly with horizontal overflow available on narrow screens. League leaderboard retains native sorting. Long tournament names in history wrap between words so all six single-line headers fit the available width.
- Updated UI regressions for #/localized headers and the shared renderer; all 83 tests passed and git diff --check is clean. Browser verified actual # display, 48px single-line Home headers, centred text, 0px decorative outline, all 18 hole rows and matching 17px centred headers. Verified handicap history has newest date 2026-10-10 first and fits its 853px container with all headers visible. Saved unified-home-preview.jpg, unified-hole-stats-preview.jpg and unified-handicap-history-preview.jpg. Updated README. No database writes; Device Hub remains waived for this web app.


## 2026-10-14T18:52:37+02:00 — Revert the latest table styling and formatting change

- User requested reverting the most recent table presentation change. Restored streamlit_app.py, tests/test_ui.py and README.md exactly to the preceding commit 14bae58, reversing 1b87bd8 while retaining the full historical change log. Restored Poradie/Place headers, earlier alignment/wrapping/outlines, and grid renderers for hole statistics and handicap history.
- Preserved earlier features including independent trend layout/category selection, Ø average labels, outcome-percentage heatmap removal, compact Home numeric columns and HCP Aktuálne/Current HCP, horizontal placement points, sorting and all database/handicap logic. No Supabase writes.
- All 83 tests passed; git diff --check clean; the three restored files exactly match 14bae58. Browser verified restored Home styling and saved restored-tables-preview.jpg. Preserved the user's unrelated uncommitted league/domain.py debug edit and excluded it from this revert commit. Device Hub remains waived for this web app.


## 2026-10-14T19:05:11+02:00 — Focused Home rank/width and leaderboard outline changes

- Applied only the narrower requested presentation changes after the previous styling revert. Home placement header now renders as # (escaped for static-table Markdown) and only its header/data column is centred. Name remains left-aligned and numeric values remain right-aligned. Numeric column widths fit their complete, unwrapped headers while Name fills the remaining space.
- Removed decorative yellow borders from shared Home/League/Tournament leaderboard containers and the placement-points wrapper. Kept existing table renderers, fonts, general alignment, hole-statistics grids, handicap-history grids and earlier features unchanged. Updated README and existing English/Slovak Home/tied-rank UI expectations.
- All 83 tests passed and git diff --check is clean. Browser verified the literal #, centred rank cells, original alignments elsewhere, no-wrap headers and a 0px decorative border; saved focused-home-tables-preview.jpg. No database writes. Preserve and exclude the user's separate uncommitted league/domain.py edit. Device Hub remains waived for this web app.
- Also browser-verified the League and Tournament leaderboard wrappers each report 0px decorative borders. Returned the app to Home for review.


## 2026-10-14T22:30:09+02:00 — Read-only golf-style handicap simulation for frequent players

- User requested a simulated comparison following TheGrint golf handicap method. Read the referenced article and cross-checked the USGA score-selection guidance. Fetched normalized Supabase document main revision 2 using only dg_load; saved an owner-only, ignored local snapshot data/backups/handicap-simulation-source-20261014-222638.json with SHA-256 sidecar. No database writes or production calculation changes.
- Selected the five busiest players plus the tie at position five: Roman Stefancik (21 completed tournaments), Michal Kapec (19), Majky Csorba (18), Mário Haško (17), Richard Melichar and Tomas Jusko (16 each). Every event is a single 18-hole round. Applied lowest 8 of latest 20, 7 of 19, 6 of 17–18 and 5 of 16, respectively, assuming Course Rating = recorded par, Slope 113 and PCC zero. Explicitly excluded hole caps, exceptional-score reductions and soft/hard caps; estimates are illustrative WHS-inspired selection comparisons, not official golf handicaps.
- Added offline-only simulate_handicaps.py with complete-event checks, 18-hole/total reconciliation, chronological last-20 window, score-count selection rules, attendance ties and independent last-10 baseline. Integer adaptation uses ceiling of the unrounded estimate, retaining negative signs. All six independently recomputed current handicaps match stored profiles. Simulation decimal/integer values: Roman 3.1/4, Michal 8.1/9, Majky 0.2/1, Mário 7.5/8, Richard -2.8/-2, Tomas -2.6/-2.
- Added docs/HANDICAP_SIMULATION_2026-10-14.md with assumptions, comparison, selected event scores, full latest-window values, source provenance/checksum and reproduction command; linked from README. Added five tests for selection boundaries, last-20 expiry, ties, incomplete events, signed rounding, input validation and non-mutation. All 88 tests passed; git diff --check clean. Preserve and exclude the user's unrelated league/domain.py edit. No UI changes; Device Hub remains waived for this web app.


## 2026-10-14T22:49:19+02:00 — Parallel handicap calculations and reversible Admin selection

- User requested implementing the simulation alongside existing handicaps and switching back from Administration. User selected the original handicap as a provisional fallback before three eligible 18-hole rounds. Added league/golf.py with the shared score-selection table and chronological best-of-last-20 snapshots for every completed player tournament. Current and historical integer values retain upward rounding/sign. Non-18-hole/totals-only rounds remain in the original model but do not enter the golf window. Golf method keeps the simulation's par/113/zero-PCC/uncapped assumptions and pending Stableford formula.
- Existing normalized handicap_runs/history/sources tables can hold both algorithms, so no new SQL migration is required. Adapted the lossless serializer to store/split parallel runs and histories as separate relational rows; exact selected rounds and small calculation metadata remain on each snapshot. Original numerical values and history are retained; the generic storage columns keep the original method, while a non-mutating in-memory projection supplies the chosen UI method. Every save recomputes both and restores canonical original fields before persisting. Prior runs/snapshots are archived by existing non-deleting save semantics.
- Added Admin Settings method selector and comparison table; settings edits retain unrelated fields. Public Handicap history supports either method with selected-round counts and provisional status; profiles and handicap-adjusted results follow the active setting. Added backup/preview/CAS/readback backfill_handicaps.py. It keeps the current method by default; initial backfill will leave original active for the user to change in Admin.
- Saved owner-only ignored backup data/backups/before-dual-handicaps-20261014-223821-566635.json plus checksum, including normalized revision 2 and the legacy app_data row. Live preview verifies all existing numerical/score fields/history and reports 291 original plus 291 golf snapshots: 26 players with golf estimates and 24 provisional. Existing source metadata had changed since its prior hash, so derived run IDs/snapshot links refresh; old records remain archived. Both histories exactly match a real PostgreSQL/PGlite RPC roundtrip, including 5,238 holes, conflicts, atomic rollback, permissions and archive retention. Six frequent-player golf values exactly match the prior simulation.
- Added eight calculation/UI regressions covering chronological use without future scores, 3-round provisional transition, signed rounding, selection boundaries/offline parity, multi-round normalized sources, short/incomplete rounds, backdated corrections, legacy value preservation, lossless dual roundtrips and Admin switching back and forth. All 96 tests pass; git diff --check clean. Restarted local loopback server to refresh stale imported modules; deployed Streamlit also needs a reboot. Browser verified authenticated Slovak Admin selector and comparison; saved dual-handicap-admin-preview.jpg. Updated README and docs/HANDICAP_METHODS.md. Exclude the user's unrelated league/domain.py edit. Device Hub remains waived for this web app.


## 2026-10-14T22:51:20+02:00 — Supabase dual-handicap backfill verified

- Pushed the compatible application changes before backfill. Executed backfill_handicaps.py --apply --activate legacy: Supabase main advanced from revision 2 to 3. Verified 291 original + 291 golf snapshots, 50 players (26 calculated, 24 provisional), exact canonical readback and preservation of all original numerical/history/score values. Kept original method active; user can select golf and return from Admin. No records were deleted.
- Saved owner-only before-golf-backfill-20261014-224938-357424.json and after-golf-backfill-20261014-224943-131328.json with checksums under ignored data/backups. Verified original legacy app_data still exactly matches the initial backup. Independent projected golf results read from Supabase match the six-player simulation (-2,4,1,8,9,-2 for Richard/Roman/Majky/Mário/Michal/Tomas).
- Automatic review rejected an attempted repeat --apply idempotence check because it could make an unnecessary additional consequential write. Used a safer read-only load plus in-memory recalculation comparison instead; the saved document is exactly identical and no additional save is needed. No remaining task work was blocked and no repeat write occurred.
- Local authenticated Admin selector/comparison verified and screenshot retained. Public app URL was requested but not supplied; document the required Streamlit reboot before using its new controls. Updated live status in docs/HANDICAP_METHODS.md. Application suite remains 96 passing tests plus PostgreSQL engine checks; the remaining local league/domain.py edit is the user's and remains excluded.


## 2026-10-14T23:18:39+02:00 — Podium rank medals, unwrapped Home headers and public history cleanup

- Moved gold/silver/bronze medals from Home player-name prefixes into the # column, replacing category places 1–3. Podium ties share their medal; subsequent ranks retain correct skipped-place/T labels. Names are displayed without medal prefixes. Numeric points/attendance/handicap values and ranking calculations are unchanged.
- Strengthened the Home header no-wrap rules for every header descendant with explicit important declarations and automatic table layout. This overrides theme/component wrapping rules; numeric columns size to complete headers, Name fills the remainder, and narrow containers can scroll horizontally without wrapping headers.
- Restricted the Handicap history method picker to authenticated administrators. Public history always follows the app's active method and ignores any stale prior Admin selection after sign-out. Removed the calculation explanation caption for all visitors, including Admin; preserved both histories and the Admin Settings method switch.
- Updated Home podium/tie assertions and added a public/admin/sign-out regression for method visibility, active-history values, removed explanation and unchanged stored data. All 97 tests pass; git diff --check clean. Browser verified first rows 🥇/Richard Melichar, 🥈/Tomas Jusko and 🥉/Sean Henderson, all five Home headers remain nowrap/48px, and public history has no picker/explanation after logout. Saved medal-rank-column-preview.jpg and public-handicap-history-preview.jpg. Updated README and method documentation. No Supabase writes; preserve/exclude the user's unrelated league/domain.py edit. Device Hub remains waived for this web app.


## 2026-10-14T23:56:56+02:00 — Historical net Stableford and rare outcome percentages

- Added separate Stableford views on Home, League and Tournament screens for Jesenna SWAM Liga only. Tournament rankings use net Stableford totals, while league standings award existing configured placement points with category competition ranks and occupied-place tie sharing. Retained original score views and both handicap methods.
- Added full integer handicap stroke allocation (positive hardest-first, negative easiest-first, repeated beyond 18), net per-hole scoring and two parallel method results using each tournament's historical handicap. Missing/incomplete per-hole results remain pending rather than guessed.
- Captured pooled difficulty from current score-minus-par statistics, sharing matching nonzero par/length configurations across renumbered layouts. Added administrator priority editor and explicit event snapshot replacement. Frozen per-event index lists prevent later statistics from silently changing prior allocations. Persist through existing normalized result rows and small course/tournament metadata; no SQL migration or deletion.
- Percentages strictly between 0 and 1 retain numeric values with two-decimal display (including trailing zeros); other percentages retain whole-number display. Kept average precision and neutral outcome colors unchanged.
- Saved owner-only checksummed before-stableford-20261014-235252-095948.json from Supabase revision 4. Preview verified 75 calculated results across five target tournaments, unchanged scores and both handicap histories. PostgreSQL engine checks passed for relational roundtrip, CAS, rollback, permissions and archive retention. Added scoring, historical-method, snapshot, scope, tie, percentage and UI coverage; documentation in docs/STABLEFORD.md. Preserve/exclude user's unrelated league/domain.py edit. Device Hub remains waived for this web app.


## 2026-10-15T00:00:40+02:00 — Stableford Supabase backfill verified

- Pushed implementation 657adab, then applied the guarded Stableford backfill. Supabase main advanced from revision 4 to 5: 75 calculated player/tournament results across five Jesenna SWAM Liga events, retained for both handicap methods. Exact readback and every original entity, raw score, handicap history, active golf setting and other league's result were verified unchanged. No data deleted and no SQL migration required.
- Owner-only checksummed backups: before-stableford-backfill-20261014-235932-526880.json and after-stableford-backfill-20261014-235936-925162.json under ignored data/backups. A subsequent read-only load/in-memory recalculation exactly matches revision 5; no repeat write required.
- All 104 tests pass, including explicit difficulty snapshot reset and trailing-zero percentage cases; PostgreSQL checks passed with the full normalized payload. Browser verified Stableford Home places (Richard 36 league points, Sean 30, Tomas 27), Eagle 0.47 alongside whole percentage fields, and the Admin shared-priority editor with explicit event recalculation. Logged out after inspection. Screenshots: stableford-home-preview.jpg, rare-eagle-percentage-preview.jpg, stableford-difficulty-preview.jpg.
- League/tournament editors preserve stored metadata and frozen snapshots when editing event details. Public deployment should reboot Streamlit to reload the new module. Unrelated user change in league/domain.py remains uncommitted and excluded.


## 2026-10-16T07:45:12+02:00 — Extend historical Stableford to earlier leagues

- Enabled the same Stableford calculation and Home/League/Tournament views for all leagues by default, including Discgolf Liga Jahodna 2025 and Discgolf Liga Jahodna 2026 Jar/Leto. Retain explicit per-league opt-out metadata. No changes to the formula, historical handicap selection, category/placement rules or existing difficulty ordering.
- Cache readiness now checks result coverage as well as formula version, so an existing version marker from autumn-only calculations cannot hide pending earlier results. Added cache, cross-league, persistence and unchanged-autumn regressions; adjusted original placeholder assertions and exercised earlier-league UI views.
- Strengthened backfill verification to reject any changes to existing calculated Stablefords, course difficulty configurations or frozen event snapshots, in addition to all original entities, scores and both handicap histories. Saved owner-only checksummed before-earlier-stableford-20261016-074356-168168.json from Supabase revision 5. Preview: 216 additional results (164 from 2025, 52 from Spring/Summer 2026), 291 calculated in total, autumn's 75 unchanged. Keep user's unrelated league/domain.py edit excluded.


## 2026-10-16T07:46:55+02:00 — Earlier Stableford backfill saved and verified

- Pushed implementation 442f79a and applied the guarded backfill to Supabase main, revision 5 → 6. All 291 player/tournament results across 29 tournaments now have calculations for both handicap methods: 164 in the 2025 league, 52 in Spring/Summer 2026 and the unchanged 75 autumn results. Existing raw scores, players, registrations, league settings, both handicap histories and difficulty snapshots were verified preserved; no data deleted.
- Owner-only checksummed backups: before-stableford-backfill-20261016-074628-094295.json and after-stableford-backfill-20261016-074635-975824.json under ignored data/backups. Exact normalized readback verified. No SQL migration required.
- All 106 application tests and full PostgreSQL schema/RPC checks pass. Browser verified the 2025 league's Stableford picker and populated standings (Michal Kapec 86 placement points / 389 Stableford points). Screenshot: earlier-stableford-league-preview.jpg. Device Hub remains waived for the web app; retain the user's unrelated league/domain.py edit. Reboot public Streamlit after deployment to reload Python modules.


## 2026-10-16T07:50:43+02:00 — Sortable tournament scores

- Render Tournament score standings with the existing sortable dataframe grid used for League standings and hole statistics. Column-header sorting now works for both relative-to-par and Stableford views, preserving category colours, integer score formatting and existing category ranks.
- Updated existing UI checks to inspect the interactive grid, including both scoring modes and row colours. All 106 tests pass. Browser verified player-name sorting (Andrea, Diana, Jiří …) on the tournament results. No Supabase writes or scoring changes. Preserve/exclude user's unrelated league/domain.py edit; Device Hub remains waived for this web app.

## 2026-10-24 — Combined tournament round scorecards

- Replaced separate player scorecard tables with one player-by-hole table per recorded round. Each table shows category places, relative scores, recorded hole scores and absolute round totals, with compact score colours and horizontal scrolling.
- Hole headers use shared recorded par and length values; individual score tooltips retain the saved metadata when categories or historical configurations differ. Totals-only records remain visible. No score data or rankings were changed.
