"""WHS-inspired selection model: recorded par, slope 113, PCC zero, uncapped."""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
import hashlib

GOLF_ALGORITHM = 'relative-par-best-of-20-ceiling-v2'


def selection_rule(count):
    if count < 3:
        return 0, Decimal(0)
    for maximum, used, adjustment in [(3,1,-2),(4,1,-1),(5,1,0),(6,2,-1),
            (8,2,0),(11,3,0),(14,4,0),(16,5,0),(18,6,0),(19,7,0)]:
        if count <= maximum:
            return used, Decimal(adjustment)
    return 8, Decimal(0)


def eligible_round(r):
    return len(r['holes']) == 18 and {h['number'] for h in r['holes']} == set(range(1,19))


def calculate_golf_history(data, by_player, rounds, run_id):
    """Write canonical handicap values using the player's initial HCP until round three."""
    from .handicaps import ceil_handicap

    histories, by_event = [], {}
    initial_by_player = {}
    for player in data['players']:
        pid = player['id']
        initial = ceil_handicap(player.setdefault('original_handicap', player['handicap']))
        initial_by_player[pid] = initial
        window, previous = [], None
        events = sorted(by_player[pid], key=lambda e: (e[0]['date'], e[0].get('event_order', 0), e[0]['id']))
        seen_dates = set()
        for t, score in events:
            order = (t['date'], t.get('event_order', 0))
            if order in seen_dates:
                raise ValueError('Two completed tournaments for one player have the same date/order. Set distinct event_order values before calculating handicaps.')
            seen_dates.add(order)
            for r in sorted(rounds[(pid, t['id'])], key=lambda r: r['round_number']):
                if eligible_round(r):
                    window.append({'round_id': r['id'], 'tournament_id': t['id'],
                                   'round_number': r['round_number'],
                                   'score': str(Decimal(str(r['total'])) - Decimal(str(r['par'])))})
            window = window[-20:]
            used, adjustment = selection_rule(len(window))
            selected = sorted(window, key=lambda r: Decimal(r['score']))[:used]
            raw = min(Decimal(54), sum(Decimal(r['score']) for r in selected) / used + adjustment) if used else None
            after = ceil_handicap(raw) if raw is not None else initial
            snapshot_id = hashlib.sha256(f'{run_id}:{pid}:{t["id"]}'.encode()).hexdigest()
            source_groups = defaultdict(list)
            for r in selected:
                source_groups[r['tournament_id']].append(Decimal(r['score']))
            h = {'id': snapshot_id, 'run_id': run_id, 'player_id': pid, 'tournament_id': t['id'],
                 'date': t['date'], 'event_order': t.get('event_order', 0), 'event_score': str(score),
                 'bootstrap': previous is None, 'handicap_before': previous['handicap_after'] if previous else None,
                 'handicap_used': previous['handicap_after'] if previous else initial,
                 'handicap_after': after, 'sample_count': max(1, used),
                 'selection_count': used, 'window_count': len(window), 'adjustment': str(adjustment),
                 'raw_index': str(raw) if raw is not None else None,
                 'index': str(raw.quantize(Decimal('.1'), rounding=ROUND_HALF_UP)) if raw is not None else None,
                 'provisional': raw is None, 'used_provisional': previous['provisional'] if previous else True,
                 'selected_rounds': selected,
                 'sources': [{'tournament_id': tid, 'score': str(sum(scores) / len(scores))}
                             for tid, scores in source_groups.items()]}
            histories.append(h)
            by_event[(pid, t['id'])] = h
            previous = h
        player['handicap'] = previous['handicap_after'] if previous else initial
        player['handicap_pending'] = False
        player['handicap_snapshot_id'] = previous['id'] if previous else None
        player['handicap_provisional'] = previous['provisional'] if previous else True
        for t in data['tournaments']:
            key = (pid, t['id'])
            if key not in by_event:
                prior = [h for h in histories if h['player_id'] == pid and
                         (h['date'], h['event_order']) < (t['date'], t.get('event_order', 0))]
                if prior:
                    by_event[key] = {'handicap_used': prior[-1]['handicap_after'],
                                     'used_provisional': prior[-1]['provisional'], 'id': None}
    for record in data.get('registrations', []) + data['rounds']:
        record.setdefault('original_handicap', record['handicap'])
        snapshot = by_event.get((record['player_id'], record['tournament_id']))
        record['handicap'] = snapshot['handicap_used'] if snapshot else initial_by_player[record['player_id']]
        record['handicap_pending'] = False
        record['handicap_provisional'] = snapshot['used_provisional'] if snapshot else True
        record['handicap_snapshot_id'] = snapshot['id'] if snapshot else None
    return histories, by_event
