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
    """Three solid contrast steps per direction; neutral samples retain native colours."""
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
    below = {'Ace %', 'Albatross or better %', 'Eagle %', 'Birdie %'}
    above = {'Bogey %', 'Double bogey %', 'Triple bogey or worse %'}
    for column in row.keys():
        if column in ['Average throws', 'Average +/− par']:
            styles.append(tint(abs(deviation), deviation < 0, (0.25, 0.75, 1.5)))
        elif column in below | above:
            styles.append(tint(row[column], column in below, (0, 25, 50)))
        else:
            styles.append('')
    return styles
