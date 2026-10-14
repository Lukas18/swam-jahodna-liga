"""WHS-inspired selection model: recorded par, slope 113, PCC zero, uncapped."""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json

GOLF_ALGORITHM = 'relative-par-best-of-20-ceiling-v1'


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


def add_golf_handicaps(data):
    """Add parallel snapshots to an already recalculated legacy document in place."""
    from .handicaps import ceil_handicap
    run_id = hashlib.sha256(json.dumps([GOLF_ALGORITHM, data['handicap_run']['id'],
        'legacy-provisional-before-3'], sort_keys=True).encode()).hexdigest()
    old = data.get('golf_handicap_run', {})
    data['golf_handicap_run'] = {'id': run_id, 'algorithm': GOLF_ALGORITHM,
        'source_revision': old.get('source_revision', data.get('revision',0))
        if old.get('id') == run_id else data.get('revision',0)}
    rounds = defaultdict(list)
    for r in data['rounds']:
        rounds[(r['player_id'],r['tournament_id'])].append(r)
    legacy = defaultdict(list)
    for h in data['handicap_history']:
        legacy[h['player_id']].append(h)
    histories, by_event = [], {}
    for player in data['players']:
        pid = player['id']
        window, previous = [], None
        history = sorted(legacy[pid], key=lambda h:(h['date'],h['event_order'],h['tournament_id']))
        for h in history:
            records = sorted(rounds[(pid,h['tournament_id'])],key=lambda r:r['round_number'])
            for r in records:
                if eligible_round(r):
                    window.append({'round_id':r['id'],'tournament_id':r['tournament_id'],
                        'round_number':r['round_number'],'score':str(Decimal(str(r['total']))-Decimal(str(r['par'])))})
            window = window[-20:]
            used, adjustment = selection_rule(len(window))
            selected = sorted(window,key=lambda r:Decimal(r['score']))[:used]
            raw = min(Decimal(54),sum(Decimal(r['score']) for r in selected)/used+adjustment) if used else None
            after = ceil_handicap(raw) if raw is not None else h['handicap_after']
            snapshot_id = hashlib.sha256(f'{run_id}:{pid}:{h["tournament_id"]}'.encode()).hexdigest()
            source_groups = defaultdict(list)
            for r in selected:
                source_groups[r['tournament_id']].append(Decimal(r['score']))
            g = {k:h[k] for k in ['player_id','tournament_id','date','event_order','event_score','bootstrap']}
            g.update(id=snapshot_id,run_id=run_id,
                handicap_before=previous['handicap_after'] if previous else None,
                handicap_used=previous['handicap_after'] if previous else h['handicap_used'],
                handicap_after=after,
                # SQL's existing 1..10 count stores selected sources, not the 20-round window.
                sample_count=max(1,used), selection_count=used, window_count=len(window),
                adjustment=str(adjustment),raw_index=str(raw) if raw is not None else None,
                index=str(raw.quantize(Decimal('.1'),rounding=ROUND_HALF_UP)) if raw is not None else None,
                provisional=raw is None, used_provisional=previous['provisional'] if previous else True,
                selected_rounds=selected,
                sources=[{'tournament_id':tid,'score':str(sum(scores)/len(scores))} for tid,scores in source_groups.items()])
            histories.append(g);by_event[(pid,h['tournament_id'])]=g;previous=g
        player['golf_handicap'] = previous['handicap_after'] if previous else player['handicap']
        player['golf_handicap_pending'] = player.get('handicap_pending', False) if previous is None else False
        player['golf_provisional'] = previous['provisional'] if previous else True
        player['golf_handicap_snapshot_id'] = previous['id'] if previous else None
        for t in data['tournaments']:
            key = (pid,t['id'])
            if key not in by_event:
                prior = [g for g in histories if g['player_id']==pid and
                         (g['date'],g['event_order']) < (t['date'],t.get('event_order',0))]
                if prior:
                    by_event[key]={'handicap_used':prior[-1]['handicap_after'],
                        'used_provisional':prior[-1]['provisional'],'id':None}
    data['golf_handicap_history'] = histories
    for record in data.get('registrations',[]) + data['rounds']:
        g = by_event.get((record['player_id'],record['tournament_id']))
        record['golf_handicap'] = g['handicap_used'] if g else record['handicap']
        record['golf_handicap_pending'] = record.get('handicap_pending',False)
        record['golf_provisional'] = g['used_provisional'] if g else True
        record['golf_handicap_snapshot_id'] = g['id'] if g else None
    return data
