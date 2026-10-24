import unittest
from copy import deepcopy
from datetime import date,timedelta
from league.domain import empty_data,save_player,add_round,validate_data
from league.handicaps import recalculate_handicaps,ceil_handicap
from league.relational import to_records,from_records


def fixture(scores):
 d=empty_data();d['courses']=[{'id':'c','name':'Jahodna','description':''}]
 d['layouts']=[{'id':'l','course_id':'c','name':'Cervena','profiles':{'default':[{'number':1,'par':3,'length':10}]}}]
 d['leagues']=[{'id':'lg','name':'League','points':[10,8],'points_scope':'category','tie_mode':'shared'}]
 save_player(d,'p','One','Player','MPO',99,'user')
 for i,score in enumerate(scores):
  t={'id':str(i),'name':f'Event {i}','date':(date(2025,1,1)+timedelta(days=i)).isoformat(),'league_id':'lg','layout_id':'l','num_rounds':1,'categories':['MPO']}
  d['tournaments'].append(t);add_round(d,t['id'],'p',1,'MPO',99,{1:score+3})
 return d


class HandicapTests(unittest.TestCase):
 def test_ceiling_including_negative(self):
  self.assertEqual([ceil_handicap(n) for n in [7.1,-6.8,-7,0,3.0001]],[8,-6,-7,0,4])
 def test_initial_handicap_without_eligible_rounds(self):
  d=fixture([10,14,6]+list(range(4,14)));before=deepcopy(d);out=recalculate_handicaps(d)
  h=out['handicap_history']
  self.assertEqual([(r['handicap_used'],r['handicap_after']) for r in h[:3]],[(99,99)] * 3)
  self.assertEqual(h[10]['sources'],[])
  self.assertEqual(h[10]['selection_count'],0)
  self.assertEqual(out['players'][0]['handicap'],h[-1]['handicap_after'])
  self.assertEqual(d,before)
  self.assertTrue(all(r['original_handicap']==99 for r in out['rounds']))
  self.assertEqual(out,recalculate_handicaps(out));validate_data(out)
 def test_backdated_rebuild_and_no_raw_score_changes(self):
  d=fixture([10,14,6]);out=recalculate_handicaps(d)
  d['rounds'][0]['total']=8;d['rounds'][0]['holes'][0]['throws']=8
  new=recalculate_handicaps(d)
  self.assertEqual(new['handicap_history'][1]['handicap_used'],99)
  self.assertNotEqual(out['handicap_run']['id'],new['handicap_run']['id'])
  self.assertEqual(new['rounds'][1]['holes'],out['rounds'][1]['holes'])
  self.assertTrue(all(r['status']=='calculated' for r in new['stableford_results']))
 def test_multi_round_event_is_one_sample_and_incomplete_excluded(self):
  d=fixture([10,14]);d['tournaments'][1]['num_rounds']=2
  out=recalculate_handicaps(d);self.assertEqual(len(out['handicap_history']),1)
  add_round(d,'1','p',2,'MPO',99,{1:7})
  out=recalculate_handicaps(d)
  self.assertEqual(out['handicap_history'][-1]['event_score'],'9')
  self.assertEqual(out['handicap_history'][-1]['handicap_after'],99)
  self.assertEqual(out['handicap_history'][-1]['selection_count'],0)
 def test_same_date_requires_order_and_debut_pending(self):
  d=fixture([1,2]);d['tournaments'][1]['date']=d['tournaments'][0]['date']
  with self.assertRaises(ValueError):recalculate_handicaps(d)
  d['tournaments'][1]['event_order']=1
  recalculate_handicaps(d)
  save_player(d,'new','New','Player','MPO',0,'new')
  out=recalculate_handicaps(d);self.assertEqual(out['players'][-1]['handicap'],0)
  self.assertTrue(out['players'][-1]['handicap_provisional'])
 def test_relational_lossless_adapter_and_preserved_original_values(self):
  d=recalculate_handicaps(fixture([1,2]));d['players'][0]['custom_metadata']='preserved'
  self.assertEqual(from_records(to_records(d),d['revision']),d)

 def test_integer_sql_columns_are_json_integers_not_integral_floats(self):
  d=recalculate_handicaps(fixture([1,2]));d['leagues'][0]['points']=[10.0,8.0]
  records=to_records(d)
  self.assertTrue(all(type(r['points']) is int for r in records['league_points']))
  self.assertEqual(from_records(records,d['revision']),d)
  d['leagues'][0]['points']=[10.5]
  with self.assertRaises(ValueError):to_records(d)
