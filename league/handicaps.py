"""Chronological golf-style handicap snapshots and Stableford calculation."""
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING
import hashlib
import json

from .golf import GOLF_ALGORITHM, calculate_golf_history


def project_handicaps(data):
    """Return an isolated view of the canonical handicap and Stableford values."""
    return deepcopy(data)


def handicaps_current(data):
    return data.get('handicap_run', {}).get('algorithm') == GOLF_ALGORITHM


def ceil_handicap(value):
    return int(Decimal(str(value)).to_integral_value(rounding=ROUND_CEILING))


def recalculate_handicaps(data):
    """Rebuild one history from completed events and eligible 18-hole rounds."""
    draft = deepcopy(data)
    draft.get('settings', {}).pop('handicap_method', None)
    draft.pop('golf_handicap_run', None)
    draft.pop('golf_handicap_history', None)
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
    score_inputs = sorted((r['id'], r['layout_id'], r['category'], r['total'], r['par'],
                           [(h['number'], h['par'], h['throws']) for h in r['holes']]) for r in draft['rounds'])
    initial_inputs = sorted((p['id'], p.get('original_handicap', p['handicap'])) for p in draft['players'])
    run_id = hashlib.sha256(json.dumps([GOLF_ALGORITHM, source, score_inputs, initial_inputs],
                                   ensure_ascii=False).encode()).hexdigest()
    old_run = draft.get('handicap_run', {})
    draft['handicap_run'] = {'id': run_id, 'algorithm': GOLF_ALGORITHM,
                            'source_revision': old_run.get('source_revision', data.get('revision', 0))
                            if old_run.get('id') == run_id else data.get('revision', 0)}
    history, by_event = calculate_golf_history(draft, by_player, grouped, run_id)
    draft['handicap_history'] = history
    for collection in ('players', 'registrations', 'rounds'):
        for record in draft.get(collection, []):
            for key in tuple(record):
                if key.startswith('golf_'):
                    record.pop(key)
    old_results = {(r['tournament_id'], r['player_id']): r for r in draft.get('stableford_results', [])}
    results = []
    for entry in draft.get('registrations', []):
        key = (entry['tournament_id'], entry['player_id'])
        existing = old_results.get(key)
        snapshot = by_event.get((key[1], key[0]))
        sid = snapshot['id'] if snapshot else None
        if (existing and existing.get('handicap_snapshot_id') == sid
                and existing.get('source_run_id') == run_id):
            existing.pop('methods', None)
            results.append(existing)
        else:
            results.append({'tournament_id': key[0], 'player_id': key[1], 'points': None,
                            'status': 'pending_formula', 'calculation_version': None,
                            'handicap_snapshot_id': sid, 'source_run_id': run_id})
    draft['stableford_results'] = results
    from .stableford import calculate_stablefords
    return calculate_stablefords(draft)
