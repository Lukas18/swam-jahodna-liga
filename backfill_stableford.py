#!/usr/bin/env python3
"""Preview/backfill Stableford across all leagues; preserve scores and HCP history."""
import argparse
from pathlib import Path
from import_players import load_store
from backfill_handicaps import backup, verify_source
from league.handicaps import recalculate_handicaps, project_handicaps
from league.stableford import enabled, league_standings


def verify_preserved(before, after):
    """Stableford and handicap outputs may change; source scores and difficulty may not."""
    verify_source(before, after)
    for collection in ('courses', 'tournaments'):
        old = {r['id']: r for r in before[collection]}
        current = {r['id']: r for r in after[collection]}
        if set(old) != set(current):
            raise ValueError(f'{collection} identities changed.')
        for rid, row in old.items():
            previous = row.get('stableford_difficulty')
            if previous is None:
                continue
            updated = current[rid].get('stableford_difficulty', {})
            if collection == 'courses' and updated != previous:
                raise ValueError('Existing course difficulty changed.')
            if collection == 'tournaments' and any(updated.get(k) != v for k, v in previous.items()):
                raise ValueError('Existing tournament difficulty snapshot changed.')


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
    print('Revision:',version,'calculated:',len(calculated),'handicap method: golf style')
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
