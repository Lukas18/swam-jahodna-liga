"""Generate the additive SQL migration from the shared record schema."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from league.relational import TABLES, KEYS

FK = [
 ('players',['category_code'],'categories',['code']),('layouts',['course_id'],'courses',['id']),
 ('layout_profiles',['layout_id'],'layouts',['id']),('layout_profiles',['category_code'],'categories',['code']),
 ('layout_holes',['layout_id','profile_key'],'layout_profiles',['layout_id','profile_key']),
 ('league_points',['league_id'],'leagues',['id']),('tournaments',['league_id'],'leagues',['id']),
 ('tournaments',['layout_id'],'layouts',['id']),('tournament_categories',['tournament_id'],'tournaments',['id']),
 ('tournament_categories',['category_code'],'categories',['code']),('tournament_entries',['tournament_id'],'tournaments',['id']),
 ('tournament_entries',['player_id'],'players',['id']),('tournament_entries',['tournament_id','category_code'],'tournament_categories',['tournament_id','category_code']),
 ('scorecards',['tournament_id','player_id'],'tournament_entries',['tournament_id','player_id']),
 ('scorecards',['tournament_id','category_code'],'tournament_categories',['tournament_id','category_code']),('scorecards',['layout_id'],'layouts',['id']),
 ('hole_scores',['scorecard_id'],'scorecards',['id']),('handicap_history',['run_id'],'handicap_runs',['id']),
 ('handicap_history',['player_id'],'players',['id']),('handicap_history',['tournament_id'],'tournaments',['id']),
 ('handicap_sources',['snapshot_id'],'handicap_history',['id']),('handicap_sources',['tournament_id'],'tournaments',['id']),
 ('stableford_results',['tournament_id','player_id'],'tournament_entries',['tournament_id','player_id']),
 ('stableford_results',['handicap_snapshot_id'],'handicap_history',['id']),('stableford_results',['source_run_id'],'handicap_runs',['id']),
 ('app_settings',['active_league_id'],'leagues',['id'])]
for table in ['players','tournament_entries','scorecards']:
 FK.append((table,['handicap_snapshot_id'],'handicap_history',['id']))
CHECKS={
 'layout_profiles':["(profile_key = 'default' AND category_code IS NULL) OR (profile_key <> 'default' AND profile_key = category_code)"],
 'layout_holes':['number > 0','par > 0','length >= 0'],
 'league_points':['place > 0','points >= 0'],
 'leagues':["points_scope IN ('category','overall')","tie_mode IN ('shared','same')"],
 'tournaments':['num_rounds BETWEEN 1 AND 20'],
 'scorecards':['round_number > 0','total > 0','par > 0'],
 'hole_scores':['number > 0','throws BETWEEN 1 AND 100','par > 0','length >= 0'],
 'handicap_history':['sample_count BETWEEN 1 AND 10'],
 'stableford_results':["status IN ('pending_formula','calculated','pending_inputs')", "(status = 'calculated' AND points IS NOT NULL AND calculation_version IS NOT NULL) OR (status <> 'calculated' AND points IS NULL)"]}
NOT_NULL={
 'players':['first_name','last_name','category_code','handicap','udisc'], 'courses':['name'], 'layouts':['course_id','name'],
 'layout_holes':['par','length'], 'leagues':['name','points_scope','tie_mode'], 'league_points':['points'],
 'tournaments':['name','date','league_id','layout_id','num_rounds'], 'tournament_categories':['position'],
 'tournament_entries':['category_code','handicap'], 'scorecards':['tournament_id','player_id','layout_id','round_number','category_code','handicap','total','par','recorded_at'],
 'hole_scores':['par','length','throws'], 'handicap_runs':['algorithm','source_revision'],
 'handicap_history':['run_id','player_id','tournament_id','date','event_score','handicap_used','handicap_after','sample_count','bootstrap'],
 'handicap_sources':['score','position'],'stableford_results':['status']}

def build():
 out=['-- ADDITIVE: never updates/deletes public.app_data. Run in Supabase SQL Editor.\nBEGIN;',
 'CREATE SCHEMA IF NOT EXISTS league_v2;',
 '''CREATE TABLE IF NOT EXISTS league_v2.documents (
 id text PRIMARY KEY, revision integer NOT NULL DEFAULT 0, schema_version integer NOT NULL,
 root_extra jsonb NOT NULL DEFAULT '{}'::jsonb, updated_at timestamptz NOT NULL DEFAULT now());''']
 for table,fields in TABLES.items():
  cols=['document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED']
  for key,typ in fields:
   required=key in KEYS[table] or key in NOT_NULL.get(table,[])
   cols.append(f'{key} {typ}'+(' NOT NULL' if required else ''))
  cols += ["extra jsonb NOT NULL DEFAULT '{}'::jsonb",'sort_order integer NOT NULL DEFAULT 0','archived boolean NOT NULL DEFAULT false',
           'PRIMARY KEY ('+', '.join(['document_id']+KEYS[table])+')']
  cols += ['CHECK ('+c+')' for c in CHECKS.get(table,[])]
  if table=='scorecards':cols.append('UNIQUE(document_id,tournament_id,player_id,round_number)')
  out.append(f'CREATE TABLE IF NOT EXISTS league_v2.{table} (\n '+',\n '.join(cols)+'\n);')
 for i,(table,cols,target,refs) in enumerate(FK):
  name=f'dg_fk_{i}_{table}'
  out.append(f"""DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='{name}' AND conrelid='league_v2.{table}'::regclass) THEN
 ALTER TABLE league_v2.{table} ADD CONSTRAINT {name} FOREIGN KEY ({','.join(['document_id']+cols)})
 REFERENCES league_v2.{target} ({','.join(['document_id']+refs)}) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;""")
 out += ["CREATE UNIQUE INDEX IF NOT EXISTS dg_unique_username ON league_v2.players(document_id, lower(btrim(udisc))) WHERE btrim(udisc) <> '' AND NOT archived;",
 "CREATE INDEX IF NOT EXISTS dg_events_date ON league_v2.tournaments(document_id,date);",
 "CREATE INDEX IF NOT EXISTS dg_history_player_date ON league_v2.handicap_history(document_id,player_id,date);",
 "CREATE INDEX IF NOT EXISTS dg_scorecards_tournament ON league_v2.scorecards(document_id,tournament_id);",
 "CREATE INDEX IF NOT EXISTS dg_scorecards_player ON league_v2.scorecards(document_id,player_id);"]
 # Only a server service role can call these RPCs; invoker privileges avoid a definer bypass.
 select=["'revision', d.revision", "'root', jsonb_build_object('schema_version',d.schema_version,'extra',d.root_extra)"]
 select += [f"'{t}', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.{t} x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb)" for t in TABLES]
 out.append("CREATE OR REPLACE FUNCTION public.dg_load(p_document_id text) RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $fn$\n SELECT jsonb_build_object("+',\n'.join(select)+") FROM league_v2.documents d WHERE d.id=p_document_id;\n$fn$;")
 body=["PERFORM pg_advisory_xact_lock(hashtextextended(p_document_id, 0));",
       "SELECT revision INTO current_revision FROM league_v2.documents WHERE id=p_document_id FOR UPDATE;",
       "IF FOUND THEN IF p_expected_revision IS NULL OR current_revision <> p_expected_revision THEN RETURN false; END IF; ELSE IF p_expected_revision IS NOT NULL THEN RETURN false; END IF; current_revision := 0; END IF;",
       "IF NOT (p_payload ? 'root') THEN RAISE EXCEPTION 'Missing root metadata'; END IF;"]
 for t in TABLES:body.append(f"IF jsonb_typeof(p_payload->'{t}') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid {t}'; END IF;")
 body += ["INSERT INTO league_v2.documents(id,revision,schema_version,root_extra) VALUES(p_document_id,current_revision+1,(p_payload->'root'->>'schema_version')::integer,COALESCE(p_payload->'root'->'extra','{}'::jsonb)) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,schema_version=excluded.schema_version,root_extra=excluded.root_extra,updated_at=now();"]
 for t,fields in TABLES.items():
  names=[k for k,_ in fields]+['extra','sort_order']
  keys=KEYS[t]
  match=' AND '.join(f't.{k}=x.{k}' for k in keys) or 'true'
  # Audit histories are retained; stale versions are archived, never deleted.
  body.append(f"UPDATE league_v2.{t} t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.{t}, p_payload->'{t}') x WHERE {match});")
  updates=[k for k in names if k not in keys]+['archived']
  body.append(f"INSERT INTO league_v2.{t} AS target (document_id,{','.join(names)},archived) SELECT p_document_id,{','.join('x.'+k for k in names)},false FROM jsonb_populate_recordset(NULL::league_v2.{t},p_payload->'{t}') x ON CONFLICT ({','.join(['document_id']+keys)}) DO UPDATE SET "+','.join(f'{k}=excluded.{k}' for k in updates)+f" WHERE ({','.join('target.'+k for k in updates)}) IS DISTINCT FROM ({','.join('excluded.'+k for k in updates)});")
 # Validate cross-table scorecard invariants inside the same transaction.
 body += ["""IF EXISTS (SELECT 1 FROM league_v2.scorecards s JOIN league_v2.tournaments t ON t.document_id=s.document_id AND t.id=s.tournament_id JOIN league_v2.tournament_entries e ON e.document_id=s.document_id AND e.tournament_id=s.tournament_id AND e.player_id=s.player_id WHERE s.document_id=p_document_id AND NOT s.archived AND (s.round_number > t.num_rounds OR s.layout_id <> t.layout_id OR s.category_code <> e.category_code OR s.handicap <> e.handicap)) THEN RAISE EXCEPTION 'Scorecard conflicts with tournament/entry'; END IF;""",
 """IF EXISTS (SELECT 1 FROM league_v2.scorecards s JOIN league_v2.hole_scores h ON h.document_id=s.document_id AND h.scorecard_id=s.id AND NOT h.archived WHERE s.document_id=p_document_id AND NOT s.archived GROUP BY s.id,s.total,s.par HAVING sum(h.throws) <> s.total OR sum(h.par) <> s.par) THEN RAISE EXCEPTION 'Scorecard totals do not match hole scores'; END IF;""",
 'RETURN true;']
 out.append("CREATE OR REPLACE FUNCTION public.dg_save(p_document_id text,p_expected_revision integer,p_payload jsonb) RETURNS boolean LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $fn$ DECLARE current_revision integer; BEGIN\n"+'\n'.join(body)+'\nEND; $fn$;')
 for t in ['documents']+list(TABLES):out.append(f'ALTER TABLE league_v2.{t} ENABLE ROW LEVEL SECURITY;')
 out += ['REVOKE ALL ON SCHEMA league_v2 FROM PUBLIC, anon, authenticated;',
 'REVOKE ALL ON ALL TABLES IN SCHEMA league_v2 FROM PUBLIC, anon, authenticated;',
 'GRANT USAGE ON SCHEMA league_v2 TO service_role;',
 'GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA league_v2 TO service_role;',
 'REVOKE ALL ON FUNCTION public.dg_load(text) FROM PUBLIC, anon, authenticated;',
 'REVOKE ALL ON FUNCTION public.dg_save(text,integer,jsonb) FROM PUBLIC, anon, authenticated;',
 'GRANT EXECUTE ON FUNCTION public.dg_load(text) TO service_role;',
 'GRANT EXECUTE ON FUNCTION public.dg_save(text,integer,jsonb) TO service_role;',
 "NOTIFY pgrst, 'reload schema';",'COMMIT;']
 return '\n\n'.join(out)+'\n'

if __name__=='__main__':
 Path(__file__).with_name('001_relational.sql').write_text(build())
