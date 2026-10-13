#!/usr/bin/env python3
"""Preview/create tournaments and import uDisc workbooks in one atomic Supabase save."""
import argparse
from copy import deepcopy
from datetime import date, datetime
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

from import_players import load_store, normalized
from league.domain import find, new_id, profile, register_player, validate_data
from league.imports import read_export, preview_import

DEFAULT_FOLDER = Path('/Users/lukas/Downloads/Jahodna DG Liga')


def filename_metadata(path, layout_override=None):
    stem = Path(path).stem
    match = re.fullmatch(r'(.+)-(\d{4}-\d{2}-\d{2})', stem)
    if not match:
        raise ValueError('Filename must end with a YYYY-MM-DD date.')
    prefix, day = match.groups()
    day = date.fromisoformat(day).isoformat()
    words = prefix.split('-')
    markers = [w for w in words if w in ('cervena', 'zelena')]
    if len(markers) > 1:
        raise ValueError('Filename has multiple layout markers.')
    numbered = re.fullmatch(r'sobotnajsie-discgolfove-turnaje-(\d+)-turnaj', prefix)
    layout = markers[0] if markers else ('cervena' if numbered else None)
    if layout_override:
        if layout and layout != layout_override:
            raise ValueError('Override conflicts with the filename layout.')
        layout = layout_override
    if not layout:
        raise ValueError('Filename has no layout; supply --layout FILE=cervena or FILE=zelena.')
    if numbered:
        name = f'Sobotnajsie Discgolfove Turnaje ({int(numbered.group(1))}. turnaj)'
    else:
        name = ' '.join(w.capitalize() for w in words if w not in ('cervena', 'zelena'))
    return {'name': name, 'date': day, 'layout': layout}


def assignments(values):
    result = {}
    for value in values:
        key, separator, val = value.partition('=')
        if not separator or not key or not val or key in result:
            raise ValueError('Assignments must be unique KEY=VALUE pairs.')
        result[key] = val
    return result


def prepare_batch(data, files, leagues, overrides=None, usernames=None, unscored='error', skip_names=()):
    draft = deepcopy(data)
    validate_data(draft)
    overrides, usernames = overrides or {}, usernames or {}
    report = []
    for path in sorted(files):
        meta = filename_metadata(path, overrides.get(path.name))
        league_id = leagues.get(meta['date'][:4]) or leagues.get('*')
        if not league_id:
            raise ValueError(f'{path.name}: no league assigned for {meta["date"][:4]}.')
        find(draft, 'leagues', league_id)
        layouts = [x for x in draft['layouts'] if normalized(x['name']) == meta['layout']
                   and normalized(find(draft, 'courses', x['course_id'])['name']) == 'jahodna']
        if len(layouts) != 1:
            raise ValueError(f'{path.name}: expected one Jahodna / {meta["layout"]} layout.')
        layout = layouts[0]
        matches = [t for t in draft['tournaments'] if t['league_id'] == league_id
                   and t['date'] == meta['date'] and normalized(t['name']) == normalized(meta['name'])]
        if len(matches) > 1:
            raise ValueError(f'{path.name}: multiple existing tournaments match.')
        created = not matches
        t = matches[0] if matches else {
            'id': new_id(), 'name': meta['name'], 'date': meta['date'], 'league_id': league_id,
            'layout_id': layout['id'], 'num_rounds': 1, 'categories': list(draft['categories'])}
        if t['layout_id'] != layout['id'] or t['num_rounds'] != 1:
            raise ValueError(f'{path.name}: existing tournament has a different layout or round count.')
        if created:
            draft['tournaments'].append(t)
        frame = read_export(path.read_bytes(), path.name, sheet='Event results')
        required = ['username', 'name', 'round_total_score'] + [f'hole_{h["number"]}' for h in profile(layout, 'default')]
        if any(c not in frame for c in required):
            raise ValueError(f'{path.name}: missing required score columns.')
        players = {normalized(p['udisc']): p for p in draft['players'] if p['udisc'].strip()}
        complete_rows, skipped, registered, seen = [], [], [], set()
        for idx, row in frame.iterrows():
            if all(not str(v).strip() for v in row):
                continue
            row = row.copy()
            if normalized(str(row['name'])) in {normalized(n) for n in skip_names}:
                skipped.append(str(row['name']))
                continue
            if not str(row['username']).strip():
                row['username'] = usernames.get(str(row['name']).strip(), '')
            u = normalized(str(row['username']))
            if u not in players:
                raise ValueError(f'{path.name} row {idx + 2}: unknown/missing username for {row["name"]}.')
            player = players[u]
            if player['id'] in seen:
                raise ValueError(f'{path.name}: duplicate player {row["username"]}.')
            seen.add(player['id'])
            division = str(row.get('division', '')).strip()
            category = division if division in draft['categories'] else player['category']
            row['import_category'] = category
            holes = [str(row[f'hole_{h["number"]}']).strip() for h in profile(layout, category)]
            no_scores = all(v in ('', '-', 'DNF', 'DNS') for v in holes)
            if no_scores:
                if unscored == 'error':
                    raise ValueError(f'{path.name}: no hole scores for {row["name"]}; choose --unscored register or skip.')
                if unscored == 'register':
                    register_player(draft, t['id'], player['id'], category, player['handicap'])
                    registered.append(str(row['name']))
                else:
                    skipped.append(str(row['name']))
                continue
            complete_rows.append(row)
        count = identical = 0
        if complete_rows:
            import pandas as pd
            scored = pd.DataFrame(complete_rows).reset_index(drop=True)
            mapping = {'username': 'username', 'category': 'import_category', 'total': 'round_total_score',
                       'holes': {int(c[5:]): c for c in frame if re.fullmatch(r'hole_\d+', c)}}
            proposed, preview, errors = preview_import(draft, t['id'], scored, mapping, 1, layout_id=layout['id'])
            if errors:
                raise ValueError(f'{path.name}: ' + '; '.join(errors))
            for record in proposed['rounds']:
                if record['tournament_id'] != t['id']:
                    continue
                old = next((r for r in draft['rounds'] if r['tournament_id'] == t['id']
                            and r['player_id'] == record['player_id'] and r['round_number'] == record['round_number']), None)
                if old:
                    # Compare actual scores and category, preserve all original snapshots/IDs.
                    old_scores = [(h['number'], h['throws']) for h in old['holes']]
                    new_scores = [(h['number'], h['throws']) for h in record['holes']]
                    if old['total'] != record['total'] or old['category'] != record['category'] or old_scores != new_scores:
                        raise ValueError(f'{path.name}: existing scores differ; no records overwritten.')
                    identical += 1
                    continue
                draft['rounds'].append(record)
                entry = next(e for e in proposed['registrations'] if e['tournament_id'] == t['id'] and e['player_id'] == record['player_id'])
                register_player(draft, t['id'], record['player_id'], entry['category'], entry['handicap'])
                count += 1
        report.append({**meta, 'file': path.name, 'tournament_id': t['id'], 'created': created,
                       'rounds_added': count, 'identical_rounds': identical,
                       'registered_without_scores': registered, 'skipped': skipped})
    validate_data(draft)
    return draft, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', nargs='?', type=Path, default=DEFAULT_FOLDER)
    parser.add_argument('--league', action='append', default=[], help='YEAR=league-ID (or *=ID for all years). Required.')
    parser.add_argument('--create-league', action='append', default=[], help='YEAR=name for a new league; copies points rules from the first --league assignment.')
    parser.add_argument('--skip-name', action='append', default=[], help='Explicit full display name to skip in source workbooks.')
    parser.add_argument('--layout', action='append', default=[], help='filename.xlsx=cervena or zelena for missing markers.')
    parser.add_argument('--username', action='append', default=[], help='Full Name=existing-username for missing workbook usernames.')
    parser.add_argument('--unscored', choices=['error', 'register', 'skip'], default='error')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--preview-json', type=Path)
    parser.add_argument('--secrets', type=Path, default=Path(__file__).resolve().parent / '.streamlit/secrets.toml')
    parser.add_argument('--document-id', default='main')
    args = parser.parse_args(argv)
    if args.apply and args.preview_json:
        parser.error('--preview-json cannot be used with --apply')
    files = [p for p in args.folder.glob('*.xlsx') if not p.name.startswith('~$')]
    if not files:
        raise ValueError('No Excel workbooks found in the folder.')
    if args.preview_json:
        data = json.loads(args.preview_json.read_text(encoding='utf-8'))
        store, version = None, None
    else:
        store = load_store(args.secrets, args.document_id)
        data, version = store.load()
        if version is None:
            raise ValueError('Application document does not exist.')
    leagues = assignments(args.league)
    working = deepcopy(data)
    for year, name in assignments(args.create_league).items():
        if year in leagues:
            raise ValueError(f'League already assigned for {year}.')
        existing = [l for l in working['leagues'] if normalized(l['name']) == normalized(name)]
        if len(existing) > 1:
            raise ValueError(f'Multiple leagues named {name}.')
        if existing:
            league = existing[0]
        else:
            if not leagues:
                raise ValueError('Provide an existing --league assignment to copy points rules from.')
            template = find(working, 'leagues', next(iter(leagues.values())))
            league = {**deepcopy(template), 'id': new_id(), 'name': name}
            working['leagues'].append(league)
        leagues[year] = league['id']
        print(f'League {year}: {league["name"]}')
    draft, report = prepare_batch(working, files, leagues, assignments(args.layout), assignments(args.username), args.unscored, args.skip_name)
    for item in report:
        print(json.dumps(item, ensure_ascii=False))
    print(f'{len(report)} files; {sum(r["created"] for r in report)} new tournaments; {sum(r["rounds_added"] for r in report)} new rounds.')
    if args.apply and draft != data:
        backup_dir = Path(__file__).resolve().parent / 'data/backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(ZoneInfo('Europe/Bratislava')).strftime('%Y%m%d-%H%M%S-%f')
        backup = backup_dir / f'before-tournament-import-{stamp}.json'
        backup.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        store.save(draft, version)
        saved, _ = store.load()
        if saved != draft:
            raise ValueError('Saved data changed before read-back verification; reload and inspect before retrying.')
        print(f'Saved and verified revision {draft["revision"]}. Backup: {backup}')
    else:
        print('No changes needed.' if args.apply else 'Dry run only; pass --apply to save.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Import failed: {exc}', file=sys.stderr)
        sys.exit(1)
