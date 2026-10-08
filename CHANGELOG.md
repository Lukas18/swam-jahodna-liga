# Change log

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
