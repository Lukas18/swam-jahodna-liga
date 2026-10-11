"""Versioned league store backed by Supabase PostgreSQL.

Requires SQL function save_app_data defined in setup_supabase_store.sql.
"""
import copy
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
        self.document_id = cfg.get('document_id', 'main')
        if not url or not key:
            raise StorageError('SUPABASE_URL and SUPABASE_KEY must be configured.')
        self.db = create_client(url, key)

    def load(self):
        try:
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
        data['revision'] = outgoing['revision']


# """Versioned league store backed by Supabase PostgreSQL.
#
# Requires SQL function save_app_data defined in setup_supabase_store.sql.
# """
# import copy
# import json
# import os
#
# from supabase import create_client
#
# from .domain import empty_data, validate_data
#
#
# class StorageError(Exception):
#     pass
#
#
# def encoded(data):
#     return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
#
#
# class Store:
#     def __init__(self, path='data/league.json', github=None, supabase=None):
#         # path and github are accepted for compatibility with existing callers.
#         # Neither is used by this Supabase-only implementation.
#         cfg = supabase or {}
#         url = cfg.get('url') or os.environ.get('SUPABASE_URL')
#         key = cfg.get('key') or os.environ.get('SUPABASE_KEY')
#         self.document_id = cfg.get('document_id', 'main')
#         if not url or not key:
#             raise StorageError('SUPABASE_URL and SUPABASE_KEY must be configured.')
#         self.db = create_client(url, key)
#
#     def load(self):
#         try:
#             response = (self.db.table('app_data')
#                         .select('content')
#                         .eq('id', self.document_id)
#                         .limit(1)
#                         .execute())
#             if not response.data:
#                 return empty_data(), None
#             data = validate_data(response.data[0]['content'])
#             # Version is the authoritative integer revision in the persisted JSON.
#             return data, str(data.get('revision', 0))
#         except StorageError:
#             raise
#         except (ValueError, KeyError, TypeError) as exc:
#             raise StorageError(f'Invalid stored data: {exc}') from exc
#         except Exception as exc:
#             raise StorageError(f'Could not load data from Supabase: {exc}') from exc
#
#     def save(self, data, expected_version):
#         # A copy avoids incrementing the caller's revision on failed saves.
#         outgoing = copy.deepcopy(data)
#         validate_data(outgoing)
#         try:
#             # Round-trip via JSON to validate JSON compatibility before writing.
#             outgoing = json.loads(encoded(outgoing))
#         except (TypeError, ValueError) as exc:
#             raise StorageError(f'Data cannot be serialized as JSON: {exc}') from exc
#
#         # expected_version=None only applies when the document does not exist.
#         # For existing documents the PostgreSQL function performs atomic CAS.
#         expected = None if expected_version is None else int(expected_version)
#         outgoing['revision'] = (expected if expected is not None else 0) + 1
#         try:
#             response = self.db.rpc('save_app_data', {
#                 'p_id': self.document_id,
#                 'p_expected_revision': expected,
#                 'p_content': outgoing,
#             }).execute()
#             if response.data is not True:
#                 raise StorageError('Data changed since this page loaded. Refresh and try again.')
#         except StorageError:
#             raise
#         except Exception as exc:
#             raise StorageError(f'Could not save data to Supabase: {exc}') from exc
#         # Maintain previous behavior: update the caller after confirmed success.
#         data['revision'] = outgoing['revision']
