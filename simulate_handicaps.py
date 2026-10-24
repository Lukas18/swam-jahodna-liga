#!/usr/bin/env python3
"""Read-only WHS-inspired best-score comparison using a local league snapshot.

This is a selection-rule simulation, not an official golf Handicap Index.
Course Rating = recorded par, Slope = 113, PCC = 0. Raw recorded scores
are uncapped; net-double-bogey, exceptional-score and soft/hard-cap adjustments
are deliberately excluded because their required inputs are not available.
No database client or write API is used.
"""
import argparse
from collections import defaultdict
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
import json
from pathlib import Path


from league.golf import selection_rule


def completed_events(data):
    tournaments = {t['id']: t for t in data['tournaments']}
    grouped = defaultdict(list)
    for r in data['rounds']:
        grouped[(r['player_id'], r['tournament_id'])].append(r)
    events = defaultdict(list)
    for (pid, tid), rounds in grouped.items():
        event = tournaments[tid]
        expected = event['num_rounds']
        if len(rounds) != expected or {r['round_number'] for r in rounds} != set(range(1, expected + 1)):
            continue
        events[pid].append((event, sorted(rounds, key=lambda r: r['round_number'])))
    for records in events.values():
        records.sort(key=lambda item: (item[0]['date'], item[0].get('event_order', 0), item[0]['id']))
    return events


def simulate(data, top=5):
    """Select the busiest players (including attendance ties) before calculating."""
    if top < 1:
        raise ValueError('Top player count must be positive.')
    players = {p['id']: p for p in data['players']}
    events = completed_events(data)
    ranked = sorted(events, key=lambda pid: (-len(events[pid]),
        (players[pid]['first_name'] + ' ' + players[pid]['last_name']).casefold(), pid))
    if not ranked:
        return []
    cutoff = len(events[ranked[min(top, len(ranked)) - 1]])
    chosen = [pid for pid in ranked if len(events[pid]) >= cutoff]
    results = []
    for pid in chosen:
        player = players[pid]
        rounds = []
        for event, records in events[pid]:
            # This simulation only accepts full recorded 18-hole rounds.
            for r in records:
                if len(r['holes']) != 18 or {h['number'] for h in r['holes']} != set(range(1, 19)):
                    raise ValueError('Simulation requires complete 18-hole scorecards.')
                if sum(h['throws'] for h in r['holes']) != r['total'] or sum(h['par'] for h in r['holes']) != r['par']:
                    raise ValueError('Recorded round totals do not match its hole snapshots.')
                relative = Decimal(str(r['total'])) - Decimal(str(r['par']))
                rounds.append({'date': event['date'], 'tournament': event['name'],
                    'tournament_id': event['id'], 'round_number': r['round_number'],
                    'layout_id': r['layout_id'], 'category': r['category'],
                    'total': r['total'], 'par': r['par'], 'differential': relative})
        recent = rounds[-20:]
        used, adjustment = selection_rule(len(recent))
        selected = sorted(recent, key=lambda r: (r['differential'], r['date'],
                          r['tournament_id'], r['round_number']))[:used]
        raw = min(Decimal(54), sum(r['differential'] for r in selected) / used + adjustment) if used else None
        results.append({'player_id': pid, 'name': (player['first_name'] + ' ' + player['last_name']).strip(),
            'category': player['category'], 'tournaments': len(events[pid]), 'rounds': len(rounds),
            'window_count': len(recent), 'used_count': used, 'adjustment': adjustment,
            'raw_estimate': raw,
            'decimal_estimate': raw.quantize(Decimal('.1'), rounding=ROUND_HALF_UP) if raw is not None else None,
            # Preserve the league's upward-rounding rule on the unrounded mean.
            'integer_estimate': int(raw.to_integral_value(rounding=ROUND_CEILING)) if raw is not None else None,
            'selected': selected, 'window': recent})
    return results


def load_snapshot(path):
    data = json.loads(Path(path).read_text())
    if 'root' in data:
        from league.relational import from_records
        return from_records(data, data['revision'])
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path, help='Existing local domain JSON or dg_load snapshot')
    parser.add_argument('--top', type=int, default=5, help='Include attendance ties at this position')
    args = parser.parse_args()
    data = load_snapshot(args.snapshot)
    print(json.dumps({'source_revision': data['revision'], 'players': simulate(data, args.top)},
                     ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()
