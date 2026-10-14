"""Versioned league store backed by Supabase PostgreSQL.

Legacy JSON mode uses save_app_data. Relational mode uses sql/001_relational.sql.
"""
import copy
import hashlib
import json
import os

from supabase import create_client

from .domain import empty_data, validate_data


class StorageError(Exception):
    pass


def encoded(data):
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')


class Store:
    def __init__(self, path='data/league.json', github=None, supabase=None):
        # path and github are accepted for compatibility with existing callers.
        # Neither is used by this Supabase-only implementation.
        cfg = supabase or {}
        url = cfg.get('url') or os.environ.get('SUPABASE_URL')
        key = cfg.get('key') or os.environ.get('SUPABASE_KEY')
        self.document_id = cfg.get('document_id', os.environ.get('DISCGOLF_DOCUMENT_ID', 'main'))
        self.model = cfg.get('model') or os.environ.get('DISCGOLF_STORAGE_MODEL', 'json')
        if self.model not in ['json', 'relational']:
            raise StorageError('Storage model must be json or relational.')
        if not url or not key:
            raise StorageError('SUPABASE_URL and SUPABASE_KEY must be configured.')
        self._connection_identity = hashlib.sha256((url + '\0' + key).encode()).hexdigest()
        self.db = create_client(url, key)

    @property
    def cache_key(self):
        return (self._connection_identity, self.document_id, self.model)

    def load(self):
        try:
            if self.model == 'relational':
                from .relational import from_records
                response = self.db.rpc('dg_load', {'p_document_id': self.document_id}).execute()
                if not response.data:
                    raise StorageError('Relational document not migrated. Run migrate_relational.py first.')
                data = from_records(response.data, response.data['revision'])
                return validate_data(data), str(data['revision'])
            response = (self.db.table('app_data')
                        .select('content')
                        .eq('id', self.document_id)
                        .limit(1)
                        .execute())
            if not response.data:
                return empty_data(), None
            data = validate_data(response.data[0]['content'])
            # Version is the authoritative integer revision in the persisted JSON.
            return data, str(data.get('revision', 0))
        except StorageError:
            raise
        except (ValueError, KeyError, TypeError) as exc:
            raise StorageError(f'Invalid stored data: {exc}') from exc
        except Exception as exc:
            raise StorageError(f'Could not load data from Supabase: {exc}') from exc

    def save(self, data, expected_version):
        # A copy avoids incrementing the caller's revision on failed saves.
        outgoing = copy.deepcopy(data)
        if self.model == 'relational' or 'handicap_run' in outgoing:
            from .handicaps import recalculate_handicaps
            outgoing = recalculate_handicaps(outgoing)
        validate_data(outgoing)
        try:
            # Round-trip via JSON to validate JSON compatibility before writing.
            outgoing = json.loads(encoded(outgoing))
        except (TypeError, ValueError) as exc:
            raise StorageError(f'Data cannot be serialized as JSON: {exc}') from exc

        # expected_version=None only applies when the document does not exist.
        # For existing documents the PostgreSQL function performs atomic CAS.
        expected = None if expected_version is None else int(expected_version)
        outgoing['revision'] = (expected if expected is not None else 0) + 1
        try:
            if self.model == 'relational':
                from .relational import to_records
                response = self.db.rpc('dg_save', {'p_document_id': self.document_id,
                    'p_expected_revision': expected, 'p_payload': to_records(outgoing)}).execute()
            else:
                response = self.db.rpc('save_app_data', {
                    'p_id': self.document_id,
                    'p_expected_revision': expected,
                    'p_content': outgoing,
                }).execute()
            if response.data is not True:
                raise StorageError('Data changed since this page loaded. Refresh and try again.')
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(f'Could not save data to Supabase: {exc}') from exc
        # Maintain previous behavior: update the caller after confirmed success.
        data.clear()
        data.update(outgoing)
