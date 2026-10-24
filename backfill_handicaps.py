#!/usr/bin/env python3
"""Back up and replace the legacy handicap history with golf-style history."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from import_players import load_store
from league.handicaps import recalculate_handicaps
from league.storage import encoded


def verify_source(before, after):
    """Check that migrating calculated values does not change recorded inputs."""
    for collection, identity, fields in [
        ('players', lambda r: r['id'], ('first_name','last_name','category','udisc')),
        ('registrations', lambda r: (r['tournament_id'],r['player_id']), ('category',)),
        ('rounds', lambda r: r['id'], ('tournament_id','player_id','round_number','category','total','par','holes')),
    ]:
        current = {identity(r):r for r in after[collection]}
        if set(current) != {identity(r) for r in before[collection]}:
            raise ValueError(f'{collection} identities changed.')
        for old in before[collection]:
            new = current[identity(old)]
            if any(new.get(field) != old.get(field) for field in fields):
                raise ValueError(f'{collection} source data changed.')
    for collection in ('categories','layouts','leagues'):
        if before[collection] != after[collection]:
            raise ValueError(f'{collection} changed.')
    for collection in ('courses', 'tournaments'):
        old = {row['id']: row for row in before[collection]}
        new = {row['id']: row for row in after[collection]}
        if set(old) != set(new):
            raise ValueError(f'{collection} identities changed.')
        for rid, row in old.items():
            original = {k: v for k, v in row.items() if k != 'stableford_difficulty'}
            current = {k: v for k, v in new[rid].items() if k != 'stableford_difficulty'}
            if original != current:
                raise ValueError(f'{collection} source data changed.')


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
    parser.add_argument('--document-id',default='main')
    parser.add_argument('--secrets',type=Path,default=Path(__file__).resolve().parent/'.streamlit/secrets.toml')
    args=parser.parse_args()
    store=load_store(args.secrets,args.document_id)
    if store.model!='relational':raise ValueError('Requires relational storage.')
    before,version=store.load();draft=recalculate_handicaps(before)
    verify_source(before,draft)
    print(json.dumps({'source_revision':version,'golf_snapshots':len(draft['handicap_history']),
        'players_with_golf_estimate':sum(not p['handicap_provisional'] for p in draft['players']),
        'players_provisional':sum(p['handicap_provisional'] for p in draft['players'])}))
    if not args.apply:
        print('Preview only; recorded inputs preserved. No writes.');return
    if before==draft:
        print('Already up to date. No writes.');return
    path=backup(before,'before-golf-backfill');print('Backup:',path)
    # Atomic revision check in dg_save rejects edits since the source was loaded.
    store.save(draft,version)
    saved,new_version=store.load()
    verify_source(before,saved)
    if saved!=draft:raise ValueError('Saved document differs from verified payload.')
    after=backup(saved,'after-golf-backfill')
    print('Verified revision',new_version,'single golf history retained. Snapshot:',after)


if __name__=='__main__':main()
