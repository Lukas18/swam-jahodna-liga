#!/usr/bin/env python3
"""Back up and add the parallel golf-style history; preview unless --apply."""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from import_players import load_store
from league.handicaps import recalculate_handicaps
from league.storage import encoded


def verify_legacy(before, after):
    """Preserve existing values; calculation-run IDs may refresh to current inputs."""
    for key,value in before.items():
        if key in ['revision','golf_handicap_run','golf_handicap_history']:
            continue
        if key == 'handicap_run':
            if value.get('algorithm') != after[key].get('algorithm'):
                raise ValueError('Original handicap algorithm changed.')
        elif key == 'handicap_history':
            strip = lambda h:{k:v for k,v in h.items() if k not in ['id','run_id']}
            if [strip(h) for h in value] != [strip(h) for h in after[key]]:
                raise ValueError('Original handicap history values changed.')
        elif key == 'stableford_results':
            strip = lambda h:{k:v for k,v in h.items() if k not in ['handicap_snapshot_id','source_run_id']}
            if [strip(h) for h in value] != [strip(h) for h in after[key]]:
                raise ValueError('Existing Stableford values changed.')
        elif key == 'settings':
            for field,old in value.items():
                if field != 'handicap_method' and after[key].get(field) != old:
                    raise ValueError(f'Existing setting changed: {field}')
        elif key in ['players','rounds','registrations']:
            identity = (lambda r:(r['tournament_id'],r['player_id'])) if key=='registrations' else (lambda r:r['id'])
            current = {identity(r):r for r in after[key]}
            if len(current) != len(value):
                raise ValueError(f'Entity count changed: {key}')
            for old in value:
                new = current[identity(old)]
                for field,original in old.items():
                    if not field.startswith('golf_') and field != 'handicap_snapshot_id' and new.get(field) != original:
                        raise ValueError(f'Existing value changed: {key}.{field}')
        elif after.get(key) != value:
            raise ValueError(f'Existing collection changed: {key}')


def backup(data, name):
    folder=Path(__file__).resolve().parent/'data/backups';folder.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(ZoneInfo('Europe/Bratislava')).strftime('%Y%m%d-%H%M%S-%f')
    path=folder/f'{name}-{stamp}.json';raw=encoded(data)
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(raw)
    path.with_suffix('.sha256').write_text(hashlib.sha256(raw).hexdigest()+'  '+path.name+'\n')
    assert json.loads(path.read_bytes())==data
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--activate',choices=['legacy','golf'],help='Default: keep the current method')
    parser.add_argument('--document-id',default='main')
    parser.add_argument('--secrets',type=Path,default=Path(__file__).resolve().parent/'.streamlit/secrets.toml')
    args=parser.parse_args()
    store=load_store(args.secrets,args.document_id)
    if store.model!='relational':raise ValueError('Requires relational storage.')
    before,version=store.load();draft=recalculate_handicaps(before)
    method=args.activate or before.get('settings',{}).get('handicap_method','legacy')
    draft.setdefault('settings',{})['handicap_method']=method
    verify_legacy(before,draft)
    print(json.dumps({'source_revision':version,'method':method,
        'legacy_snapshots':len(draft['handicap_history']),
        'golf_snapshots':len(draft['golf_handicap_history']),
        'players_with_golf_estimate':sum(not p['golf_provisional'] for p in draft['players']),
        'players_provisional':sum(p['golf_provisional'] for p in draft['players'])}))
    if not args.apply:
        print('Preview only; all original fields preserved. No writes.');return
    if before==draft:
        print('Already up to date. No writes.');return
    path=backup(before,'before-golf-backfill');print('Backup:',path)
    # Atomic revision check in dg_save rejects edits since the source was loaded.
    store.save(draft,version)
    saved,new_version=store.load()
    verify_legacy(before,saved)
    if saved!=draft:raise ValueError('Saved document differs from verified payload.')
    after=backup(saved,'after-golf-backfill')
    print('Verified revision',new_version,'both histories retained. Snapshot:',after)


if __name__=='__main__':main()
