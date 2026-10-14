import unittest
from copy import deepcopy
from decimal import Decimal
from test_handicaps import fixture
from league.handicaps import recalculate_handicaps, project_handicaps
from league.relational import to_records, from_records
from league.domain import validate_data


def golf_fixture(scores):
    data = fixture([0]*len(scores))
    holes = [{'number':n,'par':3,'length':10} for n in range(1,19)]
    data['layouts'][0]['profiles']['default'] = holes
    for r,score in zip(data['rounds'],scores):
        r['holes'] = [{**h,'throws':3} for h in holes]
        for i in range(abs(score)):
            r['holes'][i%18]['throws'] += 1 if score > 0 else -1
        r['par']=54;r['total']=54+score
    return data


class DualHandicapTests(unittest.TestCase):
    def test_parallel_history_matches_simulation_and_preserves_legacy(self):
        data = golf_fixture([-4,-3,-3,-2,-2,-2,-2,-2]+[5]*12)
        out = recalculate_handicaps(data)
        self.assertEqual(out['players'][0]['handicap'],5)
        self.assertEqual(out['players'][0]['golf_handicap'],-2)
        self.assertEqual(out['golf_handicap_history'][-1]['index'],'-2.5')
        self.assertEqual(out,recalculate_handicaps(out))
        self.assertEqual(from_records(to_records(out),out['revision']),out)
        payload=to_records(out)
        self.assertEqual(len(payload['handicap_runs']),2)
        self.assertEqual(len(payload['handicap_history']),40)
        self.assertNotIn('golf_handicap_history',payload['root']['extra'])
        validate_data(out)

    def test_provisional_debut_and_no_lookahead(self):
        out = recalculate_handicaps(golf_fixture([1,2,3,10]))
        h=out['golf_handicap_history']
        self.assertEqual([r['provisional'] for r in h],[True,True,False,False])
        self.assertEqual([r['handicap_after'] for r in h],[1,2,-1,0])
        self.assertEqual([r['handicap_used'] for r in h],[1,1,2,-1])
        self.assertEqual([r['used_provisional'] for r in h],[True,True,True,False])
        self.assertEqual(h[2]['selection_count'],1)

    def test_switch_is_reversible_and_persisted_fields_remain_legacy(self):
        stored=recalculate_handicaps(golf_fixture([1,2,3,10]))
        before=deepcopy(stored)
        stored['settings']['handicap_method']='golf'
        view=project_handicaps(stored)
        self.assertEqual(view['players'][0]['handicap'],0)
        self.assertEqual(view['rounds'][-1]['handicap'],-1)
        validate_data(view)
        saved=recalculate_handicaps(view)
        for collection in ['players','registrations','rounds']:
            self.assertEqual([r['handicap'] for r in saved[collection]],
                             [r['handicap'] for r in before[collection]])
        self.assertEqual(saved['handicap_history'],before['handicap_history'])
        saved['settings']['handicap_method']='legacy'
        self.assertEqual(project_handicaps(saved)['players'][0]['handicap'],4)
        self.assertEqual(saved['golf_handicap_history'],before['golf_handicap_history'])

    def test_short_and_incomplete_events_do_not_supply_golf_scores(self):
        data=golf_fixture([1,2,3])
        data['rounds'][0]['holes']=data['rounds'][0]['holes'][:9]
        data['rounds'][0]['total']=sum(h['throws'] for h in data['rounds'][0]['holes'])
        data['rounds'][0]['par']=27
        out=recalculate_handicaps(data)
        self.assertTrue(out['players'][0]['golf_provisional'])
        self.assertEqual(out['golf_handicap_history'][-1]['window_count'],2)
        data=golf_fixture([1,2,3]);data['tournaments'][-1]['num_rounds']=2
        out=recalculate_handicaps(data)
        self.assertEqual(len(out['golf_handicap_history']),2)

    def test_backdated_correction_rebuilds_both_histories(self):
        data=golf_fixture([1,2,3,10]);old=recalculate_handicaps(data)
        data['rounds'][0]['holes'][0]['throws']+=5;data['rounds'][0]['total']+=5
        new=recalculate_handicaps(data)
        self.assertNotEqual(old['golf_handicap_run']['id'],new['golf_handicap_run']['id'])
        self.assertNotEqual(old['golf_handicap_history'][2]['handicap_after'],new['golf_handicap_history'][2]['handicap_after'])

    def test_golf_matches_offline_simulation_and_multi_round_sources(self):
        from simulate_handicaps import simulate
        for count in [3,4,5,6,8,11,14,16,18,19,20,21]:
            data=golf_fixture([(i*7)%15-3 for i in range(count)])
            out=recalculate_handicaps(data)
            expected=simulate(out)[0]
            self.assertEqual(out['players'][0]['golf_handicap'],expected['integer_estimate'])
            self.assertEqual(Decimal(out['golf_handicap_history'][-1]['raw_index']),expected['raw_estimate'])
        data=golf_fixture(list(range(20)))
        data['tournaments']=data['tournaments'][:1];data['tournaments'][0]['num_rounds']=20
        data['registrations']=data['registrations'][:1]
        for i,r in enumerate(data['rounds'],1):r['tournament_id']='0';r['round_number']=i
        out=recalculate_handicaps(data)
        self.assertEqual(out['golf_handicap_history'][0]['selection_count'],8)
        self.assertEqual(len(out['golf_handicap_history'][0]['sources']),1)
        self.assertEqual(from_records(to_records(out),out['revision']),out)
        validate_data(out)

    def test_backfill_rejects_any_legacy_value_or_score_change(self):
        from backfill_handicaps import verify_legacy
        before=recalculate_handicaps(golf_fixture([1,2,3]))
        for collection,field in [('players','handicap'),('rounds','total'),('handicap_history','handicap_after')]:
            changed=deepcopy(before);changed[collection][0][field]+=1
            with self.assertRaises(ValueError):verify_legacy(before,changed)
