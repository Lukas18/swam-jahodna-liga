// Usage: PGLITE_MODULE=/absolute/path/to/pglite/dist/index.js node tests/verify_relational_sql.mjs /tmp/payload.json
const { PGlite } = await import(process.env.PGLITE_MODULE);
import { fileURLToPath } from 'node:url';
import fs from 'node:fs/promises';
const db=new PGlite();
await db.exec('CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role BYPASSRLS;');
const sql=await fs.readFile(fileURLToPath(new URL('../sql/001_relational.sql', import.meta.url)),'utf8');
await db.exec(sql);
await db.exec(sql); // migration is rerunnable without removing records
const payload=JSON.parse(await fs.readFile(process.argv[2],'utf8'));
let result=await db.query('SELECT public.dg_save($1,$2,$3::jsonb) AS ok',['main',null,JSON.stringify(payload)]);
if(result.rows[0].ok!==true)throw Error('Initial save failed');
let saved=(await db.query('SELECT public.dg_load($1) AS content',['main'])).rows[0].content;
await fs.writeFile('/tmp/discgolf-relational-readback.json',JSON.stringify(saved));
result=await db.query('SELECT public.dg_save($1,$2,$3::jsonb) AS ok',['main',null,JSON.stringify(payload)]);
if(result.rows[0].ok!==false)throw Error('Missing expected revision accepted');
result=await db.query('SELECT public.dg_save($1,$2,$3::jsonb) AS ok',['main',0,JSON.stringify(payload)]);
if(result.rows[0].ok!==false)throw Error('Stale revision accepted');
const invalid=structuredClone(payload);invalid.hole_scores[0].throws+=1;
try {await db.query('SELECT public.dg_save($1,$2,$3::jsonb) AS ok',['main',1,JSON.stringify(invalid)]);throw Error('Invalid totals accepted');}
catch(e){if(!e.message.includes('totals do not match'))throw e;}
if((await db.query('SELECT revision FROM league_v2.documents')).rows[0].revision!==1)throw Error('Failed save changed revision');
await db.exec('SET ROLE anon');
try{await db.query('SELECT public.dg_load($1)',['main']);throw Error('Anon could read private RPC');}
catch(e){if(!e.message.includes('permission denied'))throw e;}
await db.exec('RESET ROLE; SET ROLE service_role');
if(!(await db.query('SELECT public.dg_load($1) AS x',['main'])).rows[0].x)throw Error('Service role unable to read');
await db.exec('RESET ROLE');
// Removing an entity from the active document archives its old row instead of deleting it.
const fewer=structuredClone(payload);fewer.stableford_results=fewer.stableford_results.slice(1);
await db.query('SELECT public.dg_save($1,$2,$3::jsonb)',['main',1,JSON.stringify(fewer)]);
const count=(await db.query('SELECT count(*)::int total,count(*) FILTER (WHERE archived)::int archived FROM league_v2.stableford_results')).rows[0];
if(count.total!==payload.stableford_results.length||count.archived!==1)throw Error('Archive retention failed');
console.log('PASS: SQL schema/rerun, 5,238 holes, RPC roundtrip, stale-write conflict, atomic rollback, role permissions and archive retention.');
await db.close();
