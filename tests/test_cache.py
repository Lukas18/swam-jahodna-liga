"""Read reuse, mutation isolation and save invalidation without network writes."""
import unittest
from copy import deepcopy
from unittest.mock import patch
from league.cache import load_view_state, clear_view_cache
from league.handicaps import recalculate_handicaps
from test_handicaps import fixture


class FakeStore:
    def __init__(self, key='main', scores=(2, 4)):
        self.cache_key = ('test-backend', key, 'relational')
        self.data = recalculate_handicaps(fixture(scores))
        self.loads = 0

    def load(self):
        self.loads += 1
        return deepcopy(self.data), str(self.data['revision'])

    def save(self, data, version):
        self.data = deepcopy(data)


class ViewCacheTests(unittest.TestCase):
    def setUp(self):
        clear_view_cache()

    def tearDown(self):
        clear_view_cache()

    def test_reuses_reads_and_returns_independent_objects(self):
        store = FakeStore()
        data, _, observations = load_view_state(store)
        data['players'][0]['first_name'] = 'Changed locally'
        observations[0]['total'] = 999
        again, _, summaries = load_view_state(store)
        self.assertEqual(store.loads, 1)
        self.assertEqual(again['players'][0]['first_name'], 'One')
        self.assertNotEqual(summaries[0]['total'], 999)

    def test_save_and_refresh_rebuild_summaries(self):
        store = FakeStore()
        data, version, old = load_view_state(store)
        data['rounds'][0]['total'] += 5
        with patch('league.database.get_store', return_value=store):
            from league.database import save_data
            save_data(data, version)
        _, _, new = load_view_state(store)
        self.assertEqual(store.loads, 2)
        self.assertEqual(new[0]['total'], old[0]['total'] + 5)
        clear_view_cache()  # Same invalidation used by the Refresh results button.
        load_view_state(store)
        self.assertEqual(store.loads, 3)

    def test_documents_and_backend_models_are_isolated(self):
        first, second = FakeStore('one'), FakeStore('two', (8,))
        self.assertNotEqual(load_view_state(first)[2], load_view_state(second)[2])
        second.cache_key = ('other-backend', 'one', 'json')
        load_view_state(second)
        self.assertEqual(second.loads, 2)

    def test_current_handicaps_are_not_recalculated_on_reads(self):
        with patch('league.cache.recalculate_handicaps') as recalculate:
            load_view_state(FakeStore())
            recalculate.assert_not_called()

    def test_client_is_reused_but_configuration_changes_are_isolated(self):
        from league.database import get_store, _cached_store
        from types import SimpleNamespace
        _cached_store.clear()
        try:
            with patch('league.database.st.secrets', SimpleNamespace(to_dict=lambda: {})), \
                 patch.dict('os.environ', {'SUPABASE_URL': 'https://example.invalid', 'SUPABASE_KEY': 'first'}), \
                 patch('league.database.Store') as constructor:
                first = get_store()
                self.assertIs(get_store(), first)
                self.assertEqual(constructor.call_count, 1)
                with patch.dict('os.environ', {'SUPABASE_KEY': 'rotated'}):
                    get_store()
                self.assertEqual(constructor.call_count, 2)
        finally:
            _cached_store.clear()
