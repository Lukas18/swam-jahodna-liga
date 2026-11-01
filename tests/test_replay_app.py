"""Standalone replay startup and workbook upload regressions; no league writes."""
from io import BytesIO
import unittest
from openpyxl import Workbook
from replay_app.app import app


def workbook_bytes():
    book = Workbook()
    book.active.title = 'Event results'
    for number in (1, 2):
        sheet = book.create_sheet(f'Round {number}')
        sheet.append(['name', 'username', 'division', 'starting_hole', 'round_total_score',
                      'round_relative_score'] + [f'hole_{n}' for n in range(1, 19)])
        for name, user, division, start, scores in [
            ('Anna Replay', 'anna', 'FPO', 18, [3] * 17 + [6]),
            ('Boris Replay', 'boris', 'MPO', 8, [4] * 18),
            ('Cyril Replay', 'cyril', 'MPO', 1, [2] + [3] * 17),
        ]:
            sheet.append([name, user, division, start, sum(scores), sum(scores) - 54] + scores)
    content = BytesIO()
    book.save(content)
    return content.getvalue()


class ReplayAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_landing_page_and_replay_assets_load(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Open replay', response.data)
        for path in ['app.js', 'style.css', 'standings.css', 'images/birdie-face.png', 'images/eagle-face.png', 'images/sad-frog.png', 'images/crying-frog.png']:
            with self.client.get('/static/' + path) as response:
                self.assertEqual(response.status_code, 200, path)

    def test_upload_retains_rounds_and_shotgun_starts(self):
        response = self.client.post('/api/workbook', data={
            'file': (BytesIO(workbook_bytes()), 'replay-smoke.xlsx')})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['player_count'], 3)
        self.assertEqual([r['number'] for r in data['rounds']], [1, 2])
        self.assertEqual([p['start'] for p in data['rounds'][0]['players']], [18, 8, 1])
        self.assertEqual(data['rounds'][0]['players'][0]['scores'][-1], 6)
        self.assertEqual(data['divisions'], ['FPO', 'MPO'])

    def test_corrupted_workbook_returns_json_error_instead_of_500(self):
        response = self.client.post('/api/workbook', data={
            'file': (BytesIO(b'not an Excel workbook'), 'broken.xlsx')})
        self.assertEqual(response.status_code, 400)
        self.assertIn('valid', response.get_json()['error'])

    def test_missing_upload_and_oversized_workbook_are_rejected(self):
        self.assertEqual(self.client.post('/api/workbook').status_code, 400)
        response = self.client.post('/api/workbook', data={
            'file': (BytesIO(b'x' * (8 * 1024 * 1024 + 1)), 'oversized.xlsx')})
        self.assertEqual(response.status_code, 413)
        self.assertIn('8 MB', response.get_json()['error'])
        response.request.input_stream.close()
        response.close()


if __name__ == '__main__':
    unittest.main()
