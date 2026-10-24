import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock,patch
from league.storage import Store,StorageError
from test_handicaps import fixture
from league.handicaps import recalculate_handicaps
from league.relational import to_records


class RelationalStoreTests(unittest.TestCase):
 def store(self, response):
  client=Mock();client.rpc.return_value.execute.return_value=SimpleNamespace(data=response)
  with patch('league.storage.create_client',return_value=client):
   store=Store(supabase={'url':'https://example.invalid','key':'test','model':'relational'})
  return store,client
 def test_load_normalized_document(self):
  data=recalculate_handicaps(fixture([1,2]));payload=to_records(data);payload['revision']=3
  store,client=self.store(payload);out,version=store.load()
  data['revision']=3;self.assertEqual(out,data);self.assertEqual(version,'3')
  self.assertEqual(client.rpc.call_args.args[0],'dg_load')
 def test_failed_save_leaves_caller_unchanged(self):
  store,_=self.store(False);data=fixture([1]);before=deepcopy(data)
  with self.assertRaises(StorageError):store.save(data,'0')
  self.assertEqual(data,before)
 def test_save_sends_separate_tables_and_updates_history(self):
  store,client=self.store(True);data=fixture([1,3]);store.save(data,'0')
  args=client.rpc.call_args
  self.assertEqual(args.args[0],'dg_save');self.assertEqual(data['revision'],1)
  self.assertEqual(data['players'][0]['handicap'],99)
  self.assertIn('hole_scores',args.args[1]['p_payload'])
  self.assertNotIn('rounds',args.args[1]['p_payload'])
