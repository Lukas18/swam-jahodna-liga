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

Home omits the league/tournament/player/round count tiles and shows standings for the single active league, separated under category headings, with place, player names, integer points and tournaments attended. Tied category places skip occupied positions. League/tournament result tables and their CSV exports use T labels (for example 1, 2, T3, T3, 5); Home retains those labels below the podium and shows shared medals for podium ties. On Home, gold/silver/bronze medals replace category places 1–3 in the # column (ties share medals); player names contain no medal prefix. Attendance counts events with at least one recorded round, including incomplete events; registration alone does not count. Leaderboard view selectors and handicap result columns are temporarily hidden; public rankings use relative-to-par results. **Admin → Settings** changes the application title and active league; older data defaults to "SWAM Jahodna liga" and the first league without modifying stored records. Home also lists clickable recent tournaments and leagues. Selecting a name opens its corresponding results screen with that record selected. Public navigation contains Home, Leagues, Tournaments, Statistics and the Admin login; all create/edit controls, Players and Courses are under Admin.

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

On the public **Statistics** page, choose **All time**, a **League**, or a **Tournament**, then choose one specific layout and filter by category. There is no All layouts option. Available default categories are MPO, FPO and MA3. The Tournament screen has its own category-specific hole statistics; Admin → Courses & layouts also retains layout statistics. Statistics offer individual categories or All (Celkovo in Slovak). Combined views show one row per hole for the selected layout, merging categories and historical tee configurations. Averages weight every recorded score equally; relative scores and outcome percentages use each score's recorded par. Displayed Par is the sample-weighted par rounded to the nearest integer (halves up), and Length averages only known, positive measurements. Statistics averages and outcome percentages display two decimal places; CSV data is also rounded to two decimal places. Recorded pars and underlying scoring calculations retain full precision. Course columns, the course selector, course/layout overview tables, bar charts, Ace % and Albatross or better % are hidden. Remaining per-hole columns include sample size, average throws, average relative-to-par and Eagle/Birdie/Par/Bogey/Double bogey/Triple bogey or worse percentages. All recorded hole scores remain in the denominators, so visible outcome percentages can total less than 100% when omitted ace/albatross outcomes occurred. Underlying outcome calculations and course data are retained. Totals-only rounds contribute to round averages but not hole statistics. All recorded rounds are included, including incomplete tournaments. For individual categories, historical tee configurations with different par/length remain separate. Combined views merge them into the same hole row.

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

Hole lengths display as whole metres in layout tables/editors, round scorecards and hole statistics; layout total length also has no decimals. Formatting preserves stored measurements. Tournament results omit the Complete/Dokončené column and show completed players without an extra filter control.

Tournament round scorecards show one scrollable table per recorded round, with players as rows and holes as columns. The table shows category places under `#` in both languages, each round's score relative to par, recorded hole scores and the absolute round total. Shared recorded hole pars and lengths are stacked within each hole header cell. Score colors mark aces and under-par results; over-par scores progress from the existing bogey orange through stronger orange for double and triple bogeys to red for four or more over par. When categories have different holes, missing cells stay blank. Totals-only scorecards stay in the table with their round totals.

Explanatory captions below result/statistics tables and the public read-only sidebar label are hidden. Calculation details remain documented here. On Community Cloud, configure the top-level `admin_password = "your-chosen-password"` in app Settings → Secrets, save it, then sign in under Administrácia. Local secrets are deliberately excluded from Git and must be configured separately for hosting.

## Bulk player creation

`import_players.py` reads UTF-8 CSV columns `username` and `name` (semicolon, comma or tab delimited). It defaults to the supplied unique_pairs.csv path and previews without saving:

```bash
.venv/bin/python import_players.py
.venv/bin/python import_players.py --apply
```

Configure SUPABASE_URL and SUPABASE_KEY in the environment, or in the ignored `.streamlit/secrets.toml` (top-level keys or a `[supabase]` url/key section). Use `--secrets PATH` for another secrets file and `--document-id ID` for another app document. Existing players match case-insensitive uDisc usernames or normalized full names and remain unchanged, including their categories and handicaps. Repeated CSV users are skipped. New players receive handicap 0; final name words ending in ova/ová, including surname-only names, receive FPO. Other new players receive MPO (`--default-category MA3` overrides this default). Multiword names split at the final word; single-word names retain a blank surname. Invalid rows/categories abort the import. One version-checked Supabase save persists the entire batch; stale data conflicts abort instead of overwriting other edits.

For an offline preview against a snapshot, use `.venv/bin/python import_players.py --preview-json data/league.json`. This mode cannot save and may differ from the current Supabase data. The script neither registers players for tournaments nor changes scores.

## Bulk tournament workbook import

`import_tournaments.py` scans only `.xlsx` files directly in the supplied directory (not its backup subfolder). It reads the Event results sheet. Filenames ending YYYY-MM-DD supply the tournament date; numbered `sobotnajsie-discgolfove-turnaje-N-turnaj` events use Cervena and display `Sobotnajsie Discgolfove Turnaje (N. turnaj)`. Other filenames use a cervena/zelena token as the layout and remove that token from the title. Dates are stored in the application's ISO format YYYY-MM-DD.

Example for the approved historical batch (preview by default; append `--apply` to save):

```bash
.venv/bin/python import_tournaments.py \
  --league 2025=ff8e51ad521345b3b8661fcb1088e389 \
  --create-league '2026=Discgolf Liga Jahodna 2026 Jar/Leto' \
  --layout nedelny-turnaj-swam-jahodna-2026-06-28.xlsx=zelena \
  --skip-name 'Martin Kellner' --unscored skip
```

The default directory is the supplied Jahodna DG Liga folder. A new league copies the points rules from the first existing `--league` assignment without changing the active league; an existing league with the requested name is reused. Use `--preview-json PATH` for an offline snapshot preview. Supabase credentials and document selection use the same options as import_players.py.

Players must already exist and match by username. Valid division codes (MPO/FPO/MA3) become the event category; export divisions such as 0-18 and 19-54 fall back to each player's category. Relative scores are recalculated from the selected layout; spreadsheet relative scores are ignored. Hole throws must agree with absolute round totals. Imports automatically register scored players. Unknown usernames and invalid scores block the entire save; explicit `--skip-name` and `--unscored skip` exclusions are reported. `--unscored register` registers players without inventing a round.

Existing tournaments match league, date and title. Identical rounds are preserved with their original IDs and par/length snapshots; different existing scores cause an error rather than an overwrite. Before a single revision-checked save the importer creates an ignored JSON backup in data/backups, then reads back the saved document to verify it. Re-running the same batch does not duplicate tournaments or rounds.

## Relational storage and automatic handicap history (review build)

See [migration instructions](docs/RELATIONAL_MIGRATION.md) and [schema](sql/001_relational.sql). The SQL is additive and leaves app_data intact. Run it, preview/copy with migrate_relational.py, verify, then enable `DISCGOLF_STORAGE_MODEL = "relational"` in Streamlit secrets. The existing JSON backend remains the default until cutover.

The app computes one golf-style integer handicap from the best eligible rounds in a player's latest 20 completed 18-hole rounds across leagues. Until three eligible rounds exist, it uses the player's initial HCP provisionally. Each event uses the handicap established before that event; the result can update the handicap for later events. Home, League and player profiles show the current HCP. Handicap history shows the event HCP, next HCP, rounds selected and provisional status. Stableford uses the same historical event HCP and frozen difficulty snapshots; see the Stableford section below.

Relational cutover completed locally on 2026-10-14: the normalized Supabase data was verified at revision 1, with the original app_data revision 50 preserved unchanged. See the migration guide's historical status section for backup paths and verification.

## Scoring trends and accent-insensitive player search

Stats includes a chronological line chart for the selected course/layout and category, with all players, a selected player, or the combined Top 3 / Top 5. If more than one course exists a course selector narrows layout choices; the single-course interface remains compact. The graph defaults to Selected layout; Whole course explicitly includes the course’s layouts while hole-statistics tables remain scoped to the selected layout. Each event point is the mean of each participating player's average round score relative to recorded par (equal player weights); totals-only recorded rounds contribute too. The chart displays a smooth approximation without individual points. A dashed zero line marks par; estimated-value tooltips have two decimals.

Top groups include only players with more than two recorded rounds in the current filters. They form a fixed cohort ranked by lowest mean event score per round, with name/ID tie-breaks to select up to N eligible players. The player list is shown. Events where no selected player participated are omitted; absent players do not count as zero. The graph reflects the selected All time/League/Tournament scope and its own Trend category selector; hole-statistics tables retain their independent category and layout scope.

Use the Search players field on Handicap history, the individual-player trend, Admin player editing and tournament registration to find names without accents: Mar/Már both find Mário. Admin search also matches uDisc usernames; public search matches names only. Original stored names and usernames are preserved. Registration selections are retained while searching for another player.

Handicap history displays newest events first (including same-day event order), with current handicap beside the player selector. Hole-statistics percentage columns now display and export whole integers with half-up rounding, while average columns remain at two decimals. Underlying scoring/statistics calculations retain their original precision. This supersedes earlier two-decimal percentage display instructions.

The trend approximation uses local regression smoothing over 60% of neighboring tournament dates, followed by a smooth spline. Two to four dates use a simple fitted straight trend; fewer than two dates show an insufficient-data message. Multiple events on the same date are averaged for the visual fit only. The display does not extrapolate beyond recorded dates or change event scores, statistics, player ranking or handicap calculations. Raw point markers and the point-to-point line are hidden.


## Trend categories and result caching

Stats now has its own **Trend category / Kategória trendu** selector. It controls All/Celkovo or a specific historical category independently of the hole-statistics table. Individual-player choices and fixed Top 3/Top 5 cohorts use that category together with the selected course/layout and tournament scope. Recorded round categories are used even if a player's profile category changes later.

The application reuses the Supabase client and keeps a shared in-memory read snapshot for up to 10 seconds. Each snapshot includes precomputed player/event/layout/category trend summaries, preserving per-round means and equal player weighting. Filters reuse these summaries; the small smooth curve is fitted for the selected scope. Existing current-version handicap snapshots are reused on reads. Nested relational records are indexed once when reconstructing a document.

Successful app saves and **Refresh results / Obnoviť výsledky** immediately invalidate the read cache, so corrections, deletions and backdated results rebuild all affected trend summaries on the next load. Writes from import scripts, SQL or another app process become visible on the next interaction after the cache expires (at most 10 seconds of cache reuse); manual refresh bypasses that wait. Idle pages do not poll. Returned cached documents are isolated copies, and database revision checks still reject stale saves. Connection/document/storage-model identities keep caches separate.

No extra Supabase table or migration is required for this optimization. Profiling showed the full-document download and repeated relational reconstruction dominated the small trend calculation. On the existing 291-scorecard dataset, reconstruction fell from about 227 ms to 28 ms; a warm cached snapshot read took about 1.3 ms without a database request. These are local measurements, not an end-to-end rendering guarantee. A persisted SQL summary table can be introduced if dataset growth later warrants server-side aggregation.


Hole-statistics headers use **Ø throws / Ø +/− par** (Slovak **Ø hody / Ø voči paru**); hover over a header for the full average label. Only these score-average columns retain the heatmap. Eagle, Birdie, Par, Bogey, Double bogey and Triple bogey or worse percentages use neutral table colours.

The trend section has its own **Trend layout / Layout grafu** picker. It is independent of the hole-statistics layout at the top. Selected-layout mode uses this picker, while Whole course combines layouts within the picker's course. Tournament scope limits its choices to that event's layout; category, player and Top 3/Top 5 selection apply as before.


Home standings label the latest handicap **Current HCP** / **HCP Aktuálne**. Rank, points, attendance and handicap columns use compact widths; the player's name takes the remaining space, and numeric headers stay on one line. The league's placement-points legend is horizontal: places across the header and their corresponding points in one row, with its generated row index hidden.


Home uses **#** for the place header and centres only that column; other column alignments remain unchanged. Numeric columns fit their unwrapped headers, with names filling the remaining width. Yellow decorative outlines have been removed from Home/League/Tournament leaderboard containers and the placement-points legend. Hole statistics and handicap history keep their existing grid renderers and formatting.


## Golf-style handicap calculation

See [the 14 October 2026 simulation](docs/HANDICAP_SIMULATION_2026-10-14.md) for the original research. `simulate_handicaps.py LOCAL_SNAPSHOT --top 5` reproduces best-score selection without connecting to or writing to the database. It assumes Course Rating = recorded par, Slope = 113 and PCC = 0; uncapped scores and omitted WHS safeguards mean these are illustrative estimates, not official golf indexes.


## Single handicap calculation

The golf-style best-of-20 history is the only active handicap history. It uses each player's initial HCP before three eligible 18-hole rounds are available. The last-10 method and method selector have been removed. See [storage, backup and backfill details](docs/HANDICAP_METHODS.md). No additional SQL migration is required; reboot Streamlit after deploying the new modules.


Home table header cells and their content explicitly disable wrapping, so points, attendance and current HCP headers stay on one line even when a theme supplies its own table styles. The table uses automatic column sizing and horizontal scrolling where needed on narrow screens.

### Stableford

All leagues, including the earlier 2025 and Spring/Summer 2026 tournaments, offer a separate net Stableford view on Home, League and Tournament screens. In Home's Stableford view, Total Stableford after Total points sums each player's calculated Stableford scores from tournaments in the active league. Configure frozen hole difficulty under Administration → Hole difficulty. [Rules, snapshots and safe backfill](docs/STABLEFORD.md). Stats percentages below 1% show two decimal places. Reboot Streamlit after deploying new Python modules.
