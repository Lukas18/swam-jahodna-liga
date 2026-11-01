# uDisc leaderboard replay

This is a separate local Flask app. It reads a uDisc `.xlsx` workbook in memory and does not edit the Streamlit app or league data.

## Run

From the repository root:

```bash
.venv/bin/python -m replay_app.app
```

If the environment has not been set up, run `python3 -m venv .venv` and `.venv/bin/python -m pip install Flask openpyxl` first. You can also launch the file directly with `.venv/bin/python replay_app/app.py`, including from an IDE.

Open <http://127.0.0.1:5055>, upload the workbook, confirm the layout for each round, and press **Open replay**. Use the timeline, playback buttons, and speed selector. The whole tournament plays continuously across rounds. The division selector filters the standings. Set `PORT` if 5055 is occupied on your computer.

Place changes animate as the replay advances. In Round 1, the up/down place indicator compares with exactly the preceding hole (with no indicator at the first hole); in every later round it compares with the preceding round's final standings. Use **Highlight players** to select several names, or click a name in the standings to toggle its highlight. Highlights remain active across rounds and division filters; chips remove individual highlights.

A floating score change shows each player's latest hole relative to par (`-1`, `+1`, and so on), then rises and fades. Par shows no marker. Birdies (`-1`) show the supplied Troll Face and eagles (`-2`) show the supplied eagle face. +1/+2 score markers are enlarged; +2/+3 show the drifting sad frog; +4 or worse show the supplied crying frog, with +6 or worse largest. All icons follow the Score icons division selection. On a forward step, a +3 or worse hole by any player in the displayed division triggers the supplied [Myinstants sound](https://www.myinstants.com/en/instant/og-roblox-death-sound-effect-uhh-oof-78522/), once for that step. The sound requires an internet connection and a browser that allows playback after interaction. Use **Sound** to mute it. Jumping across several holes with the slider does not trigger sounds for skipped steps.

The app looks for worksheets named `Round 1`, `Round 2`, and so on. It ignores the `Event results` overview. It reads `starting_hole` and `hole_1` through `hole_18`, then rotates each player's playing order from their starting hole and wraps after hole 18. At replay step 1, every player has completed their own first played hole. Round 2 starts after Round 1's 18th played hole. Scores are cumulative throws relative to the par of holes actually completed; ties share places.

The workbook supplies each round's total par, but not individual hole pars. The app reads available course layouts from `data/league.json` **without changing that file**, suggests a layout when its par total matches the export, and checks the choice before replay. You can enter 18 pars manually if no layout matches. Set `REPLAY_LAYOUTS_PATH` to another league JSON file if needed.

The export has a group start time, but no completion time for each hole. Replay therefore shows synchronized snapshots by **played-hole count**, not a historical second-by-second reconstruction. It cannot determine which shotgun group actually completed a hole first. Incomplete hole scores are left uncounted and those players appear below players with complete scores at that step.

The server listens only on `127.0.0.1` by default. Uploads are limited to 8 MB and are not saved.
