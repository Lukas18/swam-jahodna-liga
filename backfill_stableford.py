#!/usr/bin/env python3
"""Preview/backfill Stableford across all leagues; preserve scores and both HCP histories."""
import argparse
from copy import deepcopy
from pathlib import Path
from import_players import load_store
from backfill_handicaps import backup
from league.handicaps import recalculate_handicaps, project_handicaps
from league.stableford import enabled, league_standings


def verify_preserved(before, after):
    """Only Stableford metadata/results may differ. No original entity is removed."""
    stripped=deepcopy(after)
    stripped.pop('stableford_version',None)
    stripped['revision']=before['revision']
    stripped['stableford_results']=deepcopy(before['stableford_results'])
    for collection,field in [('courses','stableford_difficulty'),('tournaments','stableford_difficulty')]:
        old={r['id']:r for r in before[collection]}
        if set(old)!={r['id'] for r in stripped[collection]}:
            raise ValueError('Entity identities changed: '+collection)
        for row in stripped[collection]:
            if field in old[row['id']]:
                previous=old[row['id']][field]
                current=row.get(field,{})
                if collection=='courses' and current!=previous:
                    raise ValueError('Existing course difficulty changed.')
                if collection=='tournaments' and any(current.get(k)!=v for k,v in previous.items()):
                    raise ValueError('Existing tournament difficulty snapshot changed.')
            row.pop(field,None)
            if field in old[row['id']]:row[field]=deepcopy(old[row['id']][field])
    if 'stableford_version' in before:stripped['stableford_version']=before['stableford_version']
    if stripped!=before:
        raise ValueError('Existing data/handicaps changed outside Stableford metadata.')
    old={(r['tournament_id'],r['player_id']):r for r in before['stableford_results']}
    if set(old)!={(r['tournament_id'],r['player_id']) for r in after['stableford_results']}:
        raise ValueError('Stableford entry identities changed.')
    target={t['id'] for t in before['tournaments'] if enabled(before,t['league_id'])}
    for result in after['stableford_results']:
        key=(result['tournament_id'],result['player_id'])
        if old[key].get('status')=='calculated' and result!=old[key]:
            raise ValueError('Existing calculated Stableford result changed.')
        if key[0] not in target and result!=old[key]:raise ValueError('Disabled league results changed.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    store=load_store(Path(__file__).resolve().parent/'.streamlit/secrets.toml','main')
    before,version=store.load()
    draft=recalculate_handicaps(before)
    verify_preserved(before,draft)
    view=project_handicaps(draft)
    calculated=[r for r in draft['stableford_results'] if r.get('status')=='calculated']
    print('Revision:',version,'calculated:',len(calculated),'active method:',draft['settings'].get('handicap_method','legacy'))
    for league in draft['leagues']:
        if enabled(draft,league['id']):
            print(league['name'])
            for row in league_standings(view,league['id']):
                print(row['Category'],row['Place'],row['Player'],row['Points'],row['Stableford'])
    if not args.apply:
        print('Preview only. No writes.');return
    if draft==before:
        print('Already current. No writes.');return
    print('Backup:',backup(before,'before-stableford-backfill'))
    store.save(draft,version)
    saved,new_version=store.load()
    verify_preserved(before,saved)
    if saved!=draft:raise ValueError('Readback differs from calculated payload.')
    print('Verified revision:',new_version,'snapshot:',backup(saved,'after-stableford-backfill'))


if __name__=='__main__':main()
