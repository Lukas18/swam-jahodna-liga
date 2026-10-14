"""Chronological, versioned handicap snapshots and subsequent Stableford calculation."""
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING
import hashlib
import json

ALGORITHM = 'relative-par-last-10-ceiling-v1'
METHODS = ['legacy', 'golf']


def handicap_method(data):
    method = data.get('settings', {}).get('handicap_method', 'legacy')
    if method not in METHODS:
        raise ValueError('Invalid handicap method.')
    return method


def project_handicaps(data):
    """Display the selected method; stored core columns always remain legacy."""
    draft = deepcopy(data)
    if handicap_method(draft) == 'golf':
        for r in draft['players'] + draft.get('registrations', []) + draft['rounds']:
            r['handicap'] = r['golf_handicap']
            r['handicap_pending'] = r['golf_handicap_pending']
            r['handicap_snapshot_id'] = r['golf_handicap_snapshot_id']
    from .stableford import project_stablefords
    return project_stablefords(draft, handicap_method(draft))


def handicaps_current(data):
    from .golf import GOLF_ALGORITHM
    return (data.get('handicap_run', {}).get('algorithm') == ALGORITHM
            and data.get('golf_handicap_run', {}).get('algorithm') == GOLF_ALGORITHM)


def ceil_handicap(value):
    return int(Decimal(str(value)).to_integral_value(rounding=ROUND_CEILING))


def recalculate_handicaps(data):
    """Return a separate state with historical event handicaps and current profiles.

    Each completed event contributes its mean relative-to-par per round. Bootstrap
    uses the debut result; later events use only earlier completed events. Registering
    for a future event never consumes a history slot. Source scores retain precision.
    """
    handicap_method(data)
    draft = deepcopy(data)
    tournaments = {t['id']: t for t in draft['tournaments']}
    grouped = defaultdict(list)
    for r in draft['rounds']:
        grouped[(r['player_id'], r['tournament_id'])].append(r)
    by_player = defaultdict(list)
    for (pid, tid), rounds in grouped.items():
        t = tournaments[tid]
        if len(rounds) == t['num_rounds'] and {r['round_number'] for r in rounds} == set(range(1, t['num_rounds'] + 1)):
            score = sum(Decimal(str(r['total'])) - Decimal(str(r['par'])) for r in rounds) / len(rounds)
            by_player[pid].append((t, score))
    source = sorted((pid, t['id'], t['date'], t.get('event_order', 0), str(score))
                    for pid, events in by_player.items() for t, score in events)
    score_inputs = sorted((r['id'], r['layout_id'], r['category'], r['total'], r['par'], [(h['number'], h['par'], h['throws']) for h in r['holes']]) for r in draft['rounds'])
    run_id = hashlib.sha256(json.dumps([ALGORITHM, source, score_inputs], ensure_ascii=False).encode()).hexdigest()
    history, snapshot_by_event, used_by_event = [], {}, {}
    for player in draft['players']:
        pid = player['id']
        events = sorted(by_player[pid], key=lambda e: (e[0]['date'], e[0].get('event_order', 0), e[0]['id']))
        seen_dates = set()
        for t, _ in events:
            order = (t['date'], t.get('event_order', 0))
            if order in seen_dates:
                raise ValueError('Two completed tournaments for one player have the same date/order. Set distinct event_order values before calculating handicaps.')
            seen_dates.add(order)
        player_history = []
        for i, (t, score) in enumerate(events):
            window = events[max(0, i-9):i+1]
            after = ceil_handicap(sum(s for _, s in window) / len(window))
            before = player_history[-1]['handicap_after'] if player_history else None
            used = ceil_handicap(score) if before is None else before
            snapshot_id = hashlib.sha256(f'{run_id}:{pid}:{t["id"]}'.encode()).hexdigest()
            h = {'id': snapshot_id, 'run_id': run_id, 'player_id': pid, 'tournament_id': t['id'],
                 'date': t['date'], 'event_order': t.get('event_order', 0), 'event_score': str(score),
                 'handicap_before': before, 'handicap_used': used, 'handicap_after': after,
                 'sample_count': len(window), 'bootstrap': before is None,
                 'sources': [{'tournament_id': event['id'], 'score': str(value)} for event, value in window]}
            player_history.append(h)
            snapshot_by_event[(pid, t['id'])] = snapshot_id
            used_by_event[(pid, t['id'])] = used
        history.extend(player_history)
        player.setdefault('original_handicap', player['handicap'])
        player['handicap'] = player_history[-1]['handicap_after'] if player_history else None
        player['handicap_snapshot_id'] = player_history[-1]['id'] if player_history else None
        # For undated future/new registrations use the most recent prior event.
        for t in tournaments.values():
            key = (pid, t['id'])
            if key not in used_by_event:
                prior = [h for h in player_history if (h['date'], h['event_order']) < (t['date'], t.get('event_order', 0))]
                used_by_event[key] = prior[-1]['handicap_after'] if prior else None
    # Existing domain APIs require finite handicaps. Pending debut players use 0
    # internally only with an explicit pending flag; UI shows a dash, not a real 0.
    for player in draft['players']:
        player['handicap_pending'] = player['handicap'] is None
        if player['handicap'] is None:
            player['handicap'] = 0
    for entry in draft.get('registrations', []):
        key = (entry['player_id'], entry['tournament_id'])
        entry.setdefault('original_handicap', entry['handicap'])
        entry['handicap_pending'] = used_by_event[key] is None
        entry['handicap'] = used_by_event[key] if used_by_event[key] is not None else 0
        entry['handicap_snapshot_id'] = snapshot_by_event.get(key)
    for r in draft['rounds']:
        key = (r['player_id'], r['tournament_id'])
        r.setdefault('original_handicap', r['handicap'])
        r['handicap_pending'] = used_by_event[key] is None
        r['handicap'] = used_by_event[key] if used_by_event[key] is not None else 0
        r['handicap_snapshot_id'] = snapshot_by_event.get(key)
    old_run = draft.get('handicap_run', {})
    draft['handicap_run'] = {'id': run_id, 'algorithm': ALGORITHM, 'source_revision': old_run.get('source_revision', data.get('revision', 0)) if old_run.get('id') == run_id else data.get('revision', 0)}
    draft['handicap_history'] = history
    # Preserve confirmed results only when their inputs/version still match.
    old_results = {(r['tournament_id'], r['player_id']): r for r in draft.get('stableford_results', [])}
    results = []
    for entry in draft.get('registrations', []):
        key = (entry['tournament_id'], entry['player_id'])
        existing = old_results.get(key)
        sid = snapshot_by_event.get((key[1], key[0]))
        if existing and existing.get('handicap_snapshot_id') == sid and existing.get('source_run_id') == run_id:
            results.append(existing)
        else:
            results.append({'tournament_id': key[0], 'player_id': key[1], 'points': None,
                            'status': 'pending_formula', 'calculation_version': None,
                            'handicap_snapshot_id': sid, 'source_run_id': run_id})
    draft['stableford_results'] = results
    from .golf import add_golf_handicaps
    from .stableford import calculate_stablefords
    return calculate_stablefords(add_golf_handicaps(draft))
