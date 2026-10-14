"""Lossless adapters between domain documents and normalized SQL records.

JSON is the RPC transport, not the database's entity storage. Extra fields retain
forward-compatible metadata without duplicating core entity columns.
"""
from copy import deepcopy
from decimal import Decimal

# SQL definitions also drive the reviewed SQL migration generator.
TABLES = {
 'categories': [('code','text'),('position','integer')],
 'players': [('id','text'),('first_name','text'),('last_name','text'),('category_code','text'),('handicap','integer'),('udisc','text'),('handicap_snapshot_id','text')],
 'courses': [('id','text'),('name','text'),('description','text')],
 'layouts': [('id','text'),('course_id','text'),('name','text')],
 'layout_profiles': [('layout_id','text'),('profile_key','text'),('category_code','text')],
 'layout_holes': [('layout_id','text'),('profile_key','text'),('number','integer'),('par','integer'),('length','numeric')],
 'leagues': [('id','text'),('name','text'),('points_scope','text'),('tie_mode','text')],
 'league_points': [('league_id','text'),('place','integer'),('points','integer')],
 'tournaments': [('id','text'),('name','text'),('date','date'),('league_id','text'),('layout_id','text'),('num_rounds','integer'),('event_order','integer')],
 'tournament_categories': [('tournament_id','text'),('category_code','text'),('position','integer')],
 'tournament_entries': [('tournament_id','text'),('player_id','text'),('category_code','text'),('handicap','integer'),('handicap_snapshot_id','text')],
 'scorecards': [('id','text'),('tournament_id','text'),('player_id','text'),('layout_id','text'),('round_number','integer'),('category_code','text'),('handicap','integer'),('total','integer'),('par','integer'),('recorded_at','timestamptz'),('handicap_snapshot_id','text')],
 'hole_scores': [('scorecard_id','text'),('number','integer'),('par','integer'),('length','numeric'),('throws','integer')],
 'handicap_runs': [('id','text'),('algorithm','text'),('source_revision','integer')],
 'handicap_history': [('id','text'),('run_id','text'),('player_id','text'),('tournament_id','text'),('date','date'),('event_order','integer'),('event_score','numeric'),('handicap_before','integer'),('handicap_used','integer'),('handicap_after','integer'),('sample_count','integer'),('bootstrap','boolean')],
 'handicap_sources': [('snapshot_id','text'),('tournament_id','text'),('score','numeric'),('position','integer')],
 'stableford_results': [('tournament_id','text'),('player_id','text'),('points','integer'),('status','text'),('calculation_version','text'),('handicap_snapshot_id','text'),('source_run_id','text')],
 'app_settings': [('site_title','text'),('active_league_id','text')],
}
KEYS = {name:['id'] for name in TABLES}
KEYS.update(categories=['code'], layout_profiles=['layout_id','profile_key'],layout_holes=['layout_id','profile_key','number'],
 league_points=['league_id','place'],tournament_categories=['tournament_id','category_code'],tournament_entries=['tournament_id','player_id'],
 hole_scores=['scorecard_id','number'],handicap_sources=['snapshot_id','tournament_id'],stableford_results=['tournament_id','player_id'],app_settings=[])
COLLECTIONS = {'players':'players','courses':'courses','layouts':'layouts','leagues':'leagues','tournaments':'tournaments',
               'tournament_entries':'registrations','scorecards':'rounds','handicap_history':'handicap_history','stableford_results':'stableford_results'}


def to_records(data):
    payload = {table:[] for table in TABLES}
    root_keys = {'categories','settings','schema_version','revision','handicap_run'} | set(COLLECTIONS.values())
    payload['root'] = {'schema_version':data['schema_version'],'extra':{k:deepcopy(v) for k,v in data.items() if k not in root_keys}}
    def pack(table, obj, exclude=()):
        obj = deepcopy(obj)
        if 'category' in obj:
            obj['category_code'] = obj.pop('category')
        cols = [k for k,_ in TABLES[table]]
        row = {k:obj[k] for k in cols if k in obj}
        for key, typ in TABLES[table]:
            if typ == 'integer' and row.get(key) is not None:
                value = Decimal(str(row[key]))
                if value != value.to_integral_value():
                    raise ValueError(f'{table}.{key} must be a whole number, got {row[key]!r}.')
                row[key] = int(value)
        row['extra'] = {k:v for k,v in obj.items() if k not in cols and k not in exclude}
        row['extra']['_present'] = list(row)
        row['extra']['_numeric_text'] = {k:obj[k] for k,typ in TABLES[table] if typ == 'numeric' and isinstance(obj.get(k), str)}
        row['extra']['_timestamp_text'] = {k:obj[k] for k,typ in TABLES[table] if typ == 'timestamptz' and k in obj}
        row['sort_order'] = len(payload[table])
        payload[table].append(row)
    for i,code in enumerate(data['categories']):pack('categories',{'code':code,'position':i})
    for table,collection in COLLECTIONS.items():
        for obj in data.get(collection,[]):
            skip = {'layouts':['profiles'],'leagues':['points'],'tournaments':['categories'],'scorecards':['holes'],'handicap_history':['sources']}.get(table,[])
            pack(table,obj,skip)
    for layout in data['layouts']:
        for key,holes in layout['profiles'].items():
            pack('layout_profiles',{'layout_id':layout['id'],'profile_key':key,'category_code':None if key=='default' else key})
            for h in holes:pack('layout_holes',{'layout_id':layout['id'],'profile_key':key,**h})
    for league in data['leagues']:
        for i,points in enumerate(league['points'],1):pack('league_points',{'league_id':league['id'],'place':i,'points':points})
    for t in data['tournaments']:
        for i,code in enumerate(t['categories']):pack('tournament_categories',{'tournament_id':t['id'],'category_code':code,'position':i})
    for r in data['rounds']:
        for h in r['holes']:pack('hole_scores',{'scorecard_id':r['id'],**h})
    for h in data.get('handicap_history',[]):
        for i,source in enumerate(h['sources']):pack('handicap_sources',{'snapshot_id':h['id'],'position':i,**source})
    if data.get('handicap_run'):pack('handicap_runs',data['handicap_run'])
    pack('app_settings',data.get('settings',{}))
    return payload


def from_records(payload, revision):
    root=payload['root']
    result={**deepcopy(root.get('extra',{})),'schema_version':root['schema_version'],'revision':revision}
    def unpack(table,row):
        # NULL optional columns are omitted unless present in the original object;
        # extra tracks that distinction through the serializer's presence list.
        out=deepcopy(row.get('extra',{}))
        present=out.pop('_present',None)
        numeric_text=out.pop('_numeric_text',{})
        timestamp_text=out.pop('_timestamp_text',{})
        for key,_ in TABLES[table]:
            if key in row and (row[key] is not None or present is None or key in present):out[key]=row[key]
        out.update(numeric_text)
        out.update(timestamp_text)
        if 'category_code' in out and table in ['players','tournament_entries','scorecards']:out['category']=out.pop('category_code')
        return out
    result['categories']=[r['code'] for r in sorted(payload['categories'],key=lambda r:r['position'])]
    for table,collection in COLLECTIONS.items():result[collection]=[unpack(table,row) for row in payload[table]]
    # Index children once rather than rescanning/sorting them for every parent.
    def grouped(table, fields, order):
        groups = {}
        for row in sorted(payload[table], key=lambda r: r[order]):
            groups.setdefault(tuple(row[f] for f in fields), []).append(row)
        return groups
    profiles = grouped('layout_profiles', ['layout_id'], 'profile_key')
    holes = grouped('layout_holes', ['layout_id', 'profile_key'], 'number')
    points = grouped('league_points', ['league_id'], 'place')
    categories = grouped('tournament_categories', ['tournament_id'], 'position')
    scores = grouped('hole_scores', ['scorecard_id'], 'number')
    sources = grouped('handicap_sources', ['snapshot_id'], 'position')
    for layout in result['layouts']:
        layout['profiles'] = {}
        for profile in profiles.get((layout['id'],), []):
            children = []
            for row in holes.get((layout['id'], profile['profile_key']), []):
                h = unpack('layout_holes', row)
                h.pop('layout_id'); h.pop('profile_key')
                children.append(h)
            layout['profiles'][profile['profile_key']] = children
    for league in result['leagues']:
        league['points'] = [r['points'] for r in points.get((league['id'],), [])]
    for t in result['tournaments']:
        t['categories'] = [r['category_code'] for r in categories.get((t['id'],), [])]
    for r in result['rounds']:
        r['holes'] = []
        for row in scores.get((r['id'],), []):
            h = unpack('hole_scores', row); h.pop('scorecard_id')
            r['holes'].append(h)
    for h in result.get('handicap_history', []):
        h['event_score'] = str(h['event_score'])
        h['sources'] = [{'tournament_id': r['tournament_id'], 'score': str(r['score'])}
                        for r in sources.get((h['id'],), [])]
    result['settings']=unpack('app_settings',payload['app_settings'][0]) if payload['app_settings'] else {}
    result['handicap_run']=unpack('handicap_runs',payload['handicap_runs'][0]) if payload['handicap_runs'] else {}
    return result
