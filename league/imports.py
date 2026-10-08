"""Explicit column mapping and atomic preview for uDisc Excel/CSV exports."""
from copy import deepcopy
from io import BytesIO
import pandas as pd
from .domain import add_round, find, username, profile, integer, finite_number, tournament_entries


def read_export(content, filename, sheet=0, header_row=1):
    stream = BytesIO(content)
    if filename.lower().endswith('.csv'):
        frame = pd.read_csv(stream, sep=None, engine='python', header=header_row-1, dtype=str, keep_default_na=False)
    else:
        frame = pd.read_excel(stream, sheet_name=sheet, header=header_row-1, dtype=str, keep_default_na=False, engine='openpyxl')
    frame.columns = [str(c).strip() for c in frame.columns]
    return frame.fillna('')


def preview_import(data, tournament_id, frame, mapping, round_number, default_category=None, layout_id=None):
    """Return a separate proposed state. Any row error blocks the entire save."""
    draft = deepcopy(data)
    t = find(draft, 'tournaments', tournament_id)
    if layout_id is not None:
        if layout_id != t['layout_id'] and any(r['tournament_id'] == tournament_id for r in data['rounds']):
            return draft, [], ['A tournament with recorded scores must keep its existing layout.']
        try:
            find(data, 'layouts', layout_id)
        except StopIteration:
            return draft, [], ['Choose a valid import layout.']
        t['layout_id'] = layout_id
    layout = find(draft, 'layouts', t['layout_id'])
    users = {username(p['udisc']): p for p in data['players'] if p['udisc'].strip()}
    entries = {e['player_id']: e for e in tournament_entries(data, tournament_id)}
    preview, errors, seen = [], [], set()
    for idx, row in frame.iterrows():
        if all(str(v).strip() == '' for v in row):
            continue
        label = f'Row {idx + 1}'
        try:
            u = str(row[mapping['username']]).strip()
            if username(u) not in users:
                raise ValueError(f'Unknown uDisc username: {u or "(blank)"}. Add it to a player first.')
            p = users[username(u)]
            defaults = entries.get(p['id'], p)
            cat = str(row[mapping['category']]).strip() if mapping.get('category') else (default_category or defaults['category'])
            hcp = finite_number(row[mapping['handicap']], 'Handicap') if mapping.get('handicap') else defaults['handicap']
            rnd = integer(row[mapping['round']], 'Round', 1, t['num_rounds']) if mapping.get('round') else round_number
            key = (p['id'], rnd)
            if key in seen:
                raise ValueError('Duplicate player and round in this file.')
            seen.add(key)
            scores = None
            if mapping.get('holes'):
                scores = {}
                for h in profile(layout, cat):
                    col = mapping['holes'].get(h['number'])
                    if not col:
                        raise ValueError(f"Map a score column for hole {h['number']}.")
                    scores[h['number']] = row[col]
            total = row[mapping['total']] if mapping.get('total') else None
            # Relative scores from the export are ignored. Par comes from the
            # selected layout's category profile; throw totals are still checked.
            record = add_round(draft, tournament_id, p['id'], rnd, cat, hcp, scores, total)
            replaced = any(r['tournament_id'] == tournament_id and r['player_id'] == p['id'] and r['round_number'] == rnd for r in data['rounds'])
            preview.append({'Player': f"{p['first_name']} {p['last_name']}".strip(), 'uDisc': u, 'Category': cat,
                            'Round': rnd, 'Layout': layout['name'], 'Throws': record['total'], 'Par': record['par'],
                            'Score relative to par': record['total'] - record['par'],
                            'Hole scores': len(record['holes']), 'Action': 'Replace' if replaced else 'Add'})
        except (ValueError, KeyError, StopIteration) as exc:
            errors.append(f'{label}: {exc}')
    if not preview and not errors:
        errors.append('No result rows found.')
    return draft, preview, errors
