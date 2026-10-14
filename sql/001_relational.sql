-- ADDITIVE: never updates/deletes public.app_data. Run in Supabase SQL Editor.
BEGIN;

CREATE SCHEMA IF NOT EXISTS league_v2;

CREATE TABLE IF NOT EXISTS league_v2.documents (
 id text PRIMARY KEY, revision integer NOT NULL DEFAULT 0, schema_version integer NOT NULL,
 root_extra jsonb NOT NULL DEFAULT '{}'::jsonb, updated_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE IF NOT EXISTS league_v2.categories (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 code text NOT NULL,
 position integer,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, code)
);

CREATE TABLE IF NOT EXISTS league_v2.players (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 id text NOT NULL,
 first_name text NOT NULL,
 last_name text NOT NULL,
 category_code text NOT NULL,
 handicap integer NOT NULL,
 udisc text NOT NULL,
 handicap_snapshot_id text,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, id)
);

CREATE TABLE IF NOT EXISTS league_v2.courses (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 id text NOT NULL,
 name text NOT NULL,
 description text,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, id)
);

CREATE TABLE IF NOT EXISTS league_v2.layouts (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 id text NOT NULL,
 course_id text NOT NULL,
 name text NOT NULL,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, id)
);

CREATE TABLE IF NOT EXISTS league_v2.layout_profiles (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 layout_id text NOT NULL,
 profile_key text NOT NULL,
 category_code text,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, layout_id, profile_key),
 CHECK ((profile_key = 'default' AND category_code IS NULL) OR (profile_key <> 'default' AND profile_key = category_code))
);

CREATE TABLE IF NOT EXISTS league_v2.layout_holes (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 layout_id text NOT NULL,
 profile_key text NOT NULL,
 number integer NOT NULL,
 par integer NOT NULL,
 length numeric NOT NULL,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, layout_id, profile_key, number),
 CHECK (number > 0),
 CHECK (par > 0),
 CHECK (length >= 0)
);

CREATE TABLE IF NOT EXISTS league_v2.leagues (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 id text NOT NULL,
 name text NOT NULL,
 points_scope text NOT NULL,
 tie_mode text NOT NULL,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, id),
 CHECK (points_scope IN ('category','overall')),
 CHECK (tie_mode IN ('shared','same'))
);

CREATE TABLE IF NOT EXISTS league_v2.league_points (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 league_id text NOT NULL,
 place integer NOT NULL,
 points integer NOT NULL,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, league_id, place),
 CHECK (place > 0),
 CHECK (points >= 0)
);

CREATE TABLE IF NOT EXISTS league_v2.tournaments (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 id text NOT NULL,
 name text NOT NULL,
 date date NOT NULL,
 league_id text NOT NULL,
 layout_id text NOT NULL,
 num_rounds integer NOT NULL,
 event_order integer,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, id),
 CHECK (num_rounds BETWEEN 1 AND 20)
);

CREATE TABLE IF NOT EXISTS league_v2.tournament_categories (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 tournament_id text NOT NULL,
 category_code text NOT NULL,
 position integer NOT NULL,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, tournament_id, category_code)
);

CREATE TABLE IF NOT EXISTS league_v2.tournament_entries (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 tournament_id text NOT NULL,
 player_id text NOT NULL,
 category_code text NOT NULL,
 handicap integer NOT NULL,
 handicap_snapshot_id text,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, tournament_id, player_id)
);

CREATE TABLE IF NOT EXISTS league_v2.scorecards (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 id text NOT NULL,
 tournament_id text NOT NULL,
 player_id text NOT NULL,
 layout_id text NOT NULL,
 round_number integer NOT NULL,
 category_code text NOT NULL,
 handicap integer NOT NULL,
 total integer NOT NULL,
 par integer NOT NULL,
 recorded_at timestamptz NOT NULL,
 handicap_snapshot_id text,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, id),
 CHECK (round_number > 0),
 CHECK (total > 0),
 CHECK (par > 0),
 UNIQUE(document_id,tournament_id,player_id,round_number)
);

CREATE TABLE IF NOT EXISTS league_v2.hole_scores (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 scorecard_id text NOT NULL,
 number integer NOT NULL,
 par integer NOT NULL,
 length numeric NOT NULL,
 throws integer NOT NULL,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, scorecard_id, number),
 CHECK (number > 0),
 CHECK (throws BETWEEN 1 AND 100),
 CHECK (par > 0),
 CHECK (length >= 0)
);

CREATE TABLE IF NOT EXISTS league_v2.handicap_runs (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 id text NOT NULL,
 algorithm text NOT NULL,
 source_revision integer NOT NULL,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, id)
);

CREATE TABLE IF NOT EXISTS league_v2.handicap_history (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 id text NOT NULL,
 run_id text NOT NULL,
 player_id text NOT NULL,
 tournament_id text NOT NULL,
 date date NOT NULL,
 event_order integer,
 event_score numeric NOT NULL,
 handicap_before integer,
 handicap_used integer NOT NULL,
 handicap_after integer NOT NULL,
 sample_count integer NOT NULL,
 bootstrap boolean NOT NULL,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, id),
 CHECK (sample_count BETWEEN 1 AND 10)
);

CREATE TABLE IF NOT EXISTS league_v2.handicap_sources (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 snapshot_id text NOT NULL,
 tournament_id text NOT NULL,
 score numeric NOT NULL,
 position integer NOT NULL,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, snapshot_id, tournament_id)
);

CREATE TABLE IF NOT EXISTS league_v2.stableford_results (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 tournament_id text NOT NULL,
 player_id text NOT NULL,
 points integer,
 status text NOT NULL,
 calculation_version text,
 handicap_snapshot_id text,
 source_run_id text,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id, tournament_id, player_id),
 CHECK (status IN ('pending_formula','calculated','pending_inputs')),
 CHECK ((status = 'calculated' AND points IS NOT NULL AND calculation_version IS NOT NULL) OR (status <> 'calculated' AND points IS NULL))
);

CREATE TABLE IF NOT EXISTS league_v2.app_settings (
 document_id text NOT NULL REFERENCES league_v2.documents(id) DEFERRABLE INITIALLY DEFERRED,
 site_title text,
 active_league_id text,
 extra jsonb NOT NULL DEFAULT '{}'::jsonb,
 sort_order integer NOT NULL DEFAULT 0,
 archived boolean NOT NULL DEFAULT false,
 PRIMARY KEY (document_id)
);

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_0_players' AND conrelid='league_v2.players'::regclass) THEN
 ALTER TABLE league_v2.players ADD CONSTRAINT dg_fk_0_players FOREIGN KEY (document_id,category_code)
 REFERENCES league_v2.categories (document_id,code) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_1_layouts' AND conrelid='league_v2.layouts'::regclass) THEN
 ALTER TABLE league_v2.layouts ADD CONSTRAINT dg_fk_1_layouts FOREIGN KEY (document_id,course_id)
 REFERENCES league_v2.courses (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_2_layout_profiles' AND conrelid='league_v2.layout_profiles'::regclass) THEN
 ALTER TABLE league_v2.layout_profiles ADD CONSTRAINT dg_fk_2_layout_profiles FOREIGN KEY (document_id,layout_id)
 REFERENCES league_v2.layouts (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_3_layout_profiles' AND conrelid='league_v2.layout_profiles'::regclass) THEN
 ALTER TABLE league_v2.layout_profiles ADD CONSTRAINT dg_fk_3_layout_profiles FOREIGN KEY (document_id,category_code)
 REFERENCES league_v2.categories (document_id,code) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_4_layout_holes' AND conrelid='league_v2.layout_holes'::regclass) THEN
 ALTER TABLE league_v2.layout_holes ADD CONSTRAINT dg_fk_4_layout_holes FOREIGN KEY (document_id,layout_id,profile_key)
 REFERENCES league_v2.layout_profiles (document_id,layout_id,profile_key) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_5_league_points' AND conrelid='league_v2.league_points'::regclass) THEN
 ALTER TABLE league_v2.league_points ADD CONSTRAINT dg_fk_5_league_points FOREIGN KEY (document_id,league_id)
 REFERENCES league_v2.leagues (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_6_tournaments' AND conrelid='league_v2.tournaments'::regclass) THEN
 ALTER TABLE league_v2.tournaments ADD CONSTRAINT dg_fk_6_tournaments FOREIGN KEY (document_id,league_id)
 REFERENCES league_v2.leagues (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_7_tournaments' AND conrelid='league_v2.tournaments'::regclass) THEN
 ALTER TABLE league_v2.tournaments ADD CONSTRAINT dg_fk_7_tournaments FOREIGN KEY (document_id,layout_id)
 REFERENCES league_v2.layouts (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_8_tournament_categories' AND conrelid='league_v2.tournament_categories'::regclass) THEN
 ALTER TABLE league_v2.tournament_categories ADD CONSTRAINT dg_fk_8_tournament_categories FOREIGN KEY (document_id,tournament_id)
 REFERENCES league_v2.tournaments (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_9_tournament_categories' AND conrelid='league_v2.tournament_categories'::regclass) THEN
 ALTER TABLE league_v2.tournament_categories ADD CONSTRAINT dg_fk_9_tournament_categories FOREIGN KEY (document_id,category_code)
 REFERENCES league_v2.categories (document_id,code) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_10_tournament_entries' AND conrelid='league_v2.tournament_entries'::regclass) THEN
 ALTER TABLE league_v2.tournament_entries ADD CONSTRAINT dg_fk_10_tournament_entries FOREIGN KEY (document_id,tournament_id)
 REFERENCES league_v2.tournaments (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_11_tournament_entries' AND conrelid='league_v2.tournament_entries'::regclass) THEN
 ALTER TABLE league_v2.tournament_entries ADD CONSTRAINT dg_fk_11_tournament_entries FOREIGN KEY (document_id,player_id)
 REFERENCES league_v2.players (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_12_tournament_entries' AND conrelid='league_v2.tournament_entries'::regclass) THEN
 ALTER TABLE league_v2.tournament_entries ADD CONSTRAINT dg_fk_12_tournament_entries FOREIGN KEY (document_id,tournament_id,category_code)
 REFERENCES league_v2.tournament_categories (document_id,tournament_id,category_code) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_13_scorecards' AND conrelid='league_v2.scorecards'::regclass) THEN
 ALTER TABLE league_v2.scorecards ADD CONSTRAINT dg_fk_13_scorecards FOREIGN KEY (document_id,tournament_id,player_id)
 REFERENCES league_v2.tournament_entries (document_id,tournament_id,player_id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_14_scorecards' AND conrelid='league_v2.scorecards'::regclass) THEN
 ALTER TABLE league_v2.scorecards ADD CONSTRAINT dg_fk_14_scorecards FOREIGN KEY (document_id,tournament_id,category_code)
 REFERENCES league_v2.tournament_categories (document_id,tournament_id,category_code) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_15_scorecards' AND conrelid='league_v2.scorecards'::regclass) THEN
 ALTER TABLE league_v2.scorecards ADD CONSTRAINT dg_fk_15_scorecards FOREIGN KEY (document_id,layout_id)
 REFERENCES league_v2.layouts (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_16_hole_scores' AND conrelid='league_v2.hole_scores'::regclass) THEN
 ALTER TABLE league_v2.hole_scores ADD CONSTRAINT dg_fk_16_hole_scores FOREIGN KEY (document_id,scorecard_id)
 REFERENCES league_v2.scorecards (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_17_handicap_history' AND conrelid='league_v2.handicap_history'::regclass) THEN
 ALTER TABLE league_v2.handicap_history ADD CONSTRAINT dg_fk_17_handicap_history FOREIGN KEY (document_id,run_id)
 REFERENCES league_v2.handicap_runs (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_18_handicap_history' AND conrelid='league_v2.handicap_history'::regclass) THEN
 ALTER TABLE league_v2.handicap_history ADD CONSTRAINT dg_fk_18_handicap_history FOREIGN KEY (document_id,player_id)
 REFERENCES league_v2.players (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_19_handicap_history' AND conrelid='league_v2.handicap_history'::regclass) THEN
 ALTER TABLE league_v2.handicap_history ADD CONSTRAINT dg_fk_19_handicap_history FOREIGN KEY (document_id,tournament_id)
 REFERENCES league_v2.tournaments (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_20_handicap_sources' AND conrelid='league_v2.handicap_sources'::regclass) THEN
 ALTER TABLE league_v2.handicap_sources ADD CONSTRAINT dg_fk_20_handicap_sources FOREIGN KEY (document_id,snapshot_id)
 REFERENCES league_v2.handicap_history (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_21_handicap_sources' AND conrelid='league_v2.handicap_sources'::regclass) THEN
 ALTER TABLE league_v2.handicap_sources ADD CONSTRAINT dg_fk_21_handicap_sources FOREIGN KEY (document_id,tournament_id)
 REFERENCES league_v2.tournaments (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_22_stableford_results' AND conrelid='league_v2.stableford_results'::regclass) THEN
 ALTER TABLE league_v2.stableford_results ADD CONSTRAINT dg_fk_22_stableford_results FOREIGN KEY (document_id,tournament_id,player_id)
 REFERENCES league_v2.tournament_entries (document_id,tournament_id,player_id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_23_stableford_results' AND conrelid='league_v2.stableford_results'::regclass) THEN
 ALTER TABLE league_v2.stableford_results ADD CONSTRAINT dg_fk_23_stableford_results FOREIGN KEY (document_id,handicap_snapshot_id)
 REFERENCES league_v2.handicap_history (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_24_stableford_results' AND conrelid='league_v2.stableford_results'::regclass) THEN
 ALTER TABLE league_v2.stableford_results ADD CONSTRAINT dg_fk_24_stableford_results FOREIGN KEY (document_id,source_run_id)
 REFERENCES league_v2.handicap_runs (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_25_app_settings' AND conrelid='league_v2.app_settings'::regclass) THEN
 ALTER TABLE league_v2.app_settings ADD CONSTRAINT dg_fk_25_app_settings FOREIGN KEY (document_id,active_league_id)
 REFERENCES league_v2.leagues (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_26_players' AND conrelid='league_v2.players'::regclass) THEN
 ALTER TABLE league_v2.players ADD CONSTRAINT dg_fk_26_players FOREIGN KEY (document_id,handicap_snapshot_id)
 REFERENCES league_v2.handicap_history (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_27_tournament_entries' AND conrelid='league_v2.tournament_entries'::regclass) THEN
 ALTER TABLE league_v2.tournament_entries ADD CONSTRAINT dg_fk_27_tournament_entries FOREIGN KEY (document_id,handicap_snapshot_id)
 REFERENCES league_v2.handicap_history (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

DO $do$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='dg_fk_28_scorecards' AND conrelid='league_v2.scorecards'::regclass) THEN
 ALTER TABLE league_v2.scorecards ADD CONSTRAINT dg_fk_28_scorecards FOREIGN KEY (document_id,handicap_snapshot_id)
 REFERENCES league_v2.handicap_history (document_id,id) DEFERRABLE INITIALLY DEFERRED;
 END IF; END $do$;

CREATE UNIQUE INDEX IF NOT EXISTS dg_unique_username ON league_v2.players(document_id, lower(btrim(udisc))) WHERE btrim(udisc) <> '' AND NOT archived;

CREATE INDEX IF NOT EXISTS dg_events_date ON league_v2.tournaments(document_id,date);

CREATE INDEX IF NOT EXISTS dg_history_player_date ON league_v2.handicap_history(document_id,player_id,date);

CREATE INDEX IF NOT EXISTS dg_scorecards_tournament ON league_v2.scorecards(document_id,tournament_id);

CREATE INDEX IF NOT EXISTS dg_scorecards_player ON league_v2.scorecards(document_id,player_id);

CREATE OR REPLACE FUNCTION public.dg_load(p_document_id text) RETURNS jsonb LANGUAGE sql STABLE SECURITY INVOKER SET search_path='' AS $fn$
 SELECT jsonb_build_object('revision', d.revision,
'root', jsonb_build_object('schema_version',d.schema_version,'extra',d.root_extra),
'categories', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.categories x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'players', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.players x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'courses', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.courses x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'layouts', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.layouts x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'layout_profiles', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.layout_profiles x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'layout_holes', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.layout_holes x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'leagues', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.leagues x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'league_points', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.league_points x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'tournaments', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.tournaments x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'tournament_categories', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.tournament_categories x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'tournament_entries', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.tournament_entries x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'scorecards', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.scorecards x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'hole_scores', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.hole_scores x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'handicap_runs', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.handicap_runs x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'handicap_history', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.handicap_history x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'handicap_sources', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.handicap_sources x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'stableford_results', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.stableford_results x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb),
'app_settings', COALESCE((SELECT jsonb_agg(to_jsonb(x) - 'document_id' - 'archived' ORDER BY x.sort_order) FROM league_v2.app_settings x WHERE x.document_id=d.id AND NOT x.archived),'[]'::jsonb)) FROM league_v2.documents d WHERE d.id=p_document_id;
$fn$;

CREATE OR REPLACE FUNCTION public.dg_save(p_document_id text,p_expected_revision integer,p_payload jsonb) RETURNS boolean LANGUAGE plpgsql SECURITY INVOKER SET search_path='' AS $fn$ DECLARE current_revision integer; BEGIN
PERFORM pg_advisory_xact_lock(hashtextextended(p_document_id, 0));
SELECT revision INTO current_revision FROM league_v2.documents WHERE id=p_document_id FOR UPDATE;
IF FOUND THEN IF p_expected_revision IS NULL OR current_revision <> p_expected_revision THEN RETURN false; END IF; ELSE IF p_expected_revision IS NOT NULL THEN RETURN false; END IF; current_revision := 0; END IF;
IF NOT (p_payload ? 'root') THEN RAISE EXCEPTION 'Missing root metadata'; END IF;
IF jsonb_typeof(p_payload->'categories') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid categories'; END IF;
IF jsonb_typeof(p_payload->'players') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid players'; END IF;
IF jsonb_typeof(p_payload->'courses') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid courses'; END IF;
IF jsonb_typeof(p_payload->'layouts') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid layouts'; END IF;
IF jsonb_typeof(p_payload->'layout_profiles') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid layout_profiles'; END IF;
IF jsonb_typeof(p_payload->'layout_holes') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid layout_holes'; END IF;
IF jsonb_typeof(p_payload->'leagues') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid leagues'; END IF;
IF jsonb_typeof(p_payload->'league_points') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid league_points'; END IF;
IF jsonb_typeof(p_payload->'tournaments') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid tournaments'; END IF;
IF jsonb_typeof(p_payload->'tournament_categories') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid tournament_categories'; END IF;
IF jsonb_typeof(p_payload->'tournament_entries') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid tournament_entries'; END IF;
IF jsonb_typeof(p_payload->'scorecards') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid scorecards'; END IF;
IF jsonb_typeof(p_payload->'hole_scores') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid hole_scores'; END IF;
IF jsonb_typeof(p_payload->'handicap_runs') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid handicap_runs'; END IF;
IF jsonb_typeof(p_payload->'handicap_history') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid handicap_history'; END IF;
IF jsonb_typeof(p_payload->'handicap_sources') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid handicap_sources'; END IF;
IF jsonb_typeof(p_payload->'stableford_results') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid stableford_results'; END IF;
IF jsonb_typeof(p_payload->'app_settings') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Missing/invalid app_settings'; END IF;
INSERT INTO league_v2.documents(id,revision,schema_version,root_extra) VALUES(p_document_id,current_revision+1,(p_payload->'root'->>'schema_version')::integer,COALESCE(p_payload->'root'->'extra','{}'::jsonb)) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,schema_version=excluded.schema_version,root_extra=excluded.root_extra,updated_at=now();
UPDATE league_v2.categories t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.categories, p_payload->'categories') x WHERE t.code=x.code);
INSERT INTO league_v2.categories AS target (document_id,code,position,extra,sort_order,archived) SELECT p_document_id,x.code,x.position,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.categories,p_payload->'categories') x ON CONFLICT (document_id,code) DO UPDATE SET position=excluded.position,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.position,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.position,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.players t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.players, p_payload->'players') x WHERE t.id=x.id);
INSERT INTO league_v2.players AS target (document_id,id,first_name,last_name,category_code,handicap,udisc,handicap_snapshot_id,extra,sort_order,archived) SELECT p_document_id,x.id,x.first_name,x.last_name,x.category_code,x.handicap,x.udisc,x.handicap_snapshot_id,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.players,p_payload->'players') x ON CONFLICT (document_id,id) DO UPDATE SET first_name=excluded.first_name,last_name=excluded.last_name,category_code=excluded.category_code,handicap=excluded.handicap,udisc=excluded.udisc,handicap_snapshot_id=excluded.handicap_snapshot_id,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.first_name,target.last_name,target.category_code,target.handicap,target.udisc,target.handicap_snapshot_id,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.first_name,excluded.last_name,excluded.category_code,excluded.handicap,excluded.udisc,excluded.handicap_snapshot_id,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.courses t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.courses, p_payload->'courses') x WHERE t.id=x.id);
INSERT INTO league_v2.courses AS target (document_id,id,name,description,extra,sort_order,archived) SELECT p_document_id,x.id,x.name,x.description,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.courses,p_payload->'courses') x ON CONFLICT (document_id,id) DO UPDATE SET name=excluded.name,description=excluded.description,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.name,target.description,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.name,excluded.description,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.layouts t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.layouts, p_payload->'layouts') x WHERE t.id=x.id);
INSERT INTO league_v2.layouts AS target (document_id,id,course_id,name,extra,sort_order,archived) SELECT p_document_id,x.id,x.course_id,x.name,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.layouts,p_payload->'layouts') x ON CONFLICT (document_id,id) DO UPDATE SET course_id=excluded.course_id,name=excluded.name,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.course_id,target.name,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.course_id,excluded.name,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.layout_profiles t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.layout_profiles, p_payload->'layout_profiles') x WHERE t.layout_id=x.layout_id AND t.profile_key=x.profile_key);
INSERT INTO league_v2.layout_profiles AS target (document_id,layout_id,profile_key,category_code,extra,sort_order,archived) SELECT p_document_id,x.layout_id,x.profile_key,x.category_code,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.layout_profiles,p_payload->'layout_profiles') x ON CONFLICT (document_id,layout_id,profile_key) DO UPDATE SET category_code=excluded.category_code,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.category_code,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.category_code,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.layout_holes t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.layout_holes, p_payload->'layout_holes') x WHERE t.layout_id=x.layout_id AND t.profile_key=x.profile_key AND t.number=x.number);
INSERT INTO league_v2.layout_holes AS target (document_id,layout_id,profile_key,number,par,length,extra,sort_order,archived) SELECT p_document_id,x.layout_id,x.profile_key,x.number,x.par,x.length,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.layout_holes,p_payload->'layout_holes') x ON CONFLICT (document_id,layout_id,profile_key,number) DO UPDATE SET par=excluded.par,length=excluded.length,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.par,target.length,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.par,excluded.length,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.leagues t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.leagues, p_payload->'leagues') x WHERE t.id=x.id);
INSERT INTO league_v2.leagues AS target (document_id,id,name,points_scope,tie_mode,extra,sort_order,archived) SELECT p_document_id,x.id,x.name,x.points_scope,x.tie_mode,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.leagues,p_payload->'leagues') x ON CONFLICT (document_id,id) DO UPDATE SET name=excluded.name,points_scope=excluded.points_scope,tie_mode=excluded.tie_mode,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.name,target.points_scope,target.tie_mode,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.name,excluded.points_scope,excluded.tie_mode,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.league_points t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.league_points, p_payload->'league_points') x WHERE t.league_id=x.league_id AND t.place=x.place);
INSERT INTO league_v2.league_points AS target (document_id,league_id,place,points,extra,sort_order,archived) SELECT p_document_id,x.league_id,x.place,x.points,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.league_points,p_payload->'league_points') x ON CONFLICT (document_id,league_id,place) DO UPDATE SET points=excluded.points,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.points,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.points,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.tournaments t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.tournaments, p_payload->'tournaments') x WHERE t.id=x.id);
INSERT INTO league_v2.tournaments AS target (document_id,id,name,date,league_id,layout_id,num_rounds,event_order,extra,sort_order,archived) SELECT p_document_id,x.id,x.name,x.date,x.league_id,x.layout_id,x.num_rounds,x.event_order,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.tournaments,p_payload->'tournaments') x ON CONFLICT (document_id,id) DO UPDATE SET name=excluded.name,date=excluded.date,league_id=excluded.league_id,layout_id=excluded.layout_id,num_rounds=excluded.num_rounds,event_order=excluded.event_order,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.name,target.date,target.league_id,target.layout_id,target.num_rounds,target.event_order,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.name,excluded.date,excluded.league_id,excluded.layout_id,excluded.num_rounds,excluded.event_order,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.tournament_categories t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.tournament_categories, p_payload->'tournament_categories') x WHERE t.tournament_id=x.tournament_id AND t.category_code=x.category_code);
INSERT INTO league_v2.tournament_categories AS target (document_id,tournament_id,category_code,position,extra,sort_order,archived) SELECT p_document_id,x.tournament_id,x.category_code,x.position,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.tournament_categories,p_payload->'tournament_categories') x ON CONFLICT (document_id,tournament_id,category_code) DO UPDATE SET position=excluded.position,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.position,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.position,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.tournament_entries t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.tournament_entries, p_payload->'tournament_entries') x WHERE t.tournament_id=x.tournament_id AND t.player_id=x.player_id);
INSERT INTO league_v2.tournament_entries AS target (document_id,tournament_id,player_id,category_code,handicap,handicap_snapshot_id,extra,sort_order,archived) SELECT p_document_id,x.tournament_id,x.player_id,x.category_code,x.handicap,x.handicap_snapshot_id,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.tournament_entries,p_payload->'tournament_entries') x ON CONFLICT (document_id,tournament_id,player_id) DO UPDATE SET category_code=excluded.category_code,handicap=excluded.handicap,handicap_snapshot_id=excluded.handicap_snapshot_id,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.category_code,target.handicap,target.handicap_snapshot_id,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.category_code,excluded.handicap,excluded.handicap_snapshot_id,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.scorecards t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.scorecards, p_payload->'scorecards') x WHERE t.id=x.id);
INSERT INTO league_v2.scorecards AS target (document_id,id,tournament_id,player_id,layout_id,round_number,category_code,handicap,total,par,recorded_at,handicap_snapshot_id,extra,sort_order,archived) SELECT p_document_id,x.id,x.tournament_id,x.player_id,x.layout_id,x.round_number,x.category_code,x.handicap,x.total,x.par,x.recorded_at,x.handicap_snapshot_id,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.scorecards,p_payload->'scorecards') x ON CONFLICT (document_id,id) DO UPDATE SET tournament_id=excluded.tournament_id,player_id=excluded.player_id,layout_id=excluded.layout_id,round_number=excluded.round_number,category_code=excluded.category_code,handicap=excluded.handicap,total=excluded.total,par=excluded.par,recorded_at=excluded.recorded_at,handicap_snapshot_id=excluded.handicap_snapshot_id,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.tournament_id,target.player_id,target.layout_id,target.round_number,target.category_code,target.handicap,target.total,target.par,target.recorded_at,target.handicap_snapshot_id,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.tournament_id,excluded.player_id,excluded.layout_id,excluded.round_number,excluded.category_code,excluded.handicap,excluded.total,excluded.par,excluded.recorded_at,excluded.handicap_snapshot_id,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.hole_scores t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.hole_scores, p_payload->'hole_scores') x WHERE t.scorecard_id=x.scorecard_id AND t.number=x.number);
INSERT INTO league_v2.hole_scores AS target (document_id,scorecard_id,number,par,length,throws,extra,sort_order,archived) SELECT p_document_id,x.scorecard_id,x.number,x.par,x.length,x.throws,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.hole_scores,p_payload->'hole_scores') x ON CONFLICT (document_id,scorecard_id,number) DO UPDATE SET par=excluded.par,length=excluded.length,throws=excluded.throws,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.par,target.length,target.throws,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.par,excluded.length,excluded.throws,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.handicap_runs t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.handicap_runs, p_payload->'handicap_runs') x WHERE t.id=x.id);
INSERT INTO league_v2.handicap_runs AS target (document_id,id,algorithm,source_revision,extra,sort_order,archived) SELECT p_document_id,x.id,x.algorithm,x.source_revision,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.handicap_runs,p_payload->'handicap_runs') x ON CONFLICT (document_id,id) DO UPDATE SET algorithm=excluded.algorithm,source_revision=excluded.source_revision,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.algorithm,target.source_revision,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.algorithm,excluded.source_revision,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.handicap_history t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.handicap_history, p_payload->'handicap_history') x WHERE t.id=x.id);
INSERT INTO league_v2.handicap_history AS target (document_id,id,run_id,player_id,tournament_id,date,event_order,event_score,handicap_before,handicap_used,handicap_after,sample_count,bootstrap,extra,sort_order,archived) SELECT p_document_id,x.id,x.run_id,x.player_id,x.tournament_id,x.date,x.event_order,x.event_score,x.handicap_before,x.handicap_used,x.handicap_after,x.sample_count,x.bootstrap,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.handicap_history,p_payload->'handicap_history') x ON CONFLICT (document_id,id) DO UPDATE SET run_id=excluded.run_id,player_id=excluded.player_id,tournament_id=excluded.tournament_id,date=excluded.date,event_order=excluded.event_order,event_score=excluded.event_score,handicap_before=excluded.handicap_before,handicap_used=excluded.handicap_used,handicap_after=excluded.handicap_after,sample_count=excluded.sample_count,bootstrap=excluded.bootstrap,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.run_id,target.player_id,target.tournament_id,target.date,target.event_order,target.event_score,target.handicap_before,target.handicap_used,target.handicap_after,target.sample_count,target.bootstrap,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.run_id,excluded.player_id,excluded.tournament_id,excluded.date,excluded.event_order,excluded.event_score,excluded.handicap_before,excluded.handicap_used,excluded.handicap_after,excluded.sample_count,excluded.bootstrap,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.handicap_sources t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.handicap_sources, p_payload->'handicap_sources') x WHERE t.snapshot_id=x.snapshot_id AND t.tournament_id=x.tournament_id);
INSERT INTO league_v2.handicap_sources AS target (document_id,snapshot_id,tournament_id,score,position,extra,sort_order,archived) SELECT p_document_id,x.snapshot_id,x.tournament_id,x.score,x.position,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.handicap_sources,p_payload->'handicap_sources') x ON CONFLICT (document_id,snapshot_id,tournament_id) DO UPDATE SET score=excluded.score,position=excluded.position,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.score,target.position,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.score,excluded.position,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.stableford_results t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.stableford_results, p_payload->'stableford_results') x WHERE t.tournament_id=x.tournament_id AND t.player_id=x.player_id);
INSERT INTO league_v2.stableford_results AS target (document_id,tournament_id,player_id,points,status,calculation_version,handicap_snapshot_id,source_run_id,extra,sort_order,archived) SELECT p_document_id,x.tournament_id,x.player_id,x.points,x.status,x.calculation_version,x.handicap_snapshot_id,x.source_run_id,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.stableford_results,p_payload->'stableford_results') x ON CONFLICT (document_id,tournament_id,player_id) DO UPDATE SET points=excluded.points,status=excluded.status,calculation_version=excluded.calculation_version,handicap_snapshot_id=excluded.handicap_snapshot_id,source_run_id=excluded.source_run_id,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.points,target.status,target.calculation_version,target.handicap_snapshot_id,target.source_run_id,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.points,excluded.status,excluded.calculation_version,excluded.handicap_snapshot_id,excluded.source_run_id,excluded.extra,excluded.sort_order,excluded.archived);
UPDATE league_v2.app_settings t SET archived=true WHERE t.document_id=p_document_id AND NOT t.archived AND NOT EXISTS (SELECT 1 FROM jsonb_populate_recordset(NULL::league_v2.app_settings, p_payload->'app_settings') x WHERE true);
INSERT INTO league_v2.app_settings AS target (document_id,site_title,active_league_id,extra,sort_order,archived) SELECT p_document_id,x.site_title,x.active_league_id,x.extra,x.sort_order,false FROM jsonb_populate_recordset(NULL::league_v2.app_settings,p_payload->'app_settings') x ON CONFLICT (document_id) DO UPDATE SET site_title=excluded.site_title,active_league_id=excluded.active_league_id,extra=excluded.extra,sort_order=excluded.sort_order,archived=excluded.archived WHERE (target.site_title,target.active_league_id,target.extra,target.sort_order,target.archived) IS DISTINCT FROM (excluded.site_title,excluded.active_league_id,excluded.extra,excluded.sort_order,excluded.archived);
IF EXISTS (SELECT 1 FROM league_v2.scorecards s JOIN league_v2.tournaments t ON t.document_id=s.document_id AND t.id=s.tournament_id JOIN league_v2.tournament_entries e ON e.document_id=s.document_id AND e.tournament_id=s.tournament_id AND e.player_id=s.player_id WHERE s.document_id=p_document_id AND NOT s.archived AND (s.round_number > t.num_rounds OR s.layout_id <> t.layout_id OR s.category_code <> e.category_code OR s.handicap <> e.handicap)) THEN RAISE EXCEPTION 'Scorecard conflicts with tournament/entry'; END IF;
IF EXISTS (SELECT 1 FROM league_v2.scorecards s JOIN league_v2.hole_scores h ON h.document_id=s.document_id AND h.scorecard_id=s.id AND NOT h.archived WHERE s.document_id=p_document_id AND NOT s.archived GROUP BY s.id,s.total,s.par HAVING sum(h.throws) <> s.total OR sum(h.par) <> s.par) THEN RAISE EXCEPTION 'Scorecard totals do not match hole scores'; END IF;
RETURN true;
END; $fn$;

ALTER TABLE league_v2.documents ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.categories ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.players ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.courses ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.layouts ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.layout_profiles ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.layout_holes ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.leagues ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.league_points ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.tournaments ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.tournament_categories ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.tournament_entries ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.scorecards ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.hole_scores ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.handicap_runs ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.handicap_history ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.handicap_sources ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.stableford_results ENABLE ROW LEVEL SECURITY;

ALTER TABLE league_v2.app_settings ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON SCHEMA league_v2 FROM PUBLIC, anon, authenticated;

REVOKE ALL ON ALL TABLES IN SCHEMA league_v2 FROM PUBLIC, anon, authenticated;

GRANT USAGE ON SCHEMA league_v2 TO service_role;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA league_v2 TO service_role;

REVOKE ALL ON FUNCTION public.dg_load(text) FROM PUBLIC, anon, authenticated;

REVOKE ALL ON FUNCTION public.dg_save(text,integer,jsonb) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.dg_load(text) TO service_role;

GRANT EXECUTE ON FUNCTION public.dg_save(text,integer,jsonb) TO service_role;

NOTIFY pgrst, 'reload schema';

COMMIT;
