import unittest
from copy import deepcopy
from io import BytesIO
import tempfile
from pathlib import Path
from unittest.mock import patch
import base64
import pandas as pd
from league.domain import (empty_data, save_player, add_round, tournament_results, league_results,
                           hole_stats, validate_data, award_points, outcome, resize_holes, register_player, tournament_entries, score_grid, save_score_grid)
from league.imports import preview_import, read_export
from league.storage import Store, StorageError, encoded


def fixture():
    d = empty_data()
    d['categories'].append('MJ15')  # Explicit fixture category for junior-profile coverage.
    d['courses'] = [{'id': 'c', 'name': 'Park', 'description': ''}]
    d['layouts'] = [{'id': 'l', 'name': 'Main', 'course_id': 'c', 'profiles': {
        'default': [{'number': 1, 'par': 3, 'length': 90}, {'number': 2, 'par': 4, 'length': 120}],
        'MJ15': [{'number': 1, 'par': 3, 'length': 40}]}}]
    d['leagues'] = [{'id': 'lg', 'name': 'League', 'points': [10, 6, 3], 'points_scope': 'category', 'tie_mode': 'shared'}]
    d['tournaments'] = [{'id': 't', 'name': 'Open', 'date': '2026-10-08', 'league_id': 'lg', 'layout_id': 'l', 'num_rounds': 1, 'categories': ['MPO', 'MJ15']}]
    for pid, first, cat, hcp in [('a', 'Alice', 'MPO', 1), ('b', 'Bob', 'MPO', 0), ('j', 'Junior', 'MJ15', 0)]:
        save_player(d, pid, first, 'Player', cat, hcp, first)
    return d


class RulesTest(unittest.TestCase):
    def test_ties_and_category_points(self):
        d = fixture()
        add_round(d, 't', 'a', 1, 'MPO', 1, {1: 3, 2: 4})
        add_round(d, 't', 'b', 1, 'MPO', 0, {1: 2, 2: 5})
        add_round(d, 't', 'j', 1, 'MJ15', 0, {1: 3})
        rows = league_results(d, 'lg')
        points = {r['Player'].split()[0]: r['Points'] for r in rows}
        self.assertEqual(points, {'Junior': 10, 'Alice': 8, 'Bob': 8})
        hcp = league_results(d, 'lg', 'MPO', 'handicap')
        self.assertEqual([r['Points'] for r in hcp], [10, 6])
        self.assertEqual(tournament_results(d, 't', 'MPO')[1]['Place'], 1)

    def test_completed_rounds_only_and_replace(self):
        d = fixture()
        d['tournaments'][0]['num_rounds'] = 2
        add_round(d, 't', 'a', 1, 'MPO', 1, {1: 2, 2: 4})
        self.assertEqual(league_results(d, 'lg'), [])
        add_round(d, 't', 'a', 2, 'MPO', 1, {1: 4, 2: 4})
        add_round(d, 't', 'a', 2, 'MPO', 1, {1: 3, 2: 4})
        self.assertEqual(len(d['rounds']), 2)
        self.assertEqual(league_results(d, 'lg')[0]['Points'], 10)
        with self.assertRaises(ValueError):
            add_round(d, 't', 'a', 2, 'MJ15', 0, {1: 2})

    def test_snapshots_and_mutually_exclusive_outcomes(self):
        d = fixture()
        for pid, scores in [('a', {1: 1, 2: 4}), ('b', {1: 2, 2: 5})]:
            add_round(d, 't', pid, 1, 'MPO', 0, scores)
        d['layouts'][0]['profiles']['default'][0]['par'] = 5
        self.assertEqual(tournament_results(d, 't', 'MPO')[0]['+/− par'], -2)
        stats = hole_stats(d, 'l', 'MPO')[0]
        self.assertEqual(stats['Average throws'], 1.5)
        self.assertEqual(stats['Ace %'], 50)
        self.assertEqual(stats['Birdie %'], 50)
        self.assertEqual(sum(v for k, v in stats.items() if k.endswith(' %')), 100)
        self.assertEqual(outcome(1, 4), 'Ace')
        validate_data(d)

    def test_totals_only_does_not_invent_holes(self):
        d = fixture()
        add_round(d, 't', 'a', 1, 'MPO', 0, total=8)
        self.assertEqual(hole_stats(d, 'l', 'MPO'), [])
        self.assertEqual(tournament_results(d, 't')[0]['+/− par'], 1)

    def test_invalid_scores_and_identity(self):
        d = fixture()
        for scores in [{1: 0, 2: 4}, {1: 2.5, 2: 4}, {1: 2}, {1: 2, 2: 4, 3: 3}]:
            with self.assertRaises(ValueError):
                add_round(d, 't', 'a', 1, 'MPO', 0, scores)
        with self.assertRaises(ValueError):
            save_player(d, None, 'Other', 'Name', 'MPO', 0, ' ALICE ')
        with self.assertRaises(ValueError):
            add_round(d, 't', 'a', 2, 'MPO', 0, total=5)
        with self.assertRaises(ValueError):
            add_round(d, 't', 'a', 1, 'MPO', float('nan'), total=5)

    def test_league_accumulates_and_ties_past_point_cutoff(self):
        d = fixture()
        d['leagues'][0]['points'] = [10]
        add_round(d, 't', 'a', 1, 'MPO', 0, total=7)
        add_round(d, 't', 'b', 1, 'MPO', 0, total=7)
        self.assertEqual([r['Points'] for r in league_results(d, 'lg')], [5, 5])
        d['tournaments'].append(dict(d['tournaments'][0], id='t2'))
        add_round(d, 't2', 'a', 1, 'MPO', 0, total=6)
        self.assertEqual(league_results(d, 'lg')[0]['Points'], 15)

    def test_combined_boards_keep_category_places(self):
        d = fixture()
        d['tournaments'][0]['categories'].append('FPO')
        save_player(d, 'f', 'FPO winner', 'Player', 'FPO', 0, 'fpo')
        for pid, cat, total in [('a', 'MPO', 7), ('b', 'MPO', 8), ('f', 'FPO', 5)]:
            add_round(d, 't', pid, 1, cat, 0, total=total)
        results = tournament_results(d, 't')
        self.assertEqual([(r['player_id'], r['Place']) for r in results], [('f', 1), ('a', 1), ('b', 2)])
        league = league_results(d, 'lg')
        self.assertEqual(next(r['Place'] for r in league if r['Player'].startswith('Bob')), 2)
        d['leagues'][0]['points_scope'] = 'overall'
        overall = league_results(d, 'lg')
        self.assertEqual(next(r['Points'] for r in overall if r['Player'].startswith('Bob')), 3)
        self.assertEqual(next(r['Place'] for r in overall if r['Player'].startswith('Bob')), 2)

    def test_each_league_view_is_independent_of_legacy_setting(self):
        d = fixture()
        add_round(d, 't', 'a', 1, 'MPO', 2, total=8)
        add_round(d, 't', 'b', 1, 'MPO', 0, total=7)
        d['leagues'][0]['ranking_metric'] = 'handicap'  # Older data remains readable.
        self.assertTrue(league_results(d, 'lg')[0]['Player'].startswith('Bob'))
        self.assertTrue(league_results(d, 'lg', metric='handicap')[0]['Player'].startswith('Alice'))
        validate_data(d)
        del d['leagues'][0]['ranking_metric']
        validate_data(d)

    def test_resize_preserves_holes_and_adds_valid_numbers(self):
        holes = [{'number': 1, 'par': 4, 'length': 100}, {'number': 3, 'par': 3, 'length': 50}]
        larger = resize_holes(holes, 4)
        self.assertEqual([h['number'] for h in larger], [1, 2, 3, 4])
        self.assertEqual(larger[0]['par'], 4)
        self.assertEqual(len(resize_holes(larger, 2)), 2)
        self.assertEqual(len(holes), 2)

    def test_integer_results_and_fractional_ties(self):
        d = fixture()
        d['leagues'][0]['points'] = [10, 7]
        add_round(d, 't', 'a', 1, 'MPO', 0.5, total=7)
        add_round(d, 't', 'b', 1, 'MPO', 0, total=7)
        self.assertEqual(tournament_results(d, 't')[0]['HCP adjusted'], -1)
        for row in league_results(d, 'lg'):
            self.assertIsInstance(row['Points'], int)
            self.assertIsInstance(row['HCP adjusted'], int)
            self.assertEqual(row['Points'], 9)

    def test_registration_without_scores_and_atomic_bulk_entry(self):
        d = fixture()
        for pid in ['a', 'b']:
            register_player(d, 't', pid)
        self.assertEqual(len(tournament_entries(d, 't')), 2)
        self.assertEqual(tournament_results(d, 't'), [])
        rows, _ = score_grid(d, 't', 1, 'MPO')
        self.assertTrue(all(r['H1'] is None for r in rows))
        for row in rows:
            row.update({'Save': True, 'H1': 3, 'H2': 4})
        rows[1]['H2'] = None
        with self.assertRaises(ValueError):
            save_score_grid(d, 't', 1, 'MPO', rows)
        self.assertEqual(d['rounds'], [])
        rows[1]['H2'] = 5
        saved = save_score_grid(d, 't', 1, 'MPO', rows)
        self.assertEqual(len(saved['rounds']), 2)
        validate_data(saved)
        # Replacing scores after tee changes preserves the recorded hole pars.
        saved['layouts'][0]['profiles']['default'][0]['par'] = 5
        rows, _ = score_grid(saved, 't', 1, 'MPO')
        rows[0]['Save'] = True
        rows[0]['H1'] = 2
        updated = save_score_grid(saved, 't', 1, 'MPO', rows)
        self.assertEqual(next(r['par'] for r in updated['rounds'] if r['player_id'] == 'a'), 7)
        self.assertEqual(len(updated['rounds']), 2)

    def test_registration_isolation_and_junior_grid(self):
        d = fixture()
        register_player(d, 't', 'j')
        rows, _ = score_grid(d, 't', 1, 'MJ15')
        self.assertNotIn('H2', rows[0])
        rows[0].update({'Save': True, 'H1': 2})
        saved = save_score_grid(d, 't', 1, 'MJ15', rows)
        self.assertEqual(saved['rounds'][0]['total'], 2)
        with self.assertRaises(ValueError):
            register_player(saved, 't', 'j', 'MPO')
        legacy = deepcopy(saved)
        del legacy['registrations']
        self.assertEqual(len(tournament_entries(legacy, 't')), 1)
        validate_data(legacy)

    def test_backup_rejects_invalid_links_and_duplicate_rounds(self):
        d = fixture()
        add_round(d, 't', 'a', 1, 'MPO', 0, total=7)
        broken = deepcopy(d)
        broken['rounds'].append(dict(broken['rounds'][0], id='different'))
        with self.assertRaises(ValueError):
            validate_data(broken)
        d['rounds'][0]['layout_id'] = 'missing'
        with self.assertRaises(ValueError):
            validate_data(d)


class ImportTest(unittest.TestCase):
    def test_udisc_ignores_exported_relative_scores(self):
        d = fixture()
        # hole_2 is a throw count; it must not choose a layout.
        frame = pd.DataFrame([{'username': 'alice', 'division': 'MPO', 'hole_1': 2,
                               'hole_2': 5, 'round_total_score': 7, 'round_relative_score': 0}])
        mapping = {'username': 'username', 'category': 'division', 'total': 'round_total_score',
                   'relative': 'round_relative_score', 'holes': {1: 'hole_1', 2: 'hole_2'}}
        draft, rows, errors = preview_import(d, 't', frame, mapping, 1)
        self.assertFalse(errors)
        self.assertEqual(rows[0]['Par'], 7)
        self.assertEqual(draft['rounds'][0]['holes'][1]['throws'], 5)
        frame.loc[0, 'round_relative_score'] = 'invalid exported value'
        frame['event_relative_score'] = -999
        draft, rows, errors = preview_import(d, 't', frame, mapping, 1)
        self.assertFalse(errors)
        self.assertEqual(rows[0]['Score relative to par'], 0)
        self.assertEqual(len(draft['rounds']), 1)

    def test_udisc_calculates_category_par_and_preserves_source(self):
        d = fixture()
        d['layouts'][0]['profiles']['MPO'] = [{'number': 1, 'par': 4, 'length': 90}, {'number': 2, 'par': 4, 'length': 120}]
        frame = pd.DataFrame([{'username': 'alice', 'total': 7, 'relative': 0}])
        draft, rows, errors = preview_import(d, 't', frame,
                                          {'username': 'username', 'total': 'total', 'relative': 'relative'}, 1)
        self.assertFalse(errors)
        self.assertEqual(rows[0]['Par'], 8)
        self.assertEqual(rows[0]['Score relative to par'], -1)
        self.assertEqual(d['rounds'], [])

    def test_import_layout_is_saved_atomically_and_controls_hole_par(self):
        d = fixture()
        red = deepcopy(d['layouts'][0])
        red.update(id='red', name='Red')
        red['profiles']['default'][1]['par'] = 3
        d['layouts'].append(red)
        frame = pd.DataFrame([{'User': 'Alice', 'H1': 3, 'H2': 4, 'Total': 7}])
        mapping = {'username': 'User', 'total': 'Total', 'holes': {1: 'H1', 2: 'H2'}}
        draft, rows, errors = preview_import(d, 't', frame, mapping, 1, layout_id='red')
        self.assertFalse(errors)
        self.assertEqual(d['tournaments'][0]['layout_id'], 'l')
        self.assertEqual(d['rounds'], [])
        self.assertEqual(draft['tournaments'][0]['layout_id'], 'red')
        self.assertEqual(draft['rounds'][0]['layout_id'], 'red')
        self.assertEqual(rows[0]['Layout'], 'Red')
        self.assertEqual(rows[0]['Par'], 6)
        self.assertEqual(rows[0]['Score relative to par'], 1)
        validate_data(draft)
        blocked, rows, errors = preview_import(draft, 't', frame, mapping, 1, layout_id='l')
        self.assertIn('existing layout', errors[0])
        self.assertEqual(blocked, draft)
        blocked, rows, errors = preview_import(d, 't', frame, mapping, 1, layout_id='missing')
        self.assertIn('valid import layout', errors[0])
        self.assertEqual(blocked, d)

    def test_players_can_use_single_names(self):
        d = fixture()
        p = save_player(d, None, 'Tomas', '', 'MPO', 0, 'tomijusko')
        validate_data(d)
        draft, rows, errors = preview_import(d, 't', pd.DataFrame([{'User': 'tomijusko', 'Total': 7}]),
                                             {'username': 'User', 'total': 'Total'}, 1)
        self.assertFalse(errors)
        self.assertEqual(rows[0]['Player'], 'Tomas')
        self.assertEqual(draft['rounds'][0]['player_id'], p['id'])
        with self.assertRaises(ValueError):
            save_player(d, None, ' ', '', 'MPO', 0, 'blank')

    def test_mapping_junior_and_atomic_errors(self):
        d = fixture()
        frame = pd.DataFrame([{'User': ' ALICE ', 'Cat': 'MPO', 'H1': 3, 'H2': 4},
                              {'User': 'Junior', 'Cat': 'MJ15', 'H1': 2, 'H2': ''}])
        mapping = {'username': 'User', 'category': 'Cat', 'holes': {1: 'H1', 2: 'H2'}}
        draft, rows, errors = preview_import(d, 't', frame, mapping, 1)
        self.assertFalse(errors)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(d['rounds']), 0)
        self.assertEqual(len(draft['rounds'][1]['holes']), 1)
        frame.loc[1, 'User'] = 'unknown'
        _, _, errors = preview_import(d, 't', frame, mapping, 1)
        self.assertIn('Unknown uDisc', errors[0])

    def test_duplicate_and_mismatched_total(self):
        d = fixture()
        frame = pd.DataFrame([{'User': 'Alice', 'Total': 7}, {'User': 'alice', 'Total': 8}])
        _, _, errors = preview_import(d, 't', frame, {'username': 'User', 'total': 'Total'}, 1)
        self.assertIn('Duplicate', errors[0])
        frame = pd.DataFrame([{'User': 'Alice', 'Total': 8, 'H1': 3, 'H2': 4}])
        _, _, errors = preview_import(d, 't', frame, {'username': 'User', 'total': 'Total', 'holes': {1: 'H1', 2: 'H2'}}, 1)
        self.assertIn('does not match', errors[0])

    def test_csv_reading(self):
        frame = read_export(b'User;H1;H2\nAlice;3;4\n', 'scores.csv')
        self.assertEqual(frame.iloc[0]['H1'], '3')

    def test_excel_reading_without_authoring(self):
        # Build a minimal OOXML fixture with stdlib: this is parser test data, not a user workbook.
        from zipfile import ZipFile
        stream = BytesIO()
        with ZipFile(stream, 'w') as z:
            z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
            z.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
            z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Scores" sheetId="1" r:id="rId1"/></sheets></workbook>')
            z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>User</t></is></c><c r="B1" t="inlineStr"><is><t>Total</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>Alice</t></is></c><c r="B2" t="n"><v>7</v></c></row></sheetData></worksheet>')
        frame = read_export(stream.getvalue(), 'scores.xlsx')
        self.assertEqual(frame.iloc[0]['User'], 'Alice')
        self.assertEqual(frame.iloc[0]['Total'], '7')


class StorageTest(unittest.TestCase):
    def test_atomic_local_and_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp)/'data.json')
            d, version = store.load()
            store.save(d, version)
            loaded, current = store.load()
            self.assertEqual(loaded['revision'], 1)
            with self.assertRaises(StorageError):
                store.save(loaded, version)
            self.assertEqual(store.load()[1], current)

    def test_github_uses_sha_and_roundtrips(self):
        d = fixture()
        store = Store(github={'repository': 'me/data', 'token': 'fake'})
        raw = encoded(d)
        with patch.object(store, 'api', return_value={'content': base64.b64encode(raw).decode(), 'sha': 'abc'}):
            loaded, sha = store.load()
            self.assertEqual(sha, 'abc')
        with patch.object(store, 'api', return_value={}) as api:
            store.save(loaded, sha)
            payload = api.call_args.args[1]
            self.assertEqual(payload['sha'], 'abc')
            self.assertEqual(payload['branch'], 'main')
            self.assertEqual(base64.b64decode(payload['content']), encoded(loaded))


if __name__ == '__main__':
    unittest.main()


class PlaceLabelsTest(unittest.TestCase):
    def test_ties_are_category_specific_and_rules_stay_numeric(self):
        from league.domain import place_labels
        rows = [{'Category': 'MPO', 'Place': p} for p in [1, 2, 3, 3, 5]]
        rows.append({'Category': 'FPO', 'Place': 1})
        self.assertEqual(place_labels(rows), ['1', '2', 'T3', 'T3', '5', '1'])
        self.assertEqual(rows[2]['Place'], 3)
