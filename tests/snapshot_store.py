"""Isolated file-backed fake for UI tests; never connects to Supabase."""
import hashlib
import json
from pathlib import Path
from league.domain import validate_data
from league.handicaps import recalculate_handicaps
from league.storage import StorageError,encoded


class SnapshotStore:
 def __init__(self,path):self.path=Path(path)
 def load(self):
  blob=self.path.read_bytes()
  return validate_data(json.loads(blob)),hashlib.sha256(blob).hexdigest()
 def save(self,data,expected_version):
  _,version=self.load()
  if version!=expected_version:raise StorageError('Data changed since this page loaded.')
  out=recalculate_handicaps(data) if 'handicap_run' in data else data.copy()
  out['revision']=out.get('revision',0)+1
  validate_data(out);self.path.write_bytes(encoded(out));data.clear();data.update(out)
