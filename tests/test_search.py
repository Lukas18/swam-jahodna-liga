import unittest
from league.search import matching_players,search_key


class PlayerSearchTests(unittest.TestCase):
 def test_both_directions_casefold_and_combining_marks(self):
  players=[{'id':'a','first_name':'Mário','last_name':'Haško','udisc':'hasky5'},
           {'id':'b','first_name':'Martin','last_name':'Novak','udisc':'other'}]
  self.assertEqual(len(matching_players(players,'Mar')),2)
  self.assertEqual(len(matching_players(players,'Már')),2)
  self.assertEqual(matching_players(players,'HASKO'),players[:1])
  self.assertEqual(matching_players(players,'haško mario'),players[:1])
  self.assertEqual(matching_players(players,'hasky5'),[])
  self.assertEqual(matching_players(players,'hasky5',True),players[:1])
  self.assertEqual(search_key('Ma\u0301rio'),'mario')
  self.assertEqual(players[0]['first_name'],'Mário')
