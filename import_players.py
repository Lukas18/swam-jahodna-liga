#!/usr/bin/env python3
"""Create missing league players from a UTF-8 username/name CSV in Supabase.

Dry run by default. Pass --apply to save all additions in one version-checked update.
"""
import argparse
from copy import deepcopy
import csv
import os
from pathlib import Path
import sys
import unicodedata

from league.domain import save_player, validate_data

DEFAULT_CSV = Path('/Users/lukas/Downloads/Jahodna DG Liga/unique_pairs.csv')


def normalized(value):
    return unicodedata.normalize('NFC', ' '.join(value.split())).casefold()


def read_pairs(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as source:
        sample = source.read(8192)
        source.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=';,\t')
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(source, dialect=dialect)
        if not reader.fieldnames:
            raise ValueError('CSV is empty; expected username and name headers.')
        reader.fieldnames = [h.strip().casefold() for h in reader.fieldnames]
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('CSV has duplicate headers.')
        if not {'username', 'name'}.issubset(reader.fieldnames):
            raise ValueError('CSV must contain username and name columns.')
        pairs = []
        for row in reader:
            if None in row:
                raise ValueError(f'CSV line {reader.line_num}: too many fields.')
            if not any((value or '').strip() for value in row.values()):
                continue
            user = (row['username'] or '').strip()
            name = ' '.join((row['name'] or '').split())
            if not user or not name:
                raise ValueError(f'CSV line {reader.line_num}: username and name are required.')
            pairs.append((user, name))
        return pairs


def prepare_players(data, pairs, default_category='MPO'):
    """Return a validated draft plus added/skipped rows; never change existing players."""
    draft = deepcopy(data)
    validate_data(draft)
    if default_category not in draft['categories']:
        raise ValueError(f'Category {default_category!r} is not configured in the app.')
    users = {normalized(p['udisc']) for p in draft['players'] if p['udisc'].strip()}
    names = {normalized(p['first_name'] + ' ' + p['last_name']) for p in draft['players']}
    added, skipped = [], []
    for user, name in pairs:
        if normalized(user) in users:
            skipped.append((user, name, 'username already exists'))
            continue
        if normalized(name) in names:
            skipped.append((user, name, 'name already exists; existing player left unchanged'))
            continue
        # Use the final word for classification, including surname-only CSV names.
        parts = name.rsplit(' ', 1)
        first, last = (parts[0], parts[1]) if len(parts) == 2 else (name, '')
        category = 'FPO' if normalized(parts[-1]).endswith(('ova', 'ová')) else default_category
        player = save_player(draft, None, first, last, category, 0, user)
        added.append(player)
        users.add(normalized(user))
        names.add(normalized(name))
    validate_data(draft)
    return draft, added, skipped


def load_store(secrets_path, document_id):
    # Import lazily: CSV planning and its tests do not require a Supabase client.
    from league.storage import Store
    config = {}
    if secrets_path.is_file():
        import toml
        config = toml.loads(secrets_path.read_text(encoding='utf-8'))
    section = config.get('supabase', {})
    url = os.environ.get('SUPABASE_URL') or config.get('SUPABASE_URL') or section.get('url')
    key = os.environ.get('SUPABASE_KEY') or config.get('SUPABASE_KEY') or section.get('key')
    if not url or not key:
        raise ValueError('Set SUPABASE_URL and SUPABASE_KEY in the environment or secrets file.')
    return Store(supabase={'url': url, 'key': key, 'document_id': document_id})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', nargs='?', type=Path, default=DEFAULT_CSV)
    parser.add_argument('--apply', action='store_true', help='Save missing players to Supabase.')
    parser.add_argument('--default-category', default='MPO', help='Category for other new players (default: MPO).')
    parser.add_argument('--document-id', default='main')
    parser.add_argument('--secrets', type=Path, default=Path(__file__).resolve().parent / '.streamlit/secrets.toml')
    parser.add_argument('--preview-json', type=Path, help='Preview against a local JSON snapshot instead of Supabase; cannot be used with --apply.')
    args = parser.parse_args(argv)
    if args.apply and args.preview_json:
        parser.error('--preview-json cannot be used with --apply')
    pairs = read_pairs(args.csv)
    if args.preview_json:
        import json
        data = json.loads(args.preview_json.read_text(encoding='utf-8'))
        store, version = None, None
    else:
        store = load_store(args.secrets, args.document_id)
        data, version = store.load()
        if version is None:
            raise ValueError('App document does not exist. Import the application data first.')
    draft, added, skipped = prepare_players(data, pairs, args.default_category)
    for player in added:
        print(f"ADD {player['first_name']} {player['last_name']} | {player['udisc']} | {player['category']} | HCP 0")
    for user, name, reason in skipped:
        print(f'SKIP {name} | {user} | {reason}')
    print(f'{len(pairs)} CSV rows: {len(added)} additions, {len(skipped)} skipped.')
    if args.apply and added:
        store.save(draft, version)
        print(f'Saved {len(added)} players to Supabase (revision {draft["revision"]}).')
    elif args.apply:
        print('No changes needed; no save performed.')
    else:
        print('Dry run only. Run with --apply to save against the current Supabase data.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'Import failed: {exc}', file=sys.stderr)
        sys.exit(1)
