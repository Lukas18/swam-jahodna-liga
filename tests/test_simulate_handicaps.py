"""Simulation calculations are isolated from league state and database writes."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
import unittest
from simulate_handicaps import simulate, selection_rule


def fixture(records):
    data = {'players': [], 'tournaments': [], 'rounds': []}
    for pid, scores in records.items():
        data['players'].append({'id': pid, 'first_name': pid, 'last_name': 'Player',
                                'category': 'MPO', 'handicap': 0})
        for i, score in enumerate(scores):
            tid = f'{pid}-{i}'
            data['tournaments'].append({'id': tid, 'name': tid,
                'date': (date(2025, 1, 1) + timedelta(days=i)).isoformat(), 'num_rounds': 1})
            holes = [{'number': n, 'par': 3, 'throws': 3} for n in range(1, 19)]
            if score >= 0:
                holes[0]['throws'] += score
            else:
                for n in range(-score):
                    holes[n % 18]['throws'] -= 1
            data['rounds'].append({'player_id': pid, 'tournament_id': tid,
                'round_number': 1, 'layout_id': 'red', 'category': 'MPO',
                'holes': holes, 'total': 54 + score, 'par': 54})
    return data


class HandicapSimulationTests(unittest.TestCase):
    def test_score_selection_boundaries(self):
        expected = {2:(0,0), 3:(1,-2), 4:(1,-1), 5:(1,0), 6:(2,-1),
            7:(2,0), 8:(2,0), 9:(3,0), 11:(3,0), 12:(4,0), 14:(4,0),
            15:(5,0), 16:(5,0), 17:(6,0), 18:(6,0), 19:(7,0), 20:(8,0), 21:(8,0)}
        for count, rule in expected.items():
            self.assertEqual(selection_rule(count), rule, count)

    def test_best_eight_only_from_latest_twenty_and_no_state_mutation(self):
        data = fixture({'one': [-20] + list(range(1,21))})
        before = deepcopy(data)
        row = simulate(data)[0]
        self.assertEqual(row['tournaments'], 21)
        self.assertEqual([r['differential'] for r in row['selected']], list(range(1,9)))
        self.assertEqual(row['decimal_estimate'], Decimal('4.5'))
        self.assertEqual(row['integer_estimate'], 5)
        self.assertNotIn('current_hcp', row)
        self.assertEqual(data, before)

    def test_top_players_include_attendance_ties_only(self):
        data = fixture({'one':[5]*21, 'two':[5]*19, 'three':[5]*19, 'four':[5]*5})
        rows = simulate(data, 2)
        self.assertEqual({r['player_id'] for r in rows}, {'one','two','three'})
        self.assertEqual([r['used_count'] for r in rows], [8,7,7])

    def test_small_record_adjustment_and_signed_ceiling(self):
        row = simulate(fixture({'one':[5,6,7]}))[0]
        self.assertEqual(row['decimal_estimate'], Decimal('3.0'))
        scores = [-4,-3,-3,-2,-2,-2,-2,-2] + [5]*12
        row = simulate(fixture({'one':scores}))[0]
        self.assertEqual(row['decimal_estimate'], Decimal('-2.5'))
        self.assertEqual(row['integer_estimate'], -2)
        row = simulate(fixture({'one':[5,6]}))[0]
        self.assertIsNone(row['raw_estimate'])

    def test_incomplete_tournament_is_excluded_and_holes_are_validated(self):
        data = fixture({'one':[5,6,7,99]})
        data['tournaments'][-1]['num_rounds'] = 2
        self.assertEqual(simulate(data)[0]['tournaments'], 3)
        data['rounds'][0]['holes'].pop()
        with self.assertRaisesRegex(ValueError, '18-hole'):
            simulate(data)
