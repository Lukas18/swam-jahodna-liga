import tempfile
from pathlib import Path
import unittest

from import_players import prepare_players, read_pairs
from league.domain import empty_data, save_player


class PlayerImportTests(unittest.TestCase):
    def test_category_rule_and_names(self):
        data = empty_data()
        draft, added, skipped = prepare_players(data, [
            ('one', 'Andrea Nagyová'), ('two', 'Petra NOVAKOVA'),
            ('three', 'Diana Henderson Khwaja'), ('four', 'Viktor'),
            ('five', 'Eva Novakova\u0301'), ('six', 'Debnáriková'), ('seven', 'Tothova')])
        self.assertEqual([p['category'] for p in added], ['FPO', 'FPO', 'MPO', 'MPO', 'FPO', 'FPO', 'FPO'])
        self.assertEqual(added[2]['first_name'], 'Diana Henderson')
        self.assertEqual(added[2]['last_name'], 'Khwaja')
        self.assertEqual(added[3]['last_name'], '')
        self.assertTrue(all(p['handicap'] == 0 for p in added))
        self.assertEqual(data['players'], [])
        self.assertEqual(len(draft['players']), 7)
        self.assertEqual(skipped, [])

    def test_existing_players_and_repeated_rows_are_unchanged(self):
        data = empty_data()
        original = save_player(data, None, 'Andrea', 'Nagyová', 'MA3', 7, 'aďuška')
        draft, added, skipped = prepare_players(data, [
            (' AĎUŠKA ', 'Another Name'), ('newhandle', 'Andrea   Nagyová'),
            ('new', 'Petra Melicharová'), ('NEW', 'Petra Melicharová')])
        self.assertEqual(len(added), 1)
        self.assertEqual(len(skipped), 3)
        self.assertEqual(draft['players'][0], original)
        again, additions, _ = prepare_players(draft, [('new', 'Petra Melicharová')])
        self.assertEqual(additions, [])
        self.assertEqual(again, draft)

    def test_missing_category_does_not_modify_input(self):
        data = empty_data()
        data['categories'].remove('FPO')
        with self.assertRaises(ValueError):
            prepare_players(data, [('one', 'Peter Novak'), ('two', 'Eva Novakova')])
        self.assertEqual(data['players'], [])

    def test_csv_bom_delimiter_and_blank_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pairs.csv'
            path.write_text('\ufeffusername;name\npetra;Petra Melicharová\n;\n', encoding='utf-8')
            self.assertEqual(read_pairs(path), [('petra', 'Petra Melicharová')])
            path.write_text('username;name\n;Missing Username\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                read_pairs(path)
