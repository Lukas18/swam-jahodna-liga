import unittest
from copy import deepcopy
from decimal import Decimal

from test_handicaps import fixture
from league.handicaps import recalculate_handicaps
from league.relational import to_records, from_records
from league.domain import validate_data


def golf_fixture(scores):
    data = fixture([0] * len(scores))
    holes = [{'number': n, 'par': 3, 'length': 10} for n in range(1, 19)]
    data['layouts'][0]['profiles']['default'] = holes
    for r, score in zip(data['rounds'], scores):
        r['holes'] = [{**h, 'throws': 3} for h in holes]
        for i in range(abs(score)):
            r['holes'][i % 18]['throws'] += 1 if score > 0 else -1
        r['par'] = 54
        r['total'] = 54 + score
    return data


class GolfHandicapTests(unittest.TestCase):
    def test_single_history_matches_simulation_and_round_trips(self):
        out = recalculate_handicaps(golf_fixture([-4,-3,-3,-2,-2,-2,-2,-2] + [5] * 12))
        self.assertEqual(out['players'][0]['handicap'], -2)
        self.assertEqual(out['handicap_history'][-1]['index'], '-2.5')
        self.assertEqual(out, recalculate_handicaps(out))
        self.assertEqual(from_records(to_records(out), out['revision']), out)
        payload = to_records(out)
        self.assertEqual(len(payload['handicap_runs']), 1)
        self.assertEqual(len(payload['handicap_history']), 20)
        self.assertNotIn('golf_handicap_history', out)
        self.assertNotIn('methods', out['stableford_results'][-1])
        validate_data(out)

    def test_initial_handicap_is_provisional_until_three_rounds(self):
        data = golf_fixture([1,2,3,10])
        data['players'][0]['handicap'] = -4
        out = recalculate_handicaps(data)
        h = out['handicap_history']
        self.assertEqual([r['provisional'] for r in h], [True,True,False,False])
        self.assertEqual([r['handicap_after'] for r in h], [-4,-4,-1,0])
        self.assertEqual([r['handicap_used'] for r in h], [-4,-4,-4,-1])
        self.assertEqual([r['used_provisional'] for r in h], [True,True,True,False])
        self.assertEqual(h[2]['selection_count'], 1)
        self.assertEqual(out['rounds'][2]['handicap'], -4)
        self.assertEqual(out['players'][0]['original_handicap'], -4)

    def test_short_and_incomplete_events_do_not_supply_scores(self):
        data = golf_fixture([1,2,3])
        data['rounds'][0]['holes'] = data['rounds'][0]['holes'][:9]
        data['rounds'][0]['total'] = sum(h['throws'] for h in data['rounds'][0]['holes'])
        data['rounds'][0]['par'] = 27
        out = recalculate_handicaps(data)
        self.assertTrue(out['players'][0]['handicap_provisional'])
        self.assertEqual(out['handicap_history'][-1]['window_count'], 2)
        data = golf_fixture([1,2,3])
        data['tournaments'][-1]['num_rounds'] = 2
        out = recalculate_handicaps(data)
        self.assertEqual(len(out['handicap_history']), 2)

    def test_backdated_correction_rebuilds_history(self):
        data = golf_fixture([1,2,3,10])
        old = recalculate_handicaps(data)
        data['rounds'][0]['holes'][0]['throws'] += 5
        data['rounds'][0]['total'] += 5
        new = recalculate_handicaps(data)
        self.assertNotEqual(old['handicap_run']['id'], new['handicap_run']['id'])
        self.assertNotEqual(old['handicap_history'][2]['handicap_after'], new['handicap_history'][2]['handicap_after'])

    def test_offline_simulation_and_multi_round_sources(self):
        from simulate_handicaps import simulate
        for count in [3,4,5,6,8,11,14,16,18,19,20,21]:
            out = recalculate_handicaps(golf_fixture([(i * 7) % 15 - 3 for i in range(count)]))
            expected = simulate(out)[0]
            self.assertEqual(out['players'][0]['handicap'], expected['integer_estimate'])
            self.assertEqual(Decimal(out['handicap_history'][-1]['raw_index']), expected['raw_estimate'])
        data = golf_fixture(list(range(20)))
        data['tournaments'] = data['tournaments'][:1]
        data['tournaments'][0]['num_rounds'] = 20
        data['registrations'] = data['registrations'][:1]
        for i, r in enumerate(data['rounds'], 1):
            r['tournament_id'] = '0'
            r['round_number'] = i
        out = recalculate_handicaps(data)
        self.assertEqual(out['handicap_history'][0]['selection_count'], 8)
        self.assertEqual(len(out['handicap_history'][0]['sources']), 1)
        self.assertEqual(from_records(to_records(out), out['revision']), out)

    def test_old_parallel_rows_load_as_one_golf_history(self):
        current = recalculate_handicaps(golf_fixture([1,2,3]))
        payload = to_records(current)
        golf_run = payload['handicap_runs'][0]
        golf_run['algorithm'] = 'relative-par-best-of-20-ceiling-v1'
        legacy_run = deepcopy(golf_run)
        legacy_run.update(id='legacy-run', algorithm='relative-par-last-10-ceiling-v1')
        payload['handicap_runs'].append(legacy_run)
        legacy_snapshot = deepcopy(payload['handicap_history'][0])
        legacy_snapshot.update(id='legacy-snapshot', run_id='legacy-run')
        payload['handicap_history'].append(legacy_snapshot)
        loaded = from_records(payload, current['revision'])
        self.assertEqual(len(loaded['handicap_history']), 3)
        self.assertEqual(loaded['handicap_run']['algorithm'], 'relative-par-best-of-20-ceiling-v1')
        loaded['settings']['handicap_method'] = 'legacy'
        loaded['players'][0]['golf_handicap'] = loaded['players'][0]['handicap']
        loaded['stableford_results'][0]['methods'] = {'legacy': {}, 'golf': {}}
        rebuilt = recalculate_handicaps(loaded)
        self.assertEqual(len(to_records(rebuilt)['handicap_runs']), 1)
        self.assertEqual(len(to_records(rebuilt)['handicap_history']), 3)
        self.assertNotIn('handicap_method', rebuilt['settings'])
        self.assertNotIn('golf_handicap', rebuilt['players'][0])
        self.assertNotIn('methods', rebuilt['stableford_results'][0])
