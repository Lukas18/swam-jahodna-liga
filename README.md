# SWAM Jahodna liga

A small Streamlit app for a local disc golf league. Public visitors browse results without a login. One administrator manages players, categories, leagues, layouts, tournaments and scores.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run streamlit_app.py
```

Open http://localhost:8501. For admin access, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, set a unique password, then sign in on **Admin**. Alternatively set `DISCGOLF_ADMIN_PASSWORD` in the environment. Without credentials the app remains read-only. Sign out when finished. Admin sessions expire after eight hours.

Local data lives in `data/league.json`. `DISCGOLF_DATA_PATH` can override the path. JSON was chosen over several CSV files to keep related records and updates together. There is no database service to operate.

Home omits the league/tournament/player/round count tiles and shows standings for the single active league, separated under category headings, with place, player names, integer points and tournaments attended. Tied category places display with T and skip the occupied positions (for example 1, 2, T3, T3, 5); the same notation appears in league/tournament result tables and their CSV exports. Gold, silver and bronze medals mark category places 1–3 (ties share medals). Attendance counts events with at least one recorded round, including incomplete events; registration alone does not count. Leaderboard view selectors and handicap result columns are temporarily hidden; public rankings use relative-to-par results. **Admin → Settings** changes the application title and active league; older data defaults to "SWAM Jahodna liga" and the first league without modifying stored records. Home also lists clickable recent tournaments and leagues. Selecting a name opens its corresponding results screen with that record selected. Public navigation contains Home, Leagues, Tournaments, Statistics and the Admin login; all create/edit controls, Players and Courses are under Admin.

## Data and migration

The original `app.py`, templates and `instance/discgolf.db` are preserved. They are not used by the new app. Migrate once with:

```bash
.venv/bin/python migrate_legacy.py
```

Migration reads SQLite without modifying it, creates an original layout for each course, adds a Local league, and preserves category par overrides and any recorded scores. It refuses to overwrite an existing JSON file. uDisc usernames and hole lengths were absent in the old data: usernames start blank and lengths at zero (unknown). Update them under Admin → Players and Admin → Courses & layouts.

## Workflow

1. **Admin → Categories:** add/remove category codes. In-use categories cannot be removed, preserving historical results.
2. **Admin → Players:** create/edit players, their default category, handicap and unique uDisc username. Matching ignores case and surrounding spaces. Usernames are shown only to the admin.
3. **Admin → Courses & layouts:** create several layouts per course. Edit the default played holes (hole number, par, length in metres), or save an independent category override. Use the Number of holes control before editing the hole grid. Each category override has its own count, so juniors may play fewer holes and shorter lengths. Category overrides can be removed to fall back to the default.
4. **Admin → Leagues:** create/edit leagues, points scope, number of awarded places and points per place. Ties share occupied-place points by default (two players tied for 1st split 1st and 2nd points). An alternative same-place points rule is configurable. Unlisted places receive zero.
5. **Admin → Tournaments & scores:** choose league, layout, date, categories and rounds. Register selected players for the tournament, then enter scores manually or import a uDisc file. Registration stores a tournament-specific category and handicap independently of the global player defaults. Imports register newly matched players automatically. Only players with all required rounds receive league points. For a player, category and handicap are fixed across a tournament’s rounds.
6. **Results:** league standings rank total placement points. League and tournament rankings currently use relative-to-par scores. Metric selectors and handicap scores are hidden for now; alternate ranking calculations remain available in the domain code for later use. Click league table headers to sort its displayed rows; sorting does not recalculate ranks or points. The League screen shows placement points below the player standings in a compact 240 px Place/Points display table without an internal scrollbar and its tournament rows open the selected tournament. All categories shows one combined table with subtly tinted category rows. Place always means category rank: an FPO winner does not shift an MPO runner-up from second to third; category points are not directly comparable across categories.

### Score entry

Under Admin → Tournaments & scores, add one or several players to a tournament. The manual entry grids show registered players as rows and holes as columns, separated by category for different junior hole counts. Scores begin blank. Tick Save for each completed row and submit that category’s grid; every selected row must have all its played holes filled. Validation is atomic: if any selected row is invalid, no scores in that batch are saved. Existing rows are populated from their recorded round, preserving historical pars/lengths. Registrations cannot be removed or have category/handicap changed until the player’s scores are removed.

### Handicap and history

`Adjusted score = total throws − total par − (handicap × rounds)`, rounded to the nearest integer per tournament. Half values round away from zero. Player handicaps may still use half steps. Adjusted scores remain integer calculations but are currently hidden from results and their CSV exports. League points are displayed as integers. Shared tie points are rounded to the nearest whole point (halves up), so sharing fractional points can slightly increase or decrease the total points awarded. Placement schedules use integers.

Round records snapshot playing category, handicap, hole pars and lengths. Changing a player or layout does not recalculate historical scores. Editing an existing manual scorecard keeps historical pars/lengths. Importing a replacement explicitly records against the current layout. League points rules are live: changing them recalculates standings from existing scores.

Total throw counts remain available in result tables and statistics, while current leaderboards use relative-to-par rankings. No automatic handicap estimation is included; the admin supplies handicaps.

### uDisc Excel / CSV import

Upload `.xlsx` or `.csv`. Choose the worksheet, header row and the course/layout used for the results, then map username, optional category/handicap/round columns, and either hole scores or absolute total throws. Layout selection is required before preview. Confirming the import saves the selected layout with the tournament; a tournament with existing scores must retain its current layout. One row represents one player-round. Files with aggregate multi-round totals need per-round data first. Legacy `.xls` files must be saved as `.xlsx` or CSV.

The app previews matched players and add/replace actions before saving. Unknown usernames, duplicate player-round rows, missing holes and invalid totals block the whole import. Extra junior-unplayed holes are ignored. Replacements need explicit acknowledgement. No players are created from guessed display-name matches. Totals-only files support standings but cannot produce hole statistics.

The supplied uDisc Event results format uses `username`, `division`, `round_total_score` and `hole_1` … `hole_18`; these columns are selected automatically. Imported round totals must equal the sum of hole throws. Both `event_relative_score` and `round_relative_score` are ignored: the app calculates relative scores from throws and the selected layout's category pars. This export contains throws, not per-hole pars: `hole_2` cannot identify a layout by its par. Aces/eagles etc. require absolute per-hole throws. Players using a single name may leave their surname blank; uDisc usernames remain unique.

### Layout statistics

On the public **Statistics** page, choose **All time** or a **Tournament**, then choose one specific layout and filter by category. There is no All layouts option. Available default categories are MPO, FPO and MA3. The Tournament screen has its own category-specific hole statistics; Admin → Courses & layouts also retains layout statistics. Statistics offer individual categories or All (Celkovo in Slovak). Combined views show one row per hole for the selected layout, merging categories and historical tee configurations. Averages weight every recorded score equally; relative scores and outcome percentages use each score's recorded par. Displayed Par is a weighted average, and Length averages only known, positive measurements. Course columns, the course selector, course/layout overview tables, bar charts, Ace % and Albatross or better % are hidden. Remaining per-hole columns include sample size, average throws, average relative-to-par and Eagle/Birdie/Par/Bogey/Double bogey/Triple bogey or worse percentages. All recorded hole scores remain in the denominators, so visible outcome percentages can total less than 100% when omitted ace/albatross outcomes occurred. Underlying outcome calculations and course data are retained. Totals-only rounds contribute to round averages but not hole statistics. All recorded rounds are included, including incomplete tournaments. For individual categories, historical tee configurations with different par/length remain separate. Combined views merge them into the same hole row.

## Free cloud deployment without a database

Streamlit Community Cloud does **not** guarantee local file persistence. Do not rely on its local JSON or CSV files for durable admin saves.

For this small single-admin app, the optional GitHub store writes the JSON file to a separate private data repository. Each save becomes a versioned commit, with SHA conflict detection to prevent a stale admin tab overwriting newer edits. Public viewers never receive the token. A separate repository avoids redeploying the application whenever scores are saved.

When GitHub is ready:

1. Put the application source in an app repository. `.gitignore` excludes secrets, local backups and the original database. The private app repository includes the current league JSON; avoid publishing that data unintentionally. No git setup is required for local use.
2. Create a separate private data repository with a `main` branch and upload the migrated `data/league.json` there as `league.json` (or restore/download a current backup from Admin).
3. Create a fine-grained token restricted to that data repository with **Contents: read/write**. Store the token in Streamlit secrets, never in source control. Configure its expiry and rotate it before expiry.
4. Deploy `streamlit_app.py` from the app repository in Community Cloud. Paste the example secrets with real password and `[github]` values into the deployment secrets settings.
5. Verify an admin save, sign out and check the public results. Keep periodic JSON backups from Admin as well as GitHub history.

A missing/unreachable/misconfigured GitHub data file stops the app or blocks saving; it never silently falls back to temporary local storage. The application source and current league JSON are versioned in the private GitHub repository [Lukas18/swam-jahodna-liga](https://github.com/Lukas18/swam-jahodna-liga). Hosting has not been deployed yet. GitHub API limits and Community Cloud resource limits still apply; this approach is intended for a small league, not a large database. The Contents API store is for JSON below 1 MB; larger data needs a different storage backend.

References: [Streamlit file persistence](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data), [deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app), [secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management), [GitHub Contents API](https://docs.github.com/en/rest/repos/contents).

### Appearance

Category rows use contrasting solid fills with explicit dark text: softer fills for Light and stronger fills for Dark or the custom forest-green theme. Heat-map fills use the same theme distinction. Palette selection follows Streamlit’s reported theme when the app renders; Refresh results updates it after changing appearance if needed. Both palettes remain readable on either background. Other score controls use Streamlit’s native theme colours. Choose Light or Dark in the app settings.

## Verify

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tests cover scoring, ties, league aggregation, snapshots, junior layouts, imports, backup validation, storage conflicts, and public/admin Streamlit screens. Device Hub is not required for this web app.

Hole statistics use a contrasting heat map in both light and dark themes: green for below par, warm orange for above par, with three fill strengths in each direction. Coloured cells use explicit dark text; near-par and zero/Par percentages retain the native theme background. Averages within ±0.25 throws of par are neutral; the remaining bands are up to 0.75, up to 1.50, and over 1.50 throws from par. Outcome percentages use >0–25%, >25–50%, and >50% bands; zero and Par percentages remain neutral. CSV exports retain numeric data without styling.

The default Custom Theme uses forest green backgrounds and cream text inspired by the supplied league poster. Home standings use cream rows, brown player names and green place/points/attendance values. Native controls follow the theme; users can still select Streamlit Light or Dark in the app settings.

## Language and downloads

New sessions default to Slovak. The sidebar **Jazyk / Language** selector switches between Slovenčina and English. App labels, navigation, forms, column headings, help text, scorecards and validation messages are localized; golf terms such as Par, Birdie, Eagle and Bogey and category codes are retained. Stored names, IDs, scoring rules and data keys are unchanged. Language switching preserves keyed navigation and leaderboard selections. Streamlit's own built-in toolbar/uploader controls may retain the vendor's English labels.

CSV download buttons and statistics exports are displayed only during an authenticated administrator session. Public pages also hide the built-in table CSV toolbar control. Admin access still requires the configured password. Public views remain readable without signing in. The League screen no longer includes the explanatory ranking/category-change or rounded tie-point captions; those calculation rules remain documented above.

Home and Tournament leaderboards use consistent 17 px text for headers and values, vertically centred cells, normal left/right alignment and a cream border. League standings use a native sortable grid with category colours, 48 px rows and enough height to include all rows and extra clearance; click a column header to sort. Rows have sufficient height and the table container includes a few pixels of padding below the data. Headers can wrap to fit their columns. The compact placement-points table uses the same vertically centred typography and grows to show every row without an internal scrollbar. Score-entry grids and statistics retain their native controls.

Hole lengths display as whole metres in layout tables/editors, round scorecards and hole statistics; layout total length also has no decimals. Formatting preserves stored measurements. Tournament results omit the Complete/Dokončené column; the completed-players filter and completion rules remain available.
