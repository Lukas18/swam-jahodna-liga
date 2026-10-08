import unittest
from copy import deepcopy
from test_league import fixture
from league.domain import add_round
from league.statistics import selected_rounds, summary, round_overview, hole_statistics


class StatisticsTest(unittest.TestCase):
    def test_combined_holes_weight_samples_and_use_recorded_category_par(self):
        d = fixture()
        d['tournaments'][0]['categories'].append('FPO')
        from league.domain import save_player
        save_player(d, 'f', 'FPO', 'Player', 'FPO', 0, 'fpo')
        d['layouts'][0]['profiles']['FPO'] = [{'number': 1, 'par': 4, 'length': 100}, {'number': 2, 'par': 5, 'length': 130}]
        add_round(d, 't', 'a', 1, 'MPO', 0, {1: 3, 2: 4})
        add_round(d, 't', 'b', 1, 'MPO', 0, {1: 3, 2: 4})
        add_round(d, 't', 'f', 1, 'FPO', 0, {1: 3, 2: 4})
        rows = hole_statistics(d, d['rounds'], combine_categories=True)
        self.assertEqual(len(rows), 2)
        self.assertEqual({r['Category'] for r in rows}, {'All'})
        self.assertEqual(rows[0]['Scores'], 3)
        self.assertEqual(rows[0]['Average throws'], 3)
        self.assertAlmostEqual(rows[0]['Average +/− par'], -1/3)
        self.assertAlmostEqual(rows[0]['Par'], 10/3)
        self.assertAlmostEqual(rows[0]['Birdie %'], 100/3)
        self.assertAlmostEqual(rows[0]['Par %'], 200/3)
        d['rounds'][0]['holes'][0]['length'] = 0  # Unknown length must not lower the combined distance.
        self.assertEqual(hole_statistics(d, d['rounds'], combine_categories=True)[0]['Length (m)'], 95)
        # Historical pars also combine to one row, and another layout remains separate.
        d['tournaments'].append(dict(d['tournaments'][0], id='t2'))
        d['layouts'][0]['profiles']['default'][0]['par'] = 5
        add_round(d, 't2', 'a', 1, 'MPO', 0, {1: 5, 2: 4})
        rows = hole_statistics(d, d['rounds'], combine_categories=True)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['Scores'], 4)
        second = deepcopy(d['layouts'][0]);second['id']='second'
        d['layouts'].append(second)
        d['tournaments'].append(dict(d['tournaments'][0], id='t3', layout_id='second'))
        add_round(d, 't3', 'a', 1, 'MPO', 0, {1: 5, 2: 4})
        self.assertEqual(len(hole_statistics(d, d['rounds'], combine_categories=True)), 4)
        scoped = selected_rounds(d, layout_id='l')
        self.assertEqual(len(hole_statistics(d, scoped, combine_categories=True)), 2)

    def test_scope_denominators_and_layout_isolation(self):
        d = fixture()
        add_round(d, 't', 'a', 1, 'MPO', 1, {1: 1, 2: 4})
        d['tournaments'].append(dict(d['tournaments'][0], id='t2'))
        add_round(d, 't2', 'b', 1, 'MPO', 0, {1: 3, 2: 5})
        add_round(d, 't2', 'j', 1, 'MJ15', 0, {1: 2})
        d['courses'].append({'id': 'c2', 'name': 'Other course', 'description': ''})
        layout = deepcopy(d['layouts'][0])
        layout.update(id='l2', course_id='c2', name='Other layout')
        d['layouts'].append(layout)
        d['tournaments'].append(dict(d['tournaments'][0], id='t3', layout_id='l2'))
        add_round(d, 't3', 'a', 1, 'MPO', 1, {1: 5, 2: 5})
        rows = selected_rounds(d, layout_id='l', category='MPO')
        h = hole_statistics(d, rows)[0]
        self.assertEqual(h['Average throws'], 2)
        self.assertEqual(h['Scores'], 2)
        self.assertEqual(h['Ace %'], 50)
        self.assertEqual(h['Par %'], 50)
        self.assertEqual(sum(h[c] for c in h if c.endswith(' %')), 100)
        self.assertEqual(len(selected_rounds(d, tournament_id='t')), 1)
        self.assertEqual(len(selected_rounds(d, course_id='c')), 3)
        self.assertEqual(len(round_overview(d, d['rounds'], 'layout')), 3)
        self.assertEqual(summary(d['rounds'])['Hole scores'], 7)
        self.assertEqual(summary(d['rounds'])['Tournaments'], 3)
        self.assertEqual(len(hole_statistics(d, d['rounds'])), 5)

    def test_totals_only_empty_and_historical_tees(self):
        d = fixture()
        add_round(d, 't', 'a', 1, 'MPO', 1, {1: 2, 2: 4})
        d['tournaments'].append(dict(d['tournaments'][0], id='t2'))
        d['layouts'][0]['profiles']['default'][0]['par'] = 4
        add_round(d, 't2', 'b', 1, 'MPO', 0, {1: 3, 2: 4})
        add_round(d, 't2', 'j', 1, 'MJ15', 0, total=3)
        self.assertEqual(len(hole_statistics(d, d['rounds'])), 3)
        self.assertEqual(summary(d['rounds'])['Recorded rounds'], 3)
        self.assertEqual(summary(d['rounds'])['Hole scores'], 4)
        self.assertIsNone(summary([])['Average throws'])
        self.assertEqual(hole_statistics(d, []), [])

    def test_heat_map_neutral_zone_and_three_steps(self):
        from league.statistics import hole_heat_styles
        for deviation in [-0.25, 0, 0.25]:
            row = {'Average throws': 3 + deviation, 'Average +/− par': deviation, 'Par %': 100, 'Bogey %': 0}
            self.assertEqual(hole_heat_styles(row), ['', '', '', ''])
        for deviation, alpha in [(0.5, '#EDD2B9'), (1, '#DFAD82'), (2, '#CA855D')]:
            self.assertIn(alpha, hole_heat_styles({'Average +/− par': deviation})[0])
            self.assertIn('color: #17251F', hole_heat_styles({'Average +/− par': -deviation})[0])
        row = {'Average +/− par': 0, 'Birdie %': 25, 'Bogey %': 50, 'Ace %': 75, 'Par %': 10}
        styles = hole_heat_styles(row)
        self.assertIn('#B6DFCD', styles[1])
        self.assertIn('#DFAD82', styles[2])
        self.assertIn('#48A680', styles[3])
        self.assertEqual(styles[4], '')

    def test_home_attendance_incomplete_events_and_league_isolation(self):
        from league.domain import home_standings, site_settings, validate_data
        d = fixture()
        add_round(d, 't', 'a', 1, 'MPO', 1, {1: 3, 2: 4})
        d['tournaments'].append(dict(d['tournaments'][0], id='t2', num_rounds=2))
        add_round(d, 't2', 'a', 1, 'MPO', 1, {1: 3, 2: 4})
        add_round(d, 't2', 'b', 1, 'MPO', 0, {1: 3, 2: 4})
        rows = home_standings(d, 'lg')
        self.assertEqual([(r['Points'], r['Tournaments']) for r in rows], [(10, 2), (0, 1)])
        d['leagues'].append(dict(d['leagues'][0], id='other'))
        self.assertEqual(home_standings(d, 'other'), [])
        del d['settings']
        self.assertEqual(site_settings(d)['site_title'], 'SWAM Jahodna liga')
        self.assertEqual(site_settings(d)['active_league_id'], 'lg')
        validate_data(d)
        d['settings'] = {'site_title': '', 'active_league_id': 'lg'}
        with self.assertRaises(ValueError):
            validate_data(d)
        d['settings'] = {'site_title': 'Title', 'active_league_id': 'missing'}
        with self.assertRaises(ValueError):
            validate_data(d)
