import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from league.storage import encoded
from snapshot_store import SnapshotStore as Store
from league.domain import add_round, register_player
from test_league import fixture

APP = str(Path(__file__).resolve().parents[1]/'streamlit_app.py')


def english_app():
    app = AppTest.from_file(APP)
    app.session_state['language'] = 'en'
    return app


class ScreensTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'league.json'
        self.path.write_bytes(encoded(fixture()))
        self.env = patch.dict(os.environ, {'DISCGOLF_DATA_PATH': str(self.path), 'DISCGOLF_ADMIN_PASSWORD': 'test-only-password'})
        self.env.start()
        self.store_patch = patch('league.database.get_store', lambda: Store(self.path))
        self.store_patch.start()

    def tearDown(self):
        self.store_patch.stop()
        self.env.stop()
        self.tmp.cleanup()

    def administrator(self, section):
        app = english_app().run(timeout=20)
        app.session_state['admin_expires'] = time.time() + 100
        app.sidebar.radio[0].set_value('Admin').run()
        app.radio(key='admin_section').set_value(section).run()
        self.assertFalse(app.exception)
        return app

    def test_public_screens_have_no_edit_forms_even_for_admin(self):
        app = english_app().run(timeout=20)
        self.assertEqual(app.sidebar.radio[0].options, ['Home', 'Leagues', 'Tournaments', 'Statistics', 'Handicap history', 'Admin'])
        for signed_in in [False, True]:
            if signed_in:
                app.session_state['admin_expires'] = time.time() + 100
            for page in ['Home', 'Leagues', 'Tournaments', 'Statistics']:
                app.sidebar.radio[0].set_value(page).run()
                self.assertFalse(app.exception, page)
                self.assertFalse(any(b.label.startswith(('Save ', 'Create ', 'Confirm import')) for b in app.button), page)
                self.assertEqual(len(app.text_input), 0)

    def test_handicap_history_and_tournament_handicap_are_visible(self):
        data = fixture()
        add_round(data, 't', 'a', 1, 'MPO', 1, {1: 4, 2: 5})
        self.path.write_bytes(encoded(data))
        app = english_app().run(timeout=20)
        app.sidebar.radio[0].set_value('Handicap history').run()
        self.assertFalse(app.exception)
        rows = app.dataframe[0].value
        self.assertEqual(rows.iloc[0]['Handicap'], 2)
        self.assertEqual(rows.iloc[0]['Next handicap'], 2)
        app.sidebar.radio[0].set_value('Tournaments').run()
        result = next(x.value for x in app.table if 'Player' in x.value)
        self.assertIn('Handicap', result)
        self.assertIn('Stableford', result)
        self.assertTrue(result['Stableford'].isna().all())

    def test_newest_handicap_first_and_accent_insensitive_search(self):
        from league.domain import save_player
        data = fixture()
        save_player(data, 'a', 'Mário', 'Haško', 'MPO', 1, 'Alice')
        add_round(data, 't', 'a', 1, 'MPO', 1, {1: 3, 2: 4})
        data['tournaments'].append(dict(data['tournaments'][0], id='later', date='2026-10-09'))
        add_round(data, 'later', 'a', 1, 'MPO', 1, {1: 4, 2: 5})
        self.path.write_bytes(encoded(data))
        app = english_app().run(timeout=20)
        app.sidebar.radio[0].set_value('Handicap history').run()
        app.text_input(key='handicap_player_search').set_value('Mar').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key='handicap_player').options, ['Mário Haško'])
        rows = app.dataframe[0].value
        self.assertEqual(rows['Date'].tolist(), ['2026-10-09', '2026-10-08'])
        app.text_input(key='handicap_player_search').set_value('Már').run()
        self.assertEqual(app.selectbox(key='handicap_player').options, ['Mário Haško'])
        app.text_input(key='handicap_player_search').set_value('no match').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe), 0)

    def test_trend_modes_and_whole_percentage_data(self):
        data = fixture()
        add_round(data, 't', 'a', 1, 'MPO', 1, {1: 3, 2: 4})
        add_round(data, 't', 'b', 1, 'MPO', 0, {1: 2, 2: 4})
        add_round(data, 't', 'j', 1, 'MJ15', 0, {1: 3})
        data['tournaments'].append(dict(data['tournaments'][0], id='later', date='2026-10-09'))
        add_round(data, 'later', 'a', 1, 'MPO', 1, {1: 3, 2: 4})
        self.path.write_bytes(encoded(data))
        app = english_app().run(timeout=20)
        app.sidebar.radio[0].set_value('Statistics').run()
        for mode in ['All players', 'Top 3', 'Top 5', 'Specific player']:
            app.radio(key='trend_mode').set_value(mode).run()
            self.assertFalse(app.exception, mode)
            self.assertEqual(len(app.get('arrow_vega_lite_chart')), 1)
        app.radio(key='trend_scope').set_value('Whole course').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('arrow_vega_lite_chart')), 1)
        frame = next(x.value for x in app.dataframe if 'Average throws' in x.value)
        self.assertEqual(frame.iloc[0]['Birdie %'], 25)
        self.assertTrue(str(frame['Birdie %'].dtype).startswith('int'))
        self.assertEqual(frame.iloc[0]['Average throws'], 2.75)
        # Graph category is independent of the hole-table filter and restricts its cohort.
        app.selectbox(key='trend_category').set_value('MJ15').run()
        app.radio(key='trend_mode').set_value('Top 3').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('arrow_vega_lite_chart')), 0)  # Junior has just one date.
        self.assertEqual(app.selectbox(key='stats_category').value, 'All')
        app.radio(key='trend_mode').set_value('Specific player').run()
        self.assertEqual(app.selectbox(key='trend_player').options, ['Junior Player'])
        app.selectbox(key='trend_category').set_value('MPO').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('arrow_vega_lite_chart')), 1)


    def test_trend_layout_is_independent_of_hole_statistics_layout(self):
        data = fixture()
        data['layouts'].append(dict(data['layouts'][0], id='second', name='Other'))
        data['tournaments'].append(dict(data['tournaments'][0], id='later', date='2026-10-09'))
        data['tournaments'].append(dict(data['tournaments'][0], id='other', layout_id='second', date='2026-10-10'))
        add_round(data, 't', 'a', 1, 'MPO', 1, {1: 3, 2: 4})
        add_round(data, 'later', 'a', 1, 'MPO', 1, {1: 4, 2: 5})
        add_round(data, 'other', 'a', 1, 'MPO', 1, {1: 5, 2: 6})
        self.path.write_bytes(encoded(data))
        app = english_app().run(timeout=20)
        app.sidebar.radio[0].set_value('Statistics').run()
        self.assertEqual(len(app.get('arrow_vega_lite_chart')), 1)
        app.selectbox(key='trend_layout').set_value('second').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key='stats_layout_alltime').value, 'l')
        self.assertEqual(len(app.get('arrow_vega_lite_chart')), 0)  # Only one date on this layout.
        frame = next(x.value for x in app.dataframe if 'Average throws' in x.value)
        self.assertEqual(set(frame['Layout']), {'Main'})
        app.selectbox(key='stats_layout_alltime').set_value('second').run()
        app.selectbox(key='trend_layout').set_value('l').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key='stats_layout_alltime').value, 'second')
        self.assertEqual(len(app.get('arrow_vega_lite_chart')), 1)
        frame = next(x.value for x in app.dataframe if 'Average throws' in x.value)
        self.assertEqual(set(frame['Layout']), {'Other'})

    def test_admin_switches_handicap_method_and_keeps_both_histories(self):
        from test_dual_handicaps import golf_fixture
        from league.handicaps import recalculate_handicaps
        data = recalculate_handicaps(golf_fixture([1,2,3,10]))
        data['settings']['active_league_id'] = 'lg'
        self.path.write_bytes(encoded(data))
        app = self.administrator('Settings')
        app.selectbox(key='admin_handicap_method').set_value('golf')
        app.button(key='FormSubmitter:application_settings-Save settings').click().run()
        self.assertFalse(app.exception)
        stored = Store(self.path).load()[0]
        self.assertEqual(stored['settings']['handicap_method'], 'golf')
        self.assertEqual(stored['players'][0]['handicap'], 4)
        self.assertEqual(stored['players'][0]['golf_handicap'], 0)
        app.sidebar.radio[0].set_value('Home').run()
        home = next(x.value for x in app.table if 'Current HCP' in x.value)
        self.assertEqual(home.iloc[0]['Current HCP'], 0)
        app.sidebar.radio[0].set_value('Handicap history').run()
        self.assertEqual(app.radio(key='history_handicap_method').value, 'golf')
        history = app.dataframe[0].value
        self.assertEqual(history['Next handicap'].tolist(), [0,-1,2,1])
        self.assertEqual(history['Status'].tolist(), ['Calculated','Calculated','Provisional','Provisional'])
        app.radio(key='history_handicap_method').set_value('legacy').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.dataframe[0].value['Next handicap'].tolist(), [4,2,2,1])
        app.sidebar.radio[0].set_value('Admin').run()
        app.radio(key='admin_section').set_value('Settings').run()
        app.selectbox(key='admin_handicap_method').set_value('legacy')
        app.button(key='FormSubmitter:application_settings-Save settings').click().run()
        self.assertFalse(app.exception)
        after = Store(self.path).load()[0]
        self.assertEqual(after['handicap_history'], stored['handicap_history'])
        self.assertEqual(after['golf_handicap_history'], stored['golf_handicap_history'])
        app.sidebar.radio[0].set_value('Home').run()
        self.assertEqual(next(x.value for x in app.table if 'Current HCP' in x.value).iloc[0]['Current HCP'],4)

    def test_admin_login_edit_and_logout(self):
        app = english_app().run(timeout=20)
        app.sidebar.radio[0].set_value('Admin').run()
        app.text_input[0].set_value('bad')
        app.button(key='FormSubmitter:login-Sign in').click().run()
        self.assertTrue(app.error)
        self.assertNotIn('admin_expires', app.session_state)
        app.text_input[0].set_value('test-only-password')
        app.button(key='FormSubmitter:login-Sign in').click().run()
        self.assertFalse(app.exception)
        self.assertGreater(app.session_state['admin_expires'], time.time())
        next(x for x in app.text_input if x.label == 'First name').set_value('New')
        next(x for x in app.text_input if x.label == 'Last name').set_value('Player')
        next(x for x in app.text_input if x.label == 'uDisc username').set_value('new-udisc')
        app.button(key='FormSubmitter:player_new-Save player').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(Store(self.path).load()[0]['players']), 4)
        for section in ['Leagues', 'Tournaments & scores', 'Courses & layouts', 'Categories', 'Backup & restore']:
            app.radio(key='admin_section').set_value(section).run()
            self.assertFalse(app.exception, section)
        next(b for b in app.sidebar.button if b.label == 'Sign out').click().run()
        self.assertFalse(app.exception)
        self.assertNotIn('admin_expires', app.session_state)
        self.assertTrue(any(b.label == 'Sign in' for b in app.button))

    def test_registration_and_horizontal_score_grid(self):
        app = self.administrator('Tournaments & scores')
        app.multiselect(key='register_players_t').set_value(['a', 'b'])
        app.button(key='register_t').click().run()
        self.assertFalse(app.exception)
        data = Store(self.path).load()[0]
        self.assertEqual(len(data['registrations']), 2)
        self.assertEqual(data['rounds'], [])
        grid = next(frame.value for frame in app.dataframe if 'Save' in frame.value)
        self.assertEqual(len(grid), 2)
        self.assertIn('H1', grid)
        self.assertIn('H2', grid)
        self.assertTrue(grid['H1'].isna().all())
        app.button(key='FormSubmitter:score_grid_t_1_MPO-Save MPO scores').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertEqual(Store(self.path).load()[0]['rounds'], [])
        # Verify a registered existing round renders and still contributes to stats.
        hcp = next(e['handicap'] for e in data['registrations'] if e['player_id'] == 'a')
        add_round(data, 't', 'a', 1, 'MPO', hcp, {1: 3, 2: 4})
        self.path.write_bytes(encoded(data))
        app.run()
        grid = next(frame.value for frame in app.dataframe if 'Save' in frame.value)
        self.assertEqual(grid.iloc[0]['H1'], 3)
        app.radio(key='admin_section').set_value('Courses & layouts').run()
        self.assertFalse(app.exception)
        self.assertTrue(any(m.label == 'Recorded rounds' for m in app.metric))

    def test_public_statistics_scopes_and_tournament_stats(self):
        data = fixture()
        add_round(data, 't', 'a', 1, 'MPO', 1, {1: 2, 2: 4})
        data['tournaments'].append(dict(data['tournaments'][0], id='t2', name='Other event'))
        add_round(data, 't2', 'b', 1, 'MPO', 0, {1: 4, 2: 4})
        self.path.write_bytes(encoded(data))
        app = english_app().run(timeout=20)
        app.sidebar.radio[0].set_value('Statistics').run()
        self.assertFalse(app.exception)
        self.assertEqual(next(m.value for m in app.metric if m.label == 'Recorded rounds'), '2')
        holes = next(x.value for x in app.dataframe if 'Average throws' in x.value and 'Hole' in x.value)
        self.assertEqual(holes.iloc[0]['Average throws'], 3)
        app.radio(key='stats_scope').set_value('Tournament').run()
        app.selectbox(key='stats_tournament').set_value('t').run()
        self.assertFalse(app.exception)
        self.assertEqual(next(m.value for m in app.metric if m.label == 'Recorded rounds'), '1')
        self.assertFalse(any(x.label == 'Course' for x in app.selectbox))
        app.selectbox(key='stats_layout_t').set_value('l').run()
        self.assertFalse(app.exception)
        app.sidebar.radio[0].set_value('Tournaments').run()
        self.assertFalse(app.exception)
        self.assertTrue(any(x.value == 'Tournament statistics' for x in app.subheader))

    def test_simplified_statistics_and_sortable_league(self):
        data = fixture()
        add_round(data, 't', 'a', 1, 'MPO', 2, {1: 1, 2: 4})
        add_round(data, 't', 'b', 1, 'MPO', 0, {1: 3, 2: 4})
        self.path.write_bytes(encoded(data))
        original = self.path.read_bytes()
        app = english_app().run(timeout=20)
        for page in ['Home', 'Leagues', 'Tournaments', 'Statistics']:
            app.sidebar.radio[0].set_value(page).run()
            self.assertFalse(app.exception)
            self.assertFalse(any(x.label == 'Leaderboard view' for x in app.selectbox))
            self.assertFalse(any(x.value in ['Course overview', 'Layout overview'] for x in app.subheader))
            self.assertEqual(len(app.get('arrow_vega_lite_chart')), 0)  # One event cannot define a time trend.
            for element in list(app.dataframe) + list(app.table):
                self.assertTrue({'Course', 'Ace %', 'Albatross or better %'}.isdisjoint(element.value.columns))
        app.sidebar.radio[0].set_value('Leagues').run()
        leaderboard = next(x for x in app.dataframe if 'Player' in x.value)
        self.assertEqual(leaderboard.value['Player'].tolist(), ['Alice Player', 'Bob Player'])
        self.assertIn('background-color', leaderboard.proto.styler.styles)
        self.assertEqual(leaderboard.value['+/− par'].tolist(), [-2, 0])
        app.session_state['admin_expires'] = time.time() + 100
        app.sidebar.radio[0].set_value('Admin').run()
        app.radio(key='admin_section').set_value('Courses & layouts').run()
        self.assertFalse(app.exception)
        holes = next(x.value for x in app.dataframe if 'Average throws' in x.value)
        self.assertTrue({'Course', 'Ace %', 'Albatross or better %'}.isdisjoint(holes.columns))
        self.assertIn('Birdie %', holes.columns)
        self.assertIn('Par %', holes.columns)
        self.assertEqual(len(app.get('arrow_vega_lite_chart')), 0)
        self.assertEqual(self.path.read_bytes(), original)

    def test_home_links_select_the_clicked_record(self):
        data = fixture()
        data['tournaments'].append(dict(data['tournaments'][0], id='t2', name='Second tournament', date='2026-10-09'))
        data['leagues'].append(dict(data['leagues'][0], id='lg2', name='Second league'))
        self.path.write_bytes(encoded(data))
        app = english_app().run(timeout=20)
        app.button(key='home_tournament_t2').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.sidebar.radio[0].value, 'Tournaments')
        self.assertEqual(app.selectbox(key='tournament_select').value, 't2')
        app.sidebar.radio[0].set_value('Home').run()
        app.button(key='home_league_lg2').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.sidebar.radio[0].value, 'Leagues')
        self.assertEqual(app.selectbox(key='league_select').value, 'lg2')

    def test_hole_count_creation_and_junior_override(self):
        app = self.administrator('Courses & layouts')
        app.number_input(key='hole_count_new_c_default').set_value(12).run()
        next(x for x in app.text_input if x.label == 'Layout name').set_value('Short layout')
        app.button(key='FormSubmitter:layout_new_c_default-Save hole configuration').click().run()
        self.assertFalse(app.exception)
        data = Store(self.path).load()[0]
        layout = next(x for x in data['layouts'] if x['name'] == 'Short layout')
        self.assertEqual(len(layout['profiles']['default']), 12)
        app.selectbox(key='layout_select_c').set_value(layout['id']).run()
        app.selectbox(key='profile_' + layout['id']).set_value('MJ15').run()
        app.number_input(key='hole_count_' + layout['id'] + '_MJ15').set_value(6).run()
        app.button(key='FormSubmitter:layout_' + layout['id'] + '_MJ15-Save hole configuration').click().run()
        self.assertFalse(app.exception)
        layout = next(x for x in Store(self.path).load()[0]['layouts'] if x['id'] == layout['id'])
        self.assertEqual(len(layout['profiles']['MJ15']), 6)
        self.assertEqual(len(layout['profiles']['default']), 12)

    def test_new_junior_configuration_preserves_default_count(self):
        app = self.administrator('Courses & layouts')
        app.selectbox(key='profile_new_c').set_value('MJ15').run()
        app.number_input(key='hole_count_new_c_MJ15').set_value(6).run()
        next(x for x in app.text_input if x.label == 'Layout name').set_value('Junior tees')
        app.button(key='FormSubmitter:layout_new_c_MJ15-Save hole configuration').click().run()
        self.assertFalse(app.exception)
        layout = next(x for x in Store(self.path).load()[0]['layouts'] if x['name'] == 'Junior tees')
        self.assertEqual(len(layout['profiles']['default']), 18)
        self.assertEqual(len(layout['profiles']['MJ15']), 6)

    def test_league_forms_have_no_metric_setting_and_view_is_read_only(self):
        app = self.administrator('Leagues')
        self.assertFalse(any(x.label == 'Leaderboard view' for x in app.selectbox))
        app.sidebar.radio[0].set_value('Leagues').run()
        original = self.path.read_bytes()
        self.assertFalse(any(x.label == 'Leaderboard view' for x in app.selectbox))
        self.assertFalse(app.exception)
        self.assertEqual(self.path.read_bytes(), original)

    def test_category_row_tints(self):
        data = fixture()
        add_round(data, 't', 'a', 1, 'MPO', 0, total=7)
        add_round(data, 't', 'j', 1, 'MJ15', 0, total=3)
        self.path.write_bytes(encoded(data))
        app = english_app().run(timeout=20)
        app.sidebar.radio[0].set_value('Tournaments').run()
        self.assertFalse(app.exception)
        self.assertIn('background-color', app.table[0].proto.styler.styles)
        self.assertIn('#82B99D', app.table[0].proto.styler.styles)
        self.assertIn('#E0C27A', app.table[0].proto.styler.styles)

    def test_category_standings_and_exclusive_tournament_statistics(self):
        data = fixture()
        add_round(data, 't', 'a', 1, 'MPO', 1, {1: 3, 2: 4})
        add_round(data, 't', 'j', 1, 'MJ15', 0, {1: 2})
        self.path.write_bytes(encoded(data))
        app = english_app().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertIn('SWAM Jahodna liga', app.title[1].value)
        standings = [x.value for x in app.table if 'Total points' in x.value]
        self.assertEqual(len(standings), 2)
        for frame in standings:
            self.assertEqual(list(frame.columns), [r'\#', 'Name', 'Total points', 'Tournaments attended', 'Current HCP'])
            self.assertTrue(frame.iloc[0]['Name'].startswith('🥇'))
        app.sidebar.radio[0].set_value('Tournaments').run()
        selector = app.selectbox(key='tournament_stats_category_t')
        self.assertIn('All', selector.options)
        selector.set_value('MJ15').run()
        self.assertEqual(app.selectbox(key='tournament_cat').value, 'All')
        holes = next(x.value for x in app.dataframe if 'Average throws' in x.value and 'Hole' in x.value)
        self.assertEqual(set(holes['Category']), {'MJ15'})
        self.assertEqual(len(holes), 1)
        app.sidebar.radio[0].set_value('Statistics').run()
        self.assertIn('All', app.selectbox(key='stats_category').options)

    def test_combined_statistics_are_layout_specific_and_localized(self):
        data = fixture()
        add_round(data, 't', 'a', 1, 'MPO', 1, {1: 3, 2: 4})
        add_round(data, 't', 'j', 1, 'MJ15', 0, {1: 2})
        self.path.write_bytes(encoded(data))
        app = english_app().run(timeout=20)
        app.sidebar.radio[0].set_value('Statistics').run()
        self.assertEqual(app.selectbox(key='stats_layout_alltime').options, ['Main'])
        self.assertEqual(app.selectbox(key='stats_category').value, 'All')
        holes = next(x.value for x in app.dataframe if 'Average throws' in x.value)
        self.assertEqual(holes['Hole'].tolist(), [1, 2])
        self.assertEqual(set(holes['Category']), {'All'})
        self.assertEqual(holes['Scores'].tolist(), [2, 1])
        self.assertEqual(holes.iloc[0]['Average throws'], 2.5)
        app.selectbox(key='language').set_value('sk').run()
        self.assertFalse(app.exception)
        self.assertIn('Celkovo', app.selectbox(key='stats_category').options)
        self.assertEqual(set(app.dataframe[0].value['Category']), {'Celkovo'})
        app.selectbox(key='language').set_value('en').run()
        app.sidebar.radio[0].set_value('Tournaments').run()
        holes = next(x.value for x in app.dataframe if 'Average throws' in x.value)
        self.assertEqual(holes['Hole'].tolist(), [1, 2])
        self.assertEqual(set(holes['Category']), {'All'})
        app.session_state['admin_expires'] = time.time() + 100
        app.sidebar.radio[0].set_value('Admin').run()
        app.radio(key='admin_section').set_value('Courses & layouts').run()
        self.assertFalse(app.exception)
        app.selectbox(key='layout_cat_l').set_value('All').run()
        holes = next(x.value for x in app.dataframe if 'Average throws' in x.value)
        self.assertEqual(holes['Hole'].tolist(), [1, 2])
        self.assertEqual(set(holes['Category']), {'All'})

    def test_editable_title_and_single_active_league(self):
        data = fixture()
        data['leagues'].append(dict(data['leagues'][0], id='lg2', name='Next league'))
        self.path.write_bytes(encoded(data))
        app = self.administrator('Settings')
        app.text_input[0].set_value('My local league')
        next(x for x in app.selectbox if x.label == 'Active league').set_value('lg2')
        app.button(key='FormSubmitter:application_settings-Save settings').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(Store(self.path).load()[0]['settings'], {'site_title': 'My local league', 'active_league_id': 'lg2', 'handicap_method': 'legacy'})
        app.sidebar.radio[0].set_value('Home').run()
        self.assertTrue(any(x.value == '🥏 My local league' for x in app.title))
        self.assertFalse(any('Total points' in x.value for x in app.table))


    def test_home_tied_places_skip_occupied_positions(self):
        from league.domain import save_player
        data = fixture()
        save_player(data, 'c', 'Chris', 'Player', 'MPO', 0, 'Chris')
        save_player(data, 'd', 'Dana', 'Player', 'MPO', 0, 'Dana')
        save_player(data, 'e', 'Evan', 'Player', 'MPO', 0, 'Evan')
        for pid, total in [('a', 5), ('b', 6), ('c', 7), ('d', 7), ('e', 8)]:
            add_round(data, 't', pid, 1, 'MPO', 0, total=total)
        self.path.write_bytes(encoded(data))
        app = english_app().run(timeout=20)
        self.assertFalse(app.exception)
        frame = next(x.value for x in app.table if 'Total points' in x.value)
        self.assertEqual(frame[r'\#'].tolist(), ['1', '2', 'T3', 'T3', '5'])
        app.sidebar.radio[0].set_value('Leagues').run()
        self.assertFalse(app.exception)
        self.assertEqual(next(x.value for x in app.dataframe if 'Player' in x.value)['Place'].tolist(), ['1', '2', 'T3', 'T3', '5'])


    def test_slovak_default_switching_and_public_simplification(self):
        import json
        data = fixture()
        add_round(data, 't', 'a', 1, 'MPO', 1, {1: 3, 2: 4})
        self.path.write_bytes(encoded(data))
        original = self.path.read_bytes()
        app = AppTest.from_file(APP).run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key='language').value, 'sk')
        self.assertEqual(app.sidebar.radio[0].options, ['Domov', 'Ligy', 'Turnaje', 'Štatistiky', 'História hendikepu', 'Administrácia'])
        self.assertEqual(len(app.metric), 0)
        self.assertFalse(any(x.label == 'Zobrazenie výsledkov' for x in app.selectbox))
        self.assertIn(r'\#', app.table[0].value.columns)
        self.assertIn('HCP Aktuálne', app.table[0].value.columns)
        self.assertEqual(len(app.get('download_button')), 0)
        self.assertTrue(any('Download as CSV' in m.value and 'display:none' in m.value for m in app.markdown))
        app.session_state['home_metric'] = 'Handicap adjusted'
        app.selectbox(key='language').set_value('en').run()
        self.assertFalse(app.exception)
        self.assertNotIn('home_metric', app.session_state)
        self.assertFalse(any(x.label == 'Leaderboard view' for x in app.selectbox))
        app.selectbox(key='language').set_value('sk').run()
        self.assertFalse(app.exception)
        for page in ['Leagues', 'Tournaments', 'Statistics']:
            app.sidebar.radio[0].set_value(page).run()
            self.assertFalse(app.exception, page)
            self.assertEqual(len(app.get('download_button')), 0)
        self.assertEqual(self.path.read_bytes(), original)

    def test_league_points_table_navigation_and_admin_exports(self):
        data = fixture()
        add_round(data, 't', 'a', 1, 'MPO', 1, {1: 3, 2: 4})
        self.path.write_bytes(encoded(data))
        app = AppTest.from_file(APP).run(timeout=20)
        app.sidebar.radio[0].set_value('Leagues').run()
        self.assertFalse(app.exception)
        points = next(x.value for x in app.table if list(x.value.columns) == ['Poradie', '1', '2', '3'])
        self.assertEqual(points.iloc[0].tolist(), ['Body', 10, 6, 3])
        self.assertTrue(any(x.value == 'Bodovanie podľa umiestnenia' for x in app.caption))
        self.assertFalse(any('Ties share occupied' in c.value or 'Players changing category' in c.value for c in app.caption))
        app.button(key='league_tournament_t').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.sidebar.radio[0].value, 'Tournaments')
        self.assertEqual(app.selectbox(key='tournament_select').value, 't')
        self.assertEqual(len(app.get('download_button')), 0)
        app.session_state['admin_expires'] = time.time() + 100
        app.run()
        self.assertFalse(app.exception)
        self.assertGreater(len(app.get('download_button')), 0)
        self.assertFalse(any('button[aria-label="Download as CSV"]' in m.value and 'display:none' in m.value for m in app.markdown))
        app.session_state['admin_expires'] = 0
        app.run()
        self.assertEqual(len(app.get('download_button')), 0)

    def test_slovak_admin_sections_and_retired_raw_view(self):
        app = AppTest.from_file(APP)
        app.session_state['home_metric'] = 'Raw throws'
        app.run(timeout=20)
        self.assertFalse(app.exception)
        self.assertNotIn('home_metric', app.session_state)
        self.assertFalse(any(x.label == 'Zobrazenie výsledkov' for x in app.selectbox))
        app.session_state['admin_expires'] = time.time() + 100
        app.sidebar.radio[0].set_value('Admin').run()
        for section in ['Players', 'Courses & layouts', 'Leagues', 'Tournaments & scores', 'Categories', 'Settings', 'Backup & restore']:
            app.radio(key='admin_section').set_value(section).run()
            self.assertFalse(app.exception, section)
        app.radio(key='admin_section').set_value('Settings').run()
        self.assertEqual(app.text_input[0].label, 'Názov aplikácie')


    def test_slovak_admin_save_preserves_record_fields(self):
        app = AppTest.from_file(APP).run(timeout=20)
        app.sidebar.radio[0].set_value('Admin').run()
        app.text_input[0].set_value('test-only-password')
        next(b for b in app.button if b.label == 'Prihlásiť sa').click().run()
        self.assertFalse(app.exception)
        next(x for x in app.text_input if x.label == 'Meno').set_value('Ján')
        next(x for x in app.text_input if x.label == 'Priezvisko').set_value('Novák')
        next(x for x in app.text_input if x.label == 'Používateľské meno uDisc').set_value('jan-udisc')
        next(b for b in app.button if b.label == 'Uložiť hráča').click().run()
        self.assertFalse(app.exception)
        player = next(p for p in Store(self.path).load()[0]['players'] if p['udisc'] == 'jan-udisc')
        self.assertEqual((player['first_name'], player['last_name'], player['category']), ('Ján', 'Novák', 'MPO'))
