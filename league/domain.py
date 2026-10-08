"""Framework-independent league rules. Scores snapshot the layout at recording time."""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import math
import uuid


def new_id():
    return uuid.uuid4().hex


def empty_data():
    return {'schema_version': 1, 'revision': 0, 'categories': ['MPO', 'FPO', 'MA3'],
            'settings': {'site_title': 'SWAM Jahodna liga', 'active_league_id': None},
            'registrations': [], 'players': [], 'courses': [], 'layouts': [], 'leagues': [], 'tournaments': [], 'rounds': []}


def whole_number(value):
    """Nearest integer, with half points rounded away from zero."""
    return int(Decimal(str(finite_number(value, 'Score'))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def tournament_entries(data, tournament_id):
    entries = {e['player_id']: deepcopy(e) for e in data.get('registrations', []) if e['tournament_id'] == tournament_id}
    # Older backups have scores but no explicit registrations.
    for r in data['rounds']:
        if r['tournament_id'] == tournament_id and r['player_id'] not in entries:
            entries[r['player_id']] = {'tournament_id': tournament_id, 'player_id': r['player_id'],
                                       'category': r['category'], 'handicap': r['handicap']}
    return list(entries.values())


def register_player(data, tournament_id, player_id, category=None, handicap=None):
    t = find(data, 'tournaments', tournament_id)
    p = find(data, 'players', player_id)
    category = category or p['category']
    handicap = finite_number(p['handicap'] if handicap is None else handicap, 'Handicap')
    if category not in t['categories']:
        raise ValueError('Category is not enabled for this tournament.')
    scored = [r for r in data['rounds'] if r['tournament_id'] == tournament_id and r['player_id'] == player_id]
    if any(r['category'] != category or r['handicap'] != handicap for r in scored):
        raise ValueError('Category and handicap cannot change while this player has tournament scores.')
    entry = {'tournament_id': tournament_id, 'player_id': player_id, 'category': category, 'handicap': handicap}
    data['registrations'] = [e for e in data.get('registrations', []) if not (e['tournament_id'] == tournament_id and e['player_id'] == player_id)] + [entry]
    return entry


def score_grid(data, tournament_id, round_number, category):
    """Rows and per-player hole snapshots; unplayed holes start blank."""
    t = find(data, 'tournaments', tournament_id)
    layout = find(data, 'layouts', t['layout_id'])
    rows, snapshots = [], {}
    entries = [e for e in tournament_entries(data, tournament_id) if e['category'] == category]
    entries.sort(key=lambda e: (find(data, 'players', e['player_id'])['last_name'], find(data, 'players', e['player_id'])['first_name']))
    for e in entries:
        p = find(data, 'players', e['player_id'])
        existing = next((r for r in data['rounds'] if r['tournament_id'] == tournament_id and r['player_id'] == p['id'] and r['round_number'] == round_number), None)
        holes = deepcopy(existing['holes']) if existing and existing['holes'] else deepcopy(profile(layout, category))
        snapshots[p['id']] = holes
        row = {'player_id': p['id'], 'Save': False, 'Player': f"{p['first_name']} {p['last_name']}", 'Handicap': e['handicap'],
               'Status': 'Totals only' if existing and not existing['holes'] else 'Recorded' if existing else 'Not recorded'}
        row.update({f"H{h['number']}": h.get('throws') for h in holes})
        rows.append(row)
    return rows, snapshots


def save_score_grid(data, tournament_id, round_number, category, rows):
    """Validate every selected row on a copy before returning an atomic batch."""
    draft = deepcopy(data)
    entries = {e['player_id']: e for e in tournament_entries(data, tournament_id) if e['category'] == category}
    _, snapshots = score_grid(data, tournament_id, round_number, category)
    selected = [row for row in rows if row.get('Save')]
    if not selected:
        raise ValueError('Select Save for at least one player row.')
    seen = set()
    t = find(data, 'tournaments', tournament_id)
    for row in selected:
        pid = row['player_id']
        if pid not in entries or pid in seen:
            raise ValueError('Unknown or duplicate player in score grid.')
        seen.add(pid)
        p = find(data, 'players', pid)
        try:
            holes = snapshots[pid]
            scores = {h['number']: integer(row.get(f"H{h['number']}"), f"Hole {h['number']} score", 1, 100) for h in holes}
            original = deepcopy(find(draft, 'layouts', t['layout_id'])['profiles'])
            find(draft, 'layouts', t['layout_id'])['profiles'][category] = [dict(number=h['number'], par=h['par'], length=h['length']) for h in holes]
            add_round(draft, tournament_id, pid, round_number, category, entries[pid]['handicap'], scores)
            find(draft, 'layouts', t['layout_id'])['profiles'] = original
        except ValueError as exc:
            raise ValueError(f"{p['first_name']} {p['last_name']}: {exc}") from None
    return draft


def find(data, collection, item_id):
    return next(x for x in data[collection] if x['id'] == item_id)


def username(value):
    return str(value).strip().casefold()


def finite_number(value, label):
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'{label} must be a number.') from None
    if not math.isfinite(result):
        raise ValueError(f'{label} must be finite.')
    return result


def integer(value, label, minimum=1, maximum=None):
    number = finite_number(value, label)
    if not number.is_integer() or number < minimum or (maximum is not None and number > maximum):
        raise ValueError(f'{label} must be a whole number from {minimum}' + (f' to {maximum}.' if maximum else '.'))
    return int(number)


def validate_holes(holes):
    if not holes:
        raise ValueError('A layout needs at least one hole.')
    numbers = set()
    output = []
    for h in holes:
        n = integer(h['number'], 'Hole number', 1, 99)
        if n in numbers:
            raise ValueError(f'Hole {n} is listed twice.')
        numbers.add(n)
        output.append({'number': n, 'par': integer(h['par'], 'Par', 1, 10),
                       'length': finite_number(h.get('length', 0), 'Length')})
        if output[-1]['length'] < 0:
            raise ValueError('Length cannot be negative.')
    return sorted(output, key=lambda h: h['number'])


def profile(layout, category):
    return layout['profiles'].get(category, layout['profiles']['default'])


def save_player(data, player_id, first, last, category, handicap, udisc):
    if not first.strip():
        raise ValueError('First name is required.')
    if category not in data['categories']:
        raise ValueError('Choose an active category.')
    if udisc.strip() and any(username(p['udisc']) == username(udisc) and p['id'] != player_id for p in data['players']):
        raise ValueError('This uDisc username already belongs to another player.')
    p = {'id': player_id or new_id(), 'first_name': first.strip(), 'last_name': last.strip(),
         'category': category, 'handicap': finite_number(handicap, 'Handicap'), 'udisc': udisc.strip()}
    data['players'] = [x for x in data['players'] if x['id'] != p['id']] + [p]
    return p


def add_round(data, tournament_id, player_id, round_number, category, handicap, throws=None, total=None):
    tournament = find(data, 'tournaments', tournament_id)
    find(data, 'players', player_id)
    if category not in tournament['categories']:
        raise ValueError('Category is not enabled for this tournament.')
    round_number = integer(round_number, 'Round', 1, tournament['num_rounds'])
    layout = find(data, 'layouts', tournament['layout_id'])
    holes = deepcopy(profile(layout, category))
    handicap = finite_number(handicap, 'Handicap')
    entry = next((e for e in tournament_entries(data, tournament_id) if e['player_id'] == player_id), None)
    if entry and (entry['category'] != category or entry['handicap'] != handicap):
        raise ValueError('Use this player’s registered category and handicap.')
    # An event entry has one category and handicap across all its rounds.
    other = [r for r in data['rounds'] if r['tournament_id'] == tournament_id and r['player_id'] == player_id and r['round_number'] != round_number]
    if any(r['category'] != category or r['handicap'] != handicap for r in other):
        raise ValueError('Use the same category and handicap as this player’s other tournament rounds.')
    if throws is not None:
        expected = {h['number'] for h in holes}
        if set(throws) != expected:
            raise ValueError('Provide scores for exactly the holes in this category’s layout.')
        for h in holes:
            h['throws'] = integer(throws[h['number']], f"Hole {h['number']} score", 1, 100)
        computed = sum(h['throws'] for h in holes)
        if total is not None and integer(total, 'Total', 1) != computed:
            raise ValueError('Total does not match the sum of hole scores.')
        total = computed
    elif total is not None:
        total = integer(total, 'Total', len(holes))
        holes = []  # Totals-only imports do not invent hole statistics.
    else:
        raise ValueError('Provide hole scores or an absolute total number of throws.')
    r = {'id': new_id(), 'tournament_id': tournament_id, 'player_id': player_id,
         'layout_id': layout['id'], 'round_number': round_number, 'category': category,
         'handicap': handicap, 'total': total, 'par': sum(h['par'] for h in profile(layout, category)),
         'holes': holes, 'recorded_at': datetime.now(timezone.utc).isoformat()}
    register_player(data, tournament_id, player_id, category, handicap)
    data['rounds'] = [x for x in data['rounds'] if not (x['tournament_id'] == tournament_id and x['player_id'] == player_id and x['round_number'] == round_number)] + [r]
    return r


def tournament_results(data, tournament_id, category='All', metric='to_par', complete_only=False, rank_within_category=True):
    t = find(data, 'tournaments', tournament_id)
    grouped = defaultdict(list)
    for r in data['rounds']:
        if r['tournament_id'] == tournament_id and (category == 'All' or r['category'] == category):
            grouped[r['player_id']].append(r)
    results = []
    for pid, rounds in grouped.items():
        if complete_only and len(rounds) != t['num_rounds']:
            continue
        player = find(data, 'players', pid)
        total, par = sum(r['total'] for r in rounds), sum(r['par'] for r in rounds)
        results.append({'player_id': pid, 'Player': f"{player['first_name']} {player['last_name']}",
                        'Category': rounds[0]['category'], 'Rounds': len(rounds), 'Throws': total,
                        '+/− par': total - par, 'HCP adjusted': whole_number(total - par - sum(r['handicap'] for r in rounds)),
                        'Complete': len(rounds) == t['num_rounds']})
    key = {'raw': 'Throws', 'to_par': '+/− par', 'handicap': 'HCP adjusted'}[metric]
    results.sort(key=lambda r: (r[key], r['Player']))
    rank_rows(results, key, by_category=rank_within_category)
    return results


def rank_rows(rows, key, by_category=True):
    # The list stays sorted across categories, but Place belongs to a category.
    counts, previous, places = {}, {}, {}
    for row in rows:
        group = row['Category'] if by_category else 'All'
        counts[group] = counts.get(group, 0) + 1
        if group not in previous or row[key] != previous[group]:
            places[group] = counts[group]
        row['Place'] = places[group]
        previous[group] = row[key]


def place_labels(rows):
    """Display competition ranks with T for category ties; retain numeric rule data."""
    counts = Counter((r.get('Category', 'All'), r['Place']) for r in rows)
    return [('T' if counts[(r.get('Category', 'All'), r['Place'])] > 1 else '') + str(r['Place']) for r in rows]


def resize_holes(holes, count):
    count = integer(count, 'Number of holes', 1, 99)
    resized = deepcopy(holes[:count])
    numbers = {h['number'] for h in resized}
    for n in range(1, 100):
        if len(resized) == count:
            break
        if n not in numbers:
            resized.append({'number': n, 'par': 3, 'length': 0})
            numbers.add(n)
    return sorted(resized, key=lambda h: h['number'])


def award_points(rows, points, metric, tie_mode='shared'):
    rows = deepcopy(rows)
    key = {'raw': 'Throws', 'to_par': '+/− par', 'handicap': 'HCP adjusted'}[metric]
    for row in rows:
        tied = [x for x in rows if x[key] == row[key]]
        place = row['Place']
        if tie_mode == 'shared':
            row['Points'] = whole_number(sum(whole_number(points[i-1]) if i <= len(points) else 0 for i in range(place, place + len(tied))) / len(tied))
        else:
            row['Points'] = whole_number(points[place-1]) if place <= len(points) else 0
    return rows


def league_results(data, league_id, category='All', metric=None):
    league = find(data, 'leagues', league_id)
    metric = metric or 'to_par'
    standings = {}
    for t in data['tournaments']:
        if t['league_id'] != league_id:
            continue
        groups = t['categories'] if league['points_scope'] == 'category' else ['All']
        for group in groups:
            rows = tournament_results(data, t['id'], group, metric, complete_only=True,
                                      rank_within_category=league['points_scope'] == 'category')
            for row in award_points(rows, league['points'], metric, league['tie_mode']):
                if category != 'All' and row['Category'] != category:
                    continue
                key = (row['player_id'], row['Category'])
                if key not in standings:
                    standings[key] = {'player_id': row['player_id'], 'Player': row['Player'], 'Category': row['Category'], 'Tournaments': 0,
                                      'Points': 0, 'Throws': 0, '+/− par': 0, 'HCP adjusted': 0}
                entry = standings[key]
                entry['Tournaments'] += 1
                for column in ['Points', 'Throws', '+/− par', 'HCP adjusted']:
                    entry[column] += row[column]
    rows = sorted(standings.values(), key=lambda r: (-r['Points'], r['Player']))
    rank_rows(rows, 'Points')
    return rows


OUTCOMES = ['Ace', 'Albatross or better', 'Eagle', 'Birdie', 'Par', 'Bogey', 'Double bogey', 'Triple bogey or worse']


def outcome(throws, par):
    if throws == 1:
        return 'Ace'
    diff = throws - par
    if diff <= -3:
        return OUTCOMES[1]
    return {-2: 'Eagle', -1: 'Birdie', 0: 'Par', 1: 'Bogey', 2: 'Double bogey'}.get(diff, OUTCOMES[-1])


def hole_stats(data, layout_id, category):
    grouped = defaultdict(list)
    for r in data['rounds']:
        if r['layout_id'] == layout_id and r['category'] == category:
            for h in r['holes']:
                # Different historical pars/lengths are different tee configurations.
                grouped[(h['number'], h['par'], h['length'])].append(h['throws'])
    rows = []
    for (number, par, length), throws in sorted(grouped.items()):
        row = {'Hole': number, 'Par': par, 'Length (m)': length, 'Scores': len(throws),
               'Average throws': sum(throws)/len(throws), 'Average +/− par': sum(throws)/len(throws)-par}
        for label in OUTCOMES:
            row[label + ' %'] = 100 * sum(outcome(s, par) == label for s in throws)/len(throws)
        rows.append(row)
    return rows


def site_settings(data):
    settings = data.get('settings', {})
    active = settings.get('active_league_id')
    leagues = data['leagues']
    return {'site_title': settings.get('site_title', 'SWAM Jahodna liga'),
            'active_league_id': active if any(x['id'] == active for x in leagues) else (leagues[0]['id'] if leagues else None)}


def home_standings(data, league_id, metric='to_par'):
    """Attendance counts events with a recorded round, including incomplete events."""
    points = {(r['player_id'], r['Category']): r['Points'] for r in league_results(data, league_id, metric=metric)}
    events = {t['id'] for t in data['tournaments'] if t['league_id'] == league_id}
    attended = defaultdict(set)
    for r in data['rounds']:
        if r['tournament_id'] in events:
            attended[(r['player_id'], r['category'])].add(r['tournament_id'])
    rows = []
    for (pid, category), tournaments in attended.items():
        player = find(data, 'players', pid)
        rows.append({'player_id': pid, 'Player': player['first_name'] + ' ' + player['last_name'],
                     'Category': category, 'Points': points.get((pid, category), 0), 'Tournaments': len(tournaments)})
    rows.sort(key=lambda r: (-r['Points'], r['Player']))
    rank_rows(rows, 'Points')
    return rows


def validate_data(data):
    """Validate restored files before accepting any persistent replacement."""
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('Unsupported backup format.')
    for collection in ['categories', 'players', 'courses', 'layouts', 'leagues', 'tournaments', 'rounds']:
        if not isinstance(data.get(collection), list):
            raise ValueError(f'Missing or invalid {collection}.')
    cats = data['categories']
    if not cats or any(not isinstance(c, str) or not c.strip() for c in cats) or len(set(cats)) != len(cats):
        raise ValueError('Categories must be unique, non-empty names.')
    ids = {}
    for collection in ['players', 'courses', 'layouts', 'leagues', 'tournaments', 'rounds']:
        values = data[collection]
        ids[collection] = {x['id'] for x in values}
        if len(ids[collection]) != len(values):
            raise ValueError(f'Duplicate IDs in {collection}.')
    settings = data.get('settings', {})
    if not isinstance(settings, dict):
        raise ValueError('Invalid application settings.')
    title = settings.get('site_title', 'SWAM Jahodna liga')
    if not isinstance(title, str) or not title.strip() or len(title) > 100:
        raise ValueError('Application title must contain 1 to 100 characters.')
    if settings.get('active_league_id') is not None and settings['active_league_id'] not in ids['leagues']:
        raise ValueError('Unknown active league.')
    users = set()
    for p in data['players']:
        if not p['first_name'].strip() or not isinstance(p['last_name'], str) or p['category'] not in cats:
            raise ValueError('Invalid player name or category.')
        finite_number(p['handicap'], 'Handicap')
        u = username(p['udisc'])
        if u and u in users:
            raise ValueError('Duplicate uDisc username.')
        users.add(u)
    for c in data['courses']:
        if not c['name'].strip():
            raise ValueError('Course name is required.')
    for layout in data['layouts']:
        if layout['course_id'] not in ids['courses'] or not layout['name'].strip() or 'default' not in layout['profiles']:
            raise ValueError('Invalid layout.')
        for cat, holes in layout['profiles'].items():
            if cat != 'default' and cat not in cats:
                raise ValueError('Unknown layout category.')
            validate_holes(holes)
    for league in data['leagues']:
        if not league['name'].strip() or not league['points']:
            raise ValueError('League name and placement points are required.')
        if league['points_scope'] not in ['category', 'overall'] or league['tie_mode'] not in ['shared', 'same']:
            raise ValueError('Invalid league scoring settings.')
        if any(finite_number(p, 'Points') < 0 for p in league['points']):
            raise ValueError('Points cannot be negative.')
    for t in data['tournaments']:
        if t['league_id'] not in ids['leagues'] or t['layout_id'] not in ids['layouts'] or not t['name'].strip():
            raise ValueError('Invalid tournament links or name.')
        datetime.strptime(t['date'], '%Y-%m-%d')
        integer(t['num_rounds'], 'Number of rounds', 1, 20)
        if not t['categories'] or any(c not in cats for c in t['categories']) or len(set(t['categories'])) != len(t['categories']):
            raise ValueError('Invalid tournament categories.')
    if not isinstance(data.get('registrations', []), list):
        raise ValueError('Invalid tournament registrations.')
    registered = {}
    for e in data.get('registrations', []):
        if e['tournament_id'] not in ids['tournaments'] or e['player_id'] not in ids['players']:
            raise ValueError('Invalid tournament registration links.')
        t = find(data, 'tournaments', e['tournament_id'])
        key = (e['tournament_id'], e['player_id'])
        if e['category'] not in t['categories'] or key in registered:
            raise ValueError('Invalid category or duplicate tournament registration.')
        registered[key] = (e['category'], finite_number(e['handicap'], 'Handicap'))
    seen = set()
    entries = {}
    for r in data['rounds']:
        if r['player_id'] not in ids['players'] or r['tournament_id'] not in ids['tournaments'] or r['layout_id'] not in ids['layouts']:
            raise ValueError('Invalid round links.')
        t = find(data, 'tournaments', r['tournament_id'])
        integer(r['round_number'], 'Round', 1, t['num_rounds'])
        if r['category'] not in t['categories'] or r['layout_id'] != t['layout_id']:
            raise ValueError('Round layout or category does not belong to tournament.')
        k = (r['tournament_id'], r['player_id'], r['round_number'])
        if k in seen:
            raise ValueError('Duplicate player round.')
        seen.add(k)
        entry = (r['tournament_id'], r['player_id'])
        metadata = (r['category'], finite_number(r['handicap'], 'Handicap'))
        if entry in registered and registered[entry] != metadata:
            raise ValueError('Scores do not match tournament registration.')
        if entry in entries and entries[entry] != metadata:
            raise ValueError('Conflicting category or handicap within a tournament.')
        entries[entry] = metadata
        integer(r['total'], 'Total')
        integer(r['par'], 'Total par')
        if r['holes']:
            validate_holes(r['holes'])
            scores = [integer(h['throws'], 'Throws', 1, 100) for h in r['holes']]
            if sum(scores) != r['total'] or sum(h['par'] for h in r['holes']) != r['par']:
                raise ValueError('Round totals do not match hole scores.')
    return data
