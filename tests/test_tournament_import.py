from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
import pandas as pd
from import_tournaments import filename_metadata, prepare_batch
from league.domain import empty_data, save_player


def fixture():
    d = empty_data()
    d['courses'] = [{'id': 'c', 'name': 'Jahodna', 'description': ''}]
    d['layouts'] = [{'id': 'red', 'name': 'Cervena', 'course_id': 'c', 'profiles': {
        'default': [{'number': 1, 'par': 3, 'length': 90}, {'number': 2, 'par': 3, 'length': 80}]}}]
    d['leagues'] = [{'id': 'lg', 'name': 'League', 'points': [10, 8], 'points_scope': 'category', 'tie_mode': 'shared'}]
    save_player(d, 'p', 'Petra', 'Novakova', 'FPO', 0, 'petra')
    return d


class TournamentImportTests(unittest.TestCase):
    def test_filename_formats_and_layouts(self):
        self.assertEqual(filename_metadata('sobotnajsie-discgolfove-turnaje-2-turnaj-2025-06-21.xlsx'),
                         {'name': 'Sobotnajsie Discgolfove Turnaje (2. turnaj)', 'date': '2025-06-21', 'layout': 'cervena'})
        for marker in ['cervena', 'zelena']:
            self.assertEqual(filename_metadata(f'nedelny-turnaj-swam-jahodna-{marker}-2026-04-26.xlsx')['name'], 'Nedelny Turnaj Swam Jahodna')
        self.assertEqual(filename_metadata('sobotnajsie-discgolfove-turnaje-novy-okruh-zelena-2025-10-18.xlsx')['name'], 'Sobotnajsie Discgolfove Turnaje Novy Okruh')
        with self.assertRaises(ValueError):
            filename_metadata('event-2025-02-30.xlsx', 'zelena')
        with self.assertRaises(ValueError):
            filename_metadata('event-2025-02-28.xlsx')
        self.assertEqual(filename_metadata('event-2025-02-28.xlsx', 'zelena')['layout'], 'zelena')

    def run_batch(self, data, rows, **kwargs):
        file = Path('sobotnajsie-discgolfove-turnaje-2-turnaj-2025-06-21.xlsx')
        with patch.object(Path, 'read_bytes', return_value=b'workbook'), patch('import_tournaments.read_export', return_value=pd.DataFrame(rows)):
            return prepare_batch(data, [file], {'2025': 'lg'}, **kwargs)

    def row(self, **values):
        return {'username': 'petra', 'name': 'Petra Novakova', 'division': '0-18',
                'hole_1': '3', 'hole_2': '4', 'round_total_score': '7', 'event_relative_score': '999', **values}

    def test_creation_registration_relative_score_and_idempotence(self):
        original = fixture()
        draft, report = self.run_batch(original, [self.row()])
        self.assertEqual(original['tournaments'], [])
        self.assertTrue(report[0]['created'])
        self.assertEqual(draft['rounds'][0]['par'], 6)
        self.assertEqual(draft['rounds'][0]['category'], 'FPO')
        self.assertEqual(len(draft['registrations']), 1)
        again, report = self.run_batch(draft, [self.row()])
        self.assertEqual(again, draft)
        self.assertEqual(report[0]['identical_rounds'], 1)
        with self.assertRaisesRegex(ValueError, 'existing scores differ'):
            self.run_batch(draft, [self.row(hole_2='5', round_total_score='8')])

    def test_invalid_rows_leave_original_unchanged(self):
        data = fixture()
        original = deepcopy(data)
        for row in [self.row(username='unknown'), self.row(round_total_score='8'), self.row(hole_1='')]:
            with self.assertRaises(ValueError):
                self.run_batch(data, [row])
        self.assertEqual(data, original)

    def test_unscored_registration_and_missing_username_override(self):
        draft, report = self.run_batch(fixture(), [self.row(username='', hole_1='', hole_2='', round_total_score='DNF')],
                                       usernames={'Petra Novakova': 'petra'}, unscored='register')
        self.assertEqual(draft['rounds'], [])
        self.assertEqual(len(draft['registrations']), 1)
        self.assertEqual(report[0]['registered_without_scores'], ['Petra Novakova'])

    def test_explicit_skip_precedes_missing_username_check(self):
        draft, report = self.run_batch(fixture(), [self.row(username='', name='Martin Kellner')], skip_names=['Martin Kellner'])
        self.assertEqual(draft['rounds'], [])
        self.assertEqual(report[0]['skipped'], ['Martin Kellner'])

    def test_division_category_and_duplicate_rows(self):
        draft, _ = self.run_batch(fixture(), [self.row(division='MA3')])
        self.assertEqual(draft['rounds'][0]['category'], 'MA3')
        with self.assertRaisesRegex(ValueError, 'duplicate player'):
            self.run_batch(fixture(), [self.row(), self.row()])
