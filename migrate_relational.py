#!/usr/bin/env python3
"""Additive copy from app_data to normalized tables; never changes app_data.

Run sql/001_relational.sql in Supabase first. Default command previews locally;
--apply copies to the new tables and verifies field equality. No legacy deletes.
"""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
from import_players import load_store
from league.domain import validate_data, site_settings
from league.handicaps import recalculate_handicaps
from league.relational import to_records, from_records


def prepare(data):
    original=deepcopy(data)
    original.setdefault('settings',site_settings(original))
    draft=recalculate_handicaps(original)
    validate_data(draft)
    check=from_records(to_records(draft),draft['revision'])
    assert check==draft, 'Record adapter changes source fields.'
    for old in data['rounds']:
        new=next(r for r in draft['rounds'] if r['id']==old['id'])
        for key in ['holes','total','par','category','layout_id','player_id','tournament_id','round_number']:
            assert old[key]==new[key],f'Original score changed: {key}'
    return draft


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--secrets',type=Path,default=Path(__file__).resolve().parent/'.streamlit/secrets.toml')
    p.add_argument('--document-id',default='main')
    p.add_argument('--source-json',type=Path,help='Offline document preview; cannot use with --apply.')
    p.add_argument('--apply',action='store_true')
    args=p.parse_args(argv)
    if args.apply and args.source_json:p.error('--source-json cannot be used with --apply')
    if args.source_json:
        data=json.loads(args.source_json.read_text())
        if 'rows' in data:data=next(r['content'] for r in data['rows'] if r['id']==args.document_id)
        source=None
    else:
        source=load_store(args.secrets,args.document_id);source.model='json';data,version=source.load()
        if version is None:raise ValueError('Source app_data document is missing.')
    draft=prepare(data)
    counts={table:len(rows) for table,rows in to_records(draft).items() if table!='root'}
    print(json.dumps(counts,indent=2))
    print('Handicap snapshots:',len(draft['handicap_history']),'algorithm:',draft['handicap_run']['algorithm'])
    print('Verified: original scorecards and hole snapshots preserved; Stableford pending formula.')
    if not args.apply:
        print('Preview only. After installing sql/001_relational.sql, run with --apply.')
        return
    target=load_store(args.secrets,args.document_id);target.model='relational'
    # Never overwrite an existing normalized document on migration retry.
    existing=target.db.rpc('dg_load',{'p_document_id':args.document_id}).execute().data
    if existing:
        current=from_records(existing,existing['revision'])
        a,b=deepcopy(current),deepcopy(draft)
        a.pop('revision',None);b.pop('revision',None)
        if a==b:
            print('Already migrated and verified. No writes performed.');return
        raise ValueError('Normalized document already exists and differs. No overwrite performed.')
    directory=Path(__file__).resolve().parent/'data/backups';directory.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(ZoneInfo('Europe/Bratislava')).strftime('%Y%m%d-%H%M%S-%f')
    backup=directory/f'before-relational-copy-{stamp}.json'
    raw=json.dumps(data,ensure_ascii=False,indent=2).encode()
    fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw)
    assert json.loads(backup.read_bytes())==data
    backup.with_suffix('.sha256').write_text(hashlib.sha256(raw).hexdigest()+'  '+backup.name+'\n')
    # Admin writes must stay paused until verification/cutover is complete.
    current,now_version=source.load()
    if now_version!=version or current!=data:raise ValueError('Source changed; migration aborted. Refresh and retry.')
    target.save(draft,None)
    saved,_=target.load()
    if saved!=draft:raise ValueError('Normalized read-back differs; keep app on legacy mode and inspect.')
    untouched,after_version=source.load()
    if untouched!=data or after_version!=version:
        raise ValueError('Legacy source changed concurrently. Keep app in legacy mode and reconcile before cutover.')
    print('Migration verified. Legacy app_data unchanged. Backup:',backup)
    print('Enable DISCGOLF_STORAGE_MODEL="relational" in Streamlit secrets and restart only after review.')


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('Migration stopped:',exc,file=sys.stderr);sys.exit(1)
