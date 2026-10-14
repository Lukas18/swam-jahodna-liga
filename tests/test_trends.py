from copy import deepcopy
import unittest
from league.statistics import scoring_trend,top_trend_players
from test_handicaps import fixture
from league.domain import add_round,save_player


class ScoringTrendTests(unittest.TestCase):
 def test_chronological_relative_par_and_player_filter(self):
  data=fixture([5,-1,3]);data['rounds'].reverse()
  rows=scoring_trend(data,data['rounds'])
  self.assertEqual([r['Average +/− par'] for r in rows],[5,-1,3])
  self.assertEqual(scoring_trend(data,data['rounds'],[]),[])
  self.assertEqual(scoring_trend(data,data['rounds'],['p']),rows)
 def test_player_equal_weight_and_layout_isolation(self):
  data=fixture([5]);data['tournaments'][0]['num_rounds']=2
  add_round(data,'0','p',2,'MPO',99,{1:10})
  save_player(data,'second','Second','Player','MPO',0,'second')
  add_round(data,'0','second',1,'MPO',0,{1:4})
  # Player P mean is 6; second player mean is 1 => 3.5, not 13/3.
  row=scoring_trend(data,data['rounds'])[0]
  self.assertEqual(row['Average +/− par'],3.5)
  self.assertEqual(row['Players'],2)
  layout=deepcopy(data['layouts'][0]);layout['id']='green';data['layouts'].append(layout)
  data['tournaments'].append({**data['tournaments'][0],'id':'green-event','layout_id':'green'})
  add_round(data,'green-event','second',1,'MPO',0,{1:5})
  rows=scoring_trend(data,data['rounds'])
  self.assertEqual(len(rows),2)
  self.assertEqual({r['layout_id'] for r in rows},{'l','green'})

 def test_top_cohort_uses_best_event_average_with_stable_ties(self):
  data=fixture([5,1])
  for pid,name,score in [('a','Alpha',0),('b','Beta',2),('c','Charlie',2),('d','Delta',7),('e','Echo',8)]:
   save_player(data,pid,name,'Player','MPO',0,pid)
   add_round(data,'0',pid,1,'MPO',0,{1:score+3})
  self.assertEqual(top_trend_players(data,data['rounds'],3),['a','b','c'])
  self.assertEqual(top_trend_players(data,data['rounds'],5),['a','b','c','p','d'])
  selected=scoring_trend(data,data['rounds'],top_trend_players(data,data['rounds'],3))
  self.assertEqual(len(selected),1)  # no invented zero at the next event
  self.assertAlmostEqual(selected[0]['Average +/− par'],4/3)

 def test_precomputed_summaries_preserve_multi_round_weights_and_categories(self):
  from league.statistics import trend_observations,selected_rounds
  data=fixture([5,1]);data['tournaments'][0]['num_rounds']=2
  add_round(data,'0','p',2,'MPO',99,{1:10})
  data['tournaments'][0]['categories'].append('FPO')
  save_player(data,'f','Female','Player','FPO',0,'f')
  add_round(data,'0','f',1,'FPO',0,{1:3})
  observations=trend_observations(data)
  self.assertLess(len(observations),len(data['rounds']))
  for category in ['All','MPO','FPO']:
   raw=selected_rounds(data,category=category)
   compact=selected_rounds({**data,'rounds':observations},category=category)
   self.assertEqual(scoring_trend(data,raw),scoring_trend(data,compact))
   self.assertEqual(top_trend_players(data,raw,3),top_trend_players(data,compact,3))
  self.assertEqual(top_trend_players(data,selected_rounds({**data,'rounds':observations},category='FPO'),3),['f'])
