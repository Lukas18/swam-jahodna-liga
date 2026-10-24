import unittest
from copy import deepcopy
from test_dual_handicaps import golf_fixture
from league.handicaps import recalculate_handicaps, project_handicaps
from league.relational import to_records, from_records
from league.stableford import (strokes_received, hole_points, league_standings,
                               tournament_standings, hole_identity, difficulty_rows, stablefords_current)


def fixture(scores):
    data = golf_fixture(scores)
    data['leagues'][0]['name'] = 'Jesenna SWAM Liga'
    return data


class StablefordTests(unittest.TestCase):
    def test_rare_percentages_keep_two_decimals_and_numeric_values(self):
        from league.presentation import percentage_value, percentage_label
        raw = [0, 0.004, 0.2378, 0.5, 0.999, 1, 1.6, 25]
        self.assertEqual([percentage_label(percentage_value(v)) for v in raw],
                         ['0', '0.00', '0.24', '0.50', '1.00', '1', '2', '25'])

    def test_golf_points_and_full_handicap_allocation(self):
        self.assertEqual([hole_points(n, 4, 0) for n in [1,2,3,4,5,6,8]], [5,4,3,2,1,0,0])
        self.assertEqual(hole_points(1,5,0),6)
        for handicap in [-40,-19,-18,-7,-1,0,1,7,18,19,40]:
            allocation=[strokes_received(handicap,n) for n in range(1,19)]
            self.assertEqual(sum(allocation),handicap)
            self.assertLessEqual(max(allocation)-min(allocation),1)
        self.assertEqual([strokes_received(2,n) for n in [1,2,3,18]],[1,1,0,0])
        self.assertEqual([strokes_received(-2,n) for n in [1,16,17,18]],[0,0,-1,-1])

    def test_historical_handicaps_and_reversible_method_switch(self):
        before=fixture([1,2,3,10]);saved=recalculate_handicaps(before)
        self.assertEqual(saved,recalculate_handicaps(saved))
        self.assertEqual(from_records(to_records(saved),saved['revision']),saved)
        self.assertEqual(saved['stableford_results'][-1]['methods']['golf']['rounds'][0]['handicap'],-1)
        self.assertEqual(saved['stableford_results'][-1]['methods']['legacy']['rounds'][0]['handicap'],2)
        for old,new in zip(before['rounds'],saved['rounds']):
            self.assertEqual(old['holes'],new['holes'])
        saved['settings']['handicap_method']='golf';view=project_handicaps(saved)
        row=view['stableford_results'][-1]
        self.assertEqual(row['points'],row['methods']['golf']['points'])
        self.assertEqual(recalculate_handicaps(view)['stableford_results'][-1]['points'],row['methods']['legacy']['points'])

    def test_difficulty_frozen_until_explicit_reset_and_shared_across_numbers(self):
        data=fixture([5,8])
        data['layouts'][0]['profiles']['default'][-1]['length']=20
        for r in data['rounds']:
            r['holes'][-1]['length']=20
        out=recalculate_handicaps(data)
        snapshot=deepcopy(out['tournaments'][0]['stableford_difficulty'])
        layout=out['layouts'][0];h=layout['profiles']['default'][0]
        self.assertEqual(hole_identity(layout,h),hole_identity({**layout,'id':'other'},{**h,'number':99}))
        easiest=hole_identity(layout,layout['profiles']['default'][-1])
        for row in out['courses'][0]['stableford_difficulty']['rows']:
            row['priority']=1 if row['id']==easiest else 2
        again=recalculate_handicaps(out)
        self.assertEqual(again['tournaments'][0]['stableford_difficulty'],snapshot)
        again['tournaments'][0].pop('stableford_difficulty')
        reset=recalculate_handicaps(again)
        reset_holes=next(iter(reset['tournaments'][0]['stableford_difficulty'].values()))['holes']
        self.assertEqual(next(h['stroke_index'] for h in reset_holes if h['number']==18),1)
        self.assertEqual(len(next(iter(snapshot.values()))['holes']),18)
        self.assertEqual({r['stroke_index'] for r in next(iter(snapshot.values()))['holes']},set(range(1,19)))

    def test_disabled_leagues_and_incomplete_or_totals_only_results(self):
        data=golf_fixture([1,2])
        data['leagues'][0]['stableford_enabled']=False
        other=recalculate_handicaps(data)
        self.assertTrue(all(r['status']=='pending_formula' for r in other['stableford_results']))
        data=fixture([1,2]);data['rounds'][0]['holes']=[]
        data['tournaments'][1]['num_rounds']=2
        out=recalculate_handicaps(data)
        self.assertTrue(all(r['status']=='pending_inputs' and r['points'] is None for r in out['stableford_results']))
        self.assertEqual(tournament_standings(out,'0'),[])

    def test_backfill_earlier_leagues_preserves_existing_results_and_snapshots(self):
        from backfill_stableford import verify_preserved
        data=golf_fixture([1,2,3,10])
        data['leagues'].append({**data['leagues'][0], 'id':'fall', 'name':'Jesenna SWAM Liga'})
        data['leagues'][0]['stableford_enabled']=False
        data['tournaments'][-1]['league_id']='fall'
        before=recalculate_handicaps(data)
        # Model the previous application: older leagues had no opt-out flag,
        # and a current formula marker despite pending historical results.
        before['leagues'][0].pop('stableford_enabled')
        self.assertFalse(stablefords_current(before))
        after=recalculate_handicaps(before)
        verify_preserved(before,after)
        self.assertTrue(stablefords_current(after))
        self.assertTrue(all(r['status']=='calculated' for r in after['stableford_results']))
        self.assertEqual(before['stableford_results'][-1],after['stableford_results'][-1])
        self.assertEqual(before['tournaments'][-1],after['tournaments'][-1])
        self.assertEqual(after,recalculate_handicaps(after))
        self.assertEqual(after,from_records(to_records(after),after['revision']))
        broken=deepcopy(after);broken['rounds'][0]['total']+=1
        with self.assertRaises(ValueError): verify_preserved(before,broken)
        broken=deepcopy(after);broken['stableford_results'][-1]['points']+=1
        with self.assertRaises(ValueError): verify_preserved(before,broken)

    def test_tied_stableford_places_and_existing_league_points(self):
        data=fixture([0]);data=recalculate_handicaps(data)
        for pid in ['q','r']:
            data['players'].append({**data['players'][0],'id':pid,'first_name':pid})
            data['registrations'].append({**data['registrations'][0],'player_id':pid})
            data['stableford_results'].append({**data['stableford_results'][0],'player_id':pid})
        data['stableford_results'][0]['points']=40
        data['stableford_results'][1]['points']=40
        data['stableford_results'][2]['points']=39
        rows=tournament_standings(data,'0')
        self.assertEqual([r['Place'] for r in rows],[1,1,3])
        standings=league_standings(data,'lg')
        self.assertEqual([r['Points'] for r in standings],[9,9,0])
        self.assertEqual([r['Place'] for r in standings],[1,1,3])

    def test_league_stableford_total_uses_only_its_tournaments(self):
        data=fixture([1,2,3])
        data['leagues'].append({**data['leagues'][0],'id':'other','name':'Other league'})
        data['tournaments'][2]['league_id']='other'
        data=recalculate_handicaps(data)
        expected=sum(tournament_standings(data,tid)[0]['Stableford'] for tid in ('0','1'))
        self.assertEqual(league_standings(data,'lg')[0]['Stableford'],expected)
        self.assertEqual(league_standings(data,'other')[0]['Stableford'],
                         tournament_standings(data,'2')[0]['Stableford'])
