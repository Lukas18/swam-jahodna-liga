"""One-time read-only migration; never overwrite an existing league JSON file."""
import sqlite3
from pathlib import Path
from league.domain import empty_data, new_id, validate_data
from league.storage import encoded


def migrate(source, target):
    target = Path(target)
    if target.exists():
        raise ValueError('Destination already exists; migration will not overwrite it.')
    db = sqlite3.connect(f'file:{Path(source).resolve()}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    data = empty_data()
    course_ids, layout_ids, player_ids, tournament_ids = {}, {}, {}, {}
    for c in db.execute('SELECT * FROM course'):
        cid, lid = new_id(), new_id()
        course_ids[c['id']], layout_ids[c['id']] = cid, lid
        data['courses'].append({'id': cid, 'name': c['name'], 'description': c['description'] or ''})
        holes = list(db.execute('SELECT * FROM hole WHERE course_id=? ORDER BY number', (c['id'],)))
        default = [{'number': h['number'], 'par': h['default_par'], 'length': 0} for h in holes]
        profiles = {'default': default}
        for cat in data['categories']:
            pars = {r['hole_id']: r['par'] for r in db.execute('SELECT * FROM hole_category_par WHERE category=?', (cat,))}
            if any(h['id'] in pars for h in holes):
                profiles[cat] = [{'number': h['number'], 'par': pars.get(h['id'], h['default_par']), 'length': 0} for h in holes]
        data['layouts'].append({'id': lid, 'course_id': cid, 'name': 'Original layout', 'profiles': profiles})
    for p in db.execute('SELECT * FROM player'):
        pid = new_id()
        player_ids[p['id']] = pid
        if p['category'] not in data['categories']:
            data['categories'].append(p['category'])
        data['players'].append({'id': pid, 'first_name': p['first_name'], 'last_name': p['last_name'],
                                'category': p['category'], 'handicap': p['handicap'] or 0, 'udisc': ''})
    league_id = new_id()
    data['leagues'].append({'id': league_id, 'name': 'Local league', 'points': [25, 20, 16, 13, 11, 10, 9, 8, 7, 6],
                            'points_scope': 'category', 'tie_mode': 'shared'})
    for t in db.execute('SELECT * FROM event'):
        tid = new_id()
        tournament_ids[t['id']] = tid
        cats = [c.strip() for c in (t['categories'] or '').split(',') if c.strip()] or data['categories'][:]
        for cat in cats:
            if cat not in data['categories']:
                data['categories'].append(cat)
        data['tournaments'].append({'id': tid, 'name': t['name'], 'date': t['date'], 'league_id': league_id,
                                    'layout_id': layout_ids[t['course_id']], 'num_rounds': t['num_rounds'], 'categories': cats})
    from league.domain import add_round, register_player
    for ep in db.execute('SELECT * FROM event_player'):
        register_player(data, tournament_ids[ep['event_id']], player_ids[ep['player_id']], ep['category'], ep['handicap'] or 0)
    for r in db.execute('SELECT * FROM round'):
        ep = db.execute('SELECT * FROM event_player WHERE id=?', (r['player_id'],)).fetchone()
        scores = {s['hole_number']: s['throws'] for s in db.execute('SELECT * FROM hole_score WHERE round_id=?', (r['id'],))}
        add_round(data, tournament_ids[r['event_id']], player_ids[ep['player_id']], r['round_number'], ep['category'], ep['handicap'] or 0, scores)
    db.close()
    validate_data(data)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encoded(data))
    return data


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='instance/discgolf.db')
    parser.add_argument('--target', default='data/league.json')
    args = parser.parse_args()
    result = migrate(args.source, args.target)
    print(f"Migrated {len(result['courses'])} courses, {len(result['players'])} players, {len(result['tournaments'])} tournaments.")
