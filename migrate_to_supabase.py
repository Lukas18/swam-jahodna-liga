#!/usr/bin/env python3
"""One-time migration of league.json into Supabase public.app_data JSONB storage.

Install: pip install supabase
Set SUPABASE_URL and SUPABASE_KEY in the environment (server-side secret key).
Run: python migrate_to_supabase.py league.json
Use --overwrite only to intentionally replace an existing database document.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

EXPECTED_LISTS = ('categories', 'players', 'courses', 'layouts', 'leagues',
                  'tournaments', 'rounds', 'registrations')


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('Root must be a JSON object')
    for name in EXPECTED_LISTS:
        if not isinstance(data.get(name), list):
            raise ValueError(f'Missing or invalid list: {name}')
    for name in ('schema_version', 'revision'):
        if not isinstance(data.get(name), int):
            raise ValueError(f'Missing or invalid integer: {name}')
    for name in ('players', 'courses', 'layouts', 'leagues', 'tournaments', 'rounds'):
        ids = [item.get('id') for item in data[name]]
        if any(not isinstance(x, str) or not x for x in ids):
            raise ValueError(f'Invalid ID in {name}')
        if len(ids) != len(set(ids)):
            raise ValueError(f'Duplicate IDs in {name}')
    canonical_bytes(data)  # reject NaN / Infinity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', nargs='?', default='league.json', type=Path)
    parser.add_argument('--document-id', default='main')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()

    with args.file.open('r', encoding='utf-8') as f:
        data = json.load(f, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(f'Invalid JSON constant: {v}')))
    validate(data)
    digest = hashlib.sha256(canonical_bytes(data)).hexdigest()
    print(f'Source: {args.file} | SHA-256: {digest}')
    for name in EXPECTED_LISTS:
        print(f'  {name}: {len(data[name])}')

    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    if not url or not key:
        raise RuntimeError('Set SUPABASE_URL and SUPABASE_KEY environment variables')

    from supabase import create_client
    db = create_client(url, key)
    table = db.table('app_data')
    existing = table.select('id').eq('id', args.document_id).limit(1).execute().data
    if existing and not args.overwrite:
        raise RuntimeError(f'Document {args.document_id!r} already exists. '
                           'No changes made. Pass --overwrite to replace it.')

    row = {'id': args.document_id, 'content': data}
    if existing:
        table.update({'content': data}).eq('id', args.document_id).execute()
        print('Updated existing document.')
    else:
        table.insert(row).execute()
        print('Inserted new document.')

    response = table.select('content').eq('id', args.document_id).single().execute()
    uploaded = response.data['content']
    if canonical_bytes(uploaded) != canonical_bytes(data):
        raise RuntimeError('Verification FAILED: uploaded content differs from source')
    print('SUCCESS: Supabase JSONB document matches the source exactly.')
    print(f'Document ID: {args.document_id} | revision: {data["revision"]}')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
