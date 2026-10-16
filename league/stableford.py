"""Net Stableford with frozen event stroke indices and parallel handicap methods."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json

from .domain import find, rank_rows, whole_number

ALGORITHM = 'net-stableford-full-handicap-v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def enabled(data, league_id):
    league = find(data, 'leagues', league_id)
    return league.get('stableford_enabled', True)


def stablefords_current(data):
    """An existing formula marker alone does not guarantee every league is filled."""
    eligible = {t['id'] for t in data['tournaments'] if enabled(data, t['league_id'])}
    if eligible and data.get('stableford_version') != ALGORITHM:
        return False
    results = {(r['tournament_id'], r['player_id']): r for r in data.get('stableford_results', [])}
    return all(results.get((e['tournament_id'], e['player_id']), {}).get('calculation_version') == ALGORITHM
               for e in data.get('registrations', []) if e['tournament_id'] in eligible)


def hole_identity(layout, hole):
    # Unknown distances cannot identify a shared physical hole reliably.
    return digest([layout['course_id'], hole['par'], float(hole['length']),
                   None if hole['length'] else [layout['id'], hole['number']]])[:20]


def difficulty_rows(data, course_id):
    """Pool matching par/distance configurations across layouts, even if renumbered."""
    layouts = {l['id']: l for l in data['layouts'] if l['course_id'] == course_id}
    groups = {}
    for layout in layouts.values():
        for holes in layout['profiles'].values():
            for h in holes:
                key = hole_identity(layout, h)
                row = groups.setdefault(key, {'id': key, 'par': h['par'], 'length': h['length'],
                                               'holes': set(), 'scores': []})
                row['holes'].add(f"{layout['name']} {h['number']}")
    for r in data['rounds']:
        if r['layout_id'] not in layouts:
            continue
        layout = layouts[r['layout_id']]
        for h in r['holes']:
            key = hole_identity(layout, h)
            # Retain historical tee configurations, as well as today's layout.
            row = groups.setdefault(key, {'id': key, 'par': h['par'], 'length': h['length'],
                                           'holes': set(), 'scores': []})
            row['holes'].add(f"{layout['name']} {h['number']}")
            row['scores'].append(h['throws'] - h['par'])
    rows = []
    for row in groups.values():
        scores = row.pop('scores')
        row.update(average=sum(scores) / len(scores) if scores else None,
                   samples=len(scores), holes=' · '.join(sorted(row['holes'])))
        rows.append(row)
    rows.sort(key=lambda r: (r['average'] is None, -(r['average'] or 0), r['id']))
    return [{**r, 'priority': i} for i, r in enumerate(rows, 1)]


def strokes_received(handicap, stroke_index, hole_count=18):
    """Full handicap each round; negative handicaps return strokes easiest first."""
    if int(handicap) != handicap or not 1 <= stroke_index <= hole_count:
        raise ValueError('Invalid handicap or stroke index.')
    base, remainder = divmod(abs(int(handicap)), hole_count)
    extra = stroke_index <= remainder if handicap >= 0 else stroke_index > hole_count - remainder
    return (base + int(extra)) * (1 if handicap >= 0 else -1)


def hole_points(throws, par, strokes):
    return max(0, 2 + par + strokes - throws)


def calculate_stablefords(data):
    """Called after both historical handicap calculations; returns canonical state.

    Difficulty is captured on first calculation and reused. A changed score or
    historical handicap recalculates points, while later statistics do not move
    previously allocated strokes. Existing raw scores/handicaps are untouched.
    """
    layouts = {l['id']: l for l in data['layouts']}
    tournaments = {t['id']: t for t in data['tournaments']}
    target_ids = {t['id'] for t in data['tournaments'] if enabled(data, t['league_id'])}
    if not target_ids:
        return data
    courses = {c['id']: c for c in data['courses']}
    for cid in {layouts[tournaments[tid]['layout_id']]['course_id'] for tid in target_ids}:
        course = courses[cid]
        if 'stableford_difficulty' not in course:
            rows = difficulty_rows(data, cid)
            course['stableford_difficulty'] = {'created_at': datetime.now(timezone.utc).isoformat(),
                                               'rows': rows, 'version': digest(rows)}
    grouped = defaultdict(list)
    for r in data['rounds']:
        grouped[(r['tournament_id'], r['player_id'])].append(r)
    results = {(r['tournament_id'], r['player_id']): r for r in data['stableford_results']}
    for key, result in results.items():
        tid, pid = key
        if tid not in target_ids:
            continue
        t = tournaments[tid]
        rounds = sorted(grouped[key], key=lambda r: r['round_number'])
        ready = ({r['round_number'] for r in rounds} == set(range(1, t['num_rounds'] + 1))
                 and len(rounds) == t['num_rounds'] and all(r['holes'] for r in rounds))
        method_results = {}
        for method, prefix in [('legacy', ''), ('golf', 'golf_')]:
            total, details = 0, []
            valid = ready and all(not r.get(prefix + 'handicap_pending', True) for r in rounds)
            if valid:
                for r in rounds:
                    layout = layouts[r['layout_id']]
                    config = courses[layout['course_id']]['stableford_difficulty']
                    priorities = {h['id']: h['priority'] for h in config['rows']}
                    signature = digest([r['layout_id'], [(h['number'], h['par'], h['length']) for h in r['holes']]])
                    snapshots = t.setdefault('stableford_difficulty', {})
                    if signature not in snapshots:
                        ordered = sorted(r['holes'], key=lambda h: (priorities.get(hole_identity(layout, h), float('inf')), h['number']))
                        snapshots[signature] = {'source_version': config['version'], 'holes': [
                            {'number': h['number'], 'identity': hole_identity(layout, h), 'stroke_index': i}
                            for i, h in enumerate(ordered, 1)]}
                    indices = {h['number']: h['stroke_index'] for h in snapshots[signature]['holes']}
                    holes = []
                    for h in r['holes']:
                        strokes = strokes_received(r[prefix + 'handicap'], indices[h['number']], len(r['holes']))
                        points = hole_points(h['throws'], h['par'], strokes)
                        total += points
                        holes.append({'number': h['number'], 'stroke_index': indices[h['number']],
                                      'strokes': strokes, 'net_score': h['throws'] - strokes, 'points': points})
                    details.append({'round_id': r['id'], 'handicap': r[prefix + 'handicap'],
                                    'difficulty_snapshot': signature, 'holes': holes})
            method_results[method] = {'points': total if valid else None,
                                      'status': 'calculated' if valid else 'pending_inputs', 'rounds': details,
                                      'handicap_snapshot_id': rounds[0].get(prefix + 'handicap_snapshot_id') if rounds else None,
                                      'source_run_id': data[prefix + 'handicap_run']['id']}
        result.update(points=method_results['legacy']['points'], status=method_results['legacy']['status'],
                      calculation_version=ALGORITHM, methods=method_results)
    data['stableford_version'] = ALGORITHM
    return data


def project_stablefords(data, method):
    for result in data.get('stableford_results', []):
        if result.get('calculation_version') == ALGORITHM:
            chosen = result['methods'][method]
            result.update(points=chosen['points'], status=chosen['status'])
    return data


def tournament_standings(data, tid, category='All', by_category=True):
    players = {p['id']: p for p in data['players']}
    entries = {(e['tournament_id'], e['player_id']): e for e in data.get('registrations', [])}
    rows = []
    for result in data.get('stableford_results', []):
        if result['tournament_id'] != tid or result.get('status') != 'calculated':
            continue
        entry = entries[(tid, result['player_id'])]
        if category != 'All' and entry['category'] != category:
            continue
        p = players[result['player_id']]
        rows.append({'player_id': p['id'], 'Player': f"{p['first_name']} {p['last_name']}",
                     'Category': entry['category'], 'Stableford': result['points'],
                     'Handicap': entry['handicap']})
    rows.sort(key=lambda r: (-r['Stableford'], r['Player']))
    rank_rows(rows, 'Stableford', by_category=by_category)
    return rows


def league_standings(data, lid, category='All'):
    league = find(data, 'leagues', lid)
    standings = {}
    for t in data['tournaments']:
        if t['league_id'] != lid:
            continue
        rows = tournament_standings(data, t['id'], by_category=league['points_scope'] == 'category')
        for row in rows:
            group = row['Category'] if league['points_scope'] == 'category' else 'All'
            tied = [r for r in rows if r['Stableford'] == row['Stableford'] and (r['Category'] if league['points_scope'] == 'category' else 'All') == group]
            occupied = range(row['Place'], row['Place'] + (len(tied) if league['tie_mode'] == 'shared' else 1))
            points = whole_number(sum(league['points'][i-1] if i <= len(league['points']) else 0 for i in occupied) / len(occupied))
            key = (row['player_id'], row['Category'])
            entry = standings.setdefault(key, {**row, 'Points': 0, 'Tournaments': 0,
                                                'Stableford': 0, 'Current handicap': find(data, 'players', row['player_id'])['handicap']})
            entry['Points'] += points
            entry['Stableford'] += row['Stableford']
            entry['Tournaments'] += 1
    rows = sorted((r for r in standings.values() if category == 'All' or r['Category'] == category), key=lambda r: (-r['Points'], r['Player']))
    for r in rows:
        r.pop('Handicap', None)
    rank_rows(rows, 'Points')
    return rows
