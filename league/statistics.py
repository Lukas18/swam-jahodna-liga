"""Statistics from recorded round snapshots, with explicit scopes and denominators."""
from collections import defaultdict
from .domain import OUTCOMES, outcome


def selected_rounds(data, tournament_id=None, course_id=None, layout_id=None, category='All'):
    layouts = {layout['id']: layout for layout in data['layouts']}
    return [r for r in data['rounds']
            if (tournament_id is None or r['tournament_id'] == tournament_id)
            and (course_id is None or layouts[r['layout_id']]['course_id'] == course_id)
            and (layout_id is None or r['layout_id'] == layout_id)
            and (category == 'All' or r['category'] == category)]


def summary(rounds):
    return {'Recorded rounds': len(rounds), 'Players': len({r['player_id'] for r in rounds}),
            'Tournaments': len({r['tournament_id'] for r in rounds}),
            'Hole scores': sum(len(r['holes']) for r in rounds),
            'Average throws': sum(r['total'] for r in rounds)/len(rounds) if rounds else None,
            'Average +/− par': sum(r['total']-r['par'] for r in rounds)/len(rounds) if rounds else None}


def round_overview(data, rounds, by='layout'):
    """Category summaries keep different course/layout populations visible."""
    layouts = {x['id']: x for x in data['layouts']}
    courses = {x['id']: x for x in data['courses']}
    grouped = defaultdict(list)
    for r in rounds:
        layout = layouts[r['layout_id']]
        key = (layout['id'] if by == 'layout' else layout['course_id'], r['category'])
        grouped[key].append(r)
    rows = []
    for (item_id, category), records in grouped.items():
        course = courses[layouts[item_id]['course_id']] if by == 'layout' else courses[item_id]
        row = {'Course': course['name']}
        if by == 'layout':
            row['Layout'] = layouts[item_id]['name']
        row['Category'] = category
        row.update(summary(records))
        rows.append(row)
    return sorted(rows, key=lambda r: (r['Course'], r.get('Layout', ''), r['Category']))


def hole_statistics(data, rounds, combine_categories=False):
    """Combine by layout/hole when requested, weighting each recorded score equally."""
    layouts = {x['id']: x for x in data['layouts']}
    courses = {x['id']: x for x in data['courses']}
    grouped = defaultdict(list)
    for r in rounds:
        for h in r['holes']:
            key = ((r['layout_id'], 'All', h['number']) if combine_categories else
                   (r['layout_id'], r['category'], h['number'], h['par'], h['length']))
            grouped[key].append(h)
    rows = []
    for key, holes in grouped.items():
        layout_id, category, number = key[:3]
        par = sum(h['par'] for h in holes) / len(holes)
        if par.is_integer():
            par = int(par)
        known_lengths = [h['length'] for h in holes if h['length'] > 0]
        length = sum(known_lengths) / len(known_lengths) if known_lengths else 0
        throws = [h['throws'] for h in holes]
        layout = layouts[layout_id]
        row = {'Course': courses[layout['course_id']]['name'], 'Layout': layout['name'], 'Category': category,
               'Hole': number, 'Par': par, 'Length (m)': length, 'Scores': len(throws),
               'Average throws': sum(throws)/len(throws),
               'Average +/− par': sum(h['throws']-h['par'] for h in holes)/len(holes)}
        for label in OUTCOMES:
            row[label + ' %'] = 100 * sum(outcome(h['throws'], h['par']) == label for h in holes)/len(holes)
        rows.append(row)
    return sorted(rows, key=lambda r: (r['Course'], r['Layout'], r['Category'], r['Hole'], r['Par'], r['Length (m)']))


def hole_heat_styles(row, theme='dark'):
    """Three contrast steps for score averages; outcome percentages remain neutral."""
    def tint(value, green, thresholds):
        if value <= thresholds[0]:
            return ''
        level = 0 if value <= thresholds[1] else 1 if value <= thresholds[2] else 2
        palettes = {
            'light': {'green': ['#D6EEDF', '#AFDBC1', '#7BBF9B'], 'warm': ['#F7E2CF', '#ECC49F', '#DAA176']},
            'dark': {'green': ['#B6DFCD', '#80C6A7', '#48A680'], 'warm': ['#EDD2B9', '#DFAD82', '#CA855D']},
        }
        palette = palettes['light' if theme == 'light' else 'dark']['green' if green else 'warm']
        return f'background-color: {palette[level]}; color: #17251F'
    styles = []
    deviation = row['Average +/− par']
    for column in row.keys():
        if column in ['Average throws', 'Average +/− par']:
            styles.append(tint(abs(deviation), deviation < 0, (0.25, 0.75, 1.5)))
        else:
            styles.append('')
    return styles


def trend_observations(data):
    """Compact player/event/layout/category summaries, rebuilt after result edits."""
    groups = {}
    for r in data['rounds']:
        key = (r['player_id'], r['tournament_id'], r['layout_id'], r['category'])
        row = groups.setdefault(key, dict(zip(
            ['player_id', 'tournament_id', 'layout_id', 'category'], key),
            total=0, par=0, round_count=0))
        row['total'] += r['total']
        row['par'] += r['par']
        row['round_count'] += 1
    return list(groups.values())


def scoring_trend(data, rounds, player_ids=None):
    """Per-event mean relative-to-par per round, equal weight per player.

    Scopes are supplied by the caller. Layouts always remain separate. Every
    recorded player event contributes once, including totals-only scorecards.
    """
    tournaments = {t['id']: t for t in data['tournaments']}
    layouts = {layout['id']: layout for layout in data['layouts']}
    courses = {course['id']: course for course in data['courses']}
    events = defaultdict(lambda: defaultdict(list))
    chosen = None if player_ids is None else set(player_ids)
    for r in rounds:
        if chosen is None or r['player_id'] in chosen:
            events[(r['layout_id'], r['tournament_id'])][r['player_id']].append((r['total'] - r['par'], r.get('round_count', 1)))
    rows = []
    for (layout_id, tid), players in events.items():
        means = [sum(value for value, _ in scores) / sum(count for _, count in scores) for scores in players.values()]
        t, layout = tournaments[tid], layouts[layout_id]
        rows.append({'tournament_id': tid, 'Date': t['date'], 'Tournament': t['name'],
                     'event_order': t.get('event_order', 0), 'layout_id': layout_id,
                     'Course': courses[layout['course_id']]['name'], 'Layout': layout['name'],
                     'Average +/− par': sum(means) / len(means), 'Players': len(means)})
    return sorted(rows, key=lambda r: (r['Date'], r['event_order'], r['tournament_id'], r['layout_id']))


def top_trend_players(data, rounds, count):
    """Lowest mean event score among players with at least three scoped rounds."""
    from fractions import Fraction
    by_event = defaultdict(list)
    round_counts = defaultdict(int)
    for r in rounds:
        by_event[(r['player_id'], r['tournament_id'])].append((r['total'] - r['par'], r.get('round_count', 1)))
        round_counts[r['player_id']] += r.get('round_count', 1)
    by_player = defaultdict(list)
    for (pid, _), scores in by_event.items():
        by_player[pid].append(Fraction(sum(value for value, _ in scores), sum(count for _, count in scores)))
    players = {p['id']: p for p in data['players']}
    ranking = sorted((pid for pid in by_player if round_counts[pid] > 2),
                     key=lambda pid: (sum(by_player[pid]) / len(by_player[pid]),
                     (players[pid]['first_name'] + ' ' + players[pid]['last_name']).casefold(), pid))
    return ranking[:count]
