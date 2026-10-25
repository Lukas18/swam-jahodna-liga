import unittest

from league.domain import add_round, save_player
from league.scorecards import round_scorecard_html
from test_league import fixture


LABELS = {label: label for label in
          ['#', 'Name', 'Category', 'Total', 'Round', 'Hole', 'Par', 'Totals only']}


class RoundScorecardTests(unittest.TestCase):
    def test_players_share_one_table_with_saved_holes_and_category_places(self):
        data = fixture()
        add_round(data, 't', 'a', 1, 'MPO', 1, {1: 2, 2: 5})
        add_round(data, 't', 'b', 1, 'MPO', 0, {1: 3, 2: 4})
        add_round(data, 't', 'j', 1, 'MJ15', 0, {1: 1})
        data['players'][0]['first_name'] = '<Alice & Co>'
        data['layouts'][0]['profiles']['default'][1]['par'] = 5

        html = round_scorecard_html(data, data['rounds'], LABELS)

        self.assertEqual(html.count('<table>'), 1)
        self.assertIn('<th scope="col" class="position">#</th>', html)
        self.assertEqual(html.count('<tbody><tr>'), 1)
        self.assertEqual(html.count('</tr>'), 4)  # Header and three players.
        self.assertIn('&lt;Alice &amp; Co&gt;', html)
        self.assertNotIn('<Alice & Co>', html)
        self.assertIn('<th scope="col" class="category">Category</th>', html)
        self.assertIn('120 m</small><small>Par 4</small>', html)  # Recorded snapshot, not edited layout.
        self.assertIn('class="score under">2</span>', html)
        self.assertIn('class="score over">5</span>', html)
        self.assertIn('class="score ace">1</span>', html)
        self.assertIn('class="hole empty">—</td>', html)  # Junior has no second hole.
        self.assertEqual(html.count('class="position">T1</td>'), 2)  # MPO tie.
        mpo = round_scorecard_html(data, [r for r in data['rounds'] if r['category'] == 'MPO'], LABELS)
        self.assertIn('<span>Round</span><small>210 m</small><small>Par 7</small>', mpo)

    def test_totals_only_scorecard_remains_in_combined_table(self):
        data = fixture()
        add_round(data, 't', 'a', 1, 'MPO', 1, {1: 3, 2: 4})
        add_round(data, 't', 'b', 1, 'MPO', 0, total=8)

        html = round_scorecard_html(data, data['rounds'], LABELS)

        self.assertEqual(html.count('<table>'), 1)
        self.assertIn('Bob Player<small class="totals-only">Totals only</small>', html)
        self.assertIn('<td class="round-total">8</td>', html)
        self.assertEqual(html.count('class="hole empty">—</td>'), 2)

    def test_above_par_scores_use_progressively_stronger_colors(self):
        data = fixture()
        for player_id, throws in [('a', 4), ('b', 5), ('c', 6), ('d', 7), ('e', 8)]:
            if player_id not in {'a', 'b'}:
                save_player(data, player_id, player_id.upper(), 'Player', 'MPO', 0, player_id)
            add_round(data, 't', player_id, 1, 'MPO', 0, {1: throws, 2: 4})

        html = round_scorecard_html(data, data['rounds'], LABELS)
        for throws, css_class in [(4, 'over'), (5, 'over over-2'), (6, 'over over-3'),
                                  (7, 'over over-4'), (8, 'over over-4')]:
            self.assertIn(f'class="score {css_class}">{throws}</span>', html)
