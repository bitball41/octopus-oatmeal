import {build} from 'esbuild';
import {readFile, mkdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

const lock=JSON.parse(await readFile('vendor/upstream.json','utf8')).MultiplayerServer;
const archive=await readFile('vendor/'+lock.archive);
if(createHash('sha256').update(archive).digest('hex')!==lock.sha256) throw new Error('Server source checksum mismatch');
await mkdir('build/upstream-server',{recursive:true});
execFileSync('python',['-m','zipfile','-e','vendor/'+lock.archive,'build/upstream-server']);

const shims={
  'node:crypto': `export function randomBytes(n) { const bytes=crypto.getRandomValues(new Uint8Array(n)); return {toString(format){if(format!=='hex')throw new Error('Unsupported byte format');return Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('')}}; }`,
  uuid: (await readFile('browser/random.js','utf8')).replace('function randomId()', 'function v4()'),
  './abuse.js': `export function parseConnectionId(value){return /serversideConnectionID=([^;\\s]+)/.exec(value||'')?.[1]??null;}`,
  // Central log storage belongs to the public TCP service. Peer-hosted rooms
  // keep upstream replay files locally and do not upload logs to that service.
  './logHashStore.js': `export const recordLogHashes=()=>false; export const recordLiveLogLines=()=>{}; export const deleteLiveLog=()=>{};`,
};
const options={bundle:true,format:'esm',platform:'browser',target:'es2022',legalComments:'inline',plugins:[{
  name:'browser-platform',
  setup(b){
    b.onResolve({filter:/.*/},a=>Object.hasOwn(shims,a.path)?{path:a.path,namespace:'browser-platform'}:undefined);
    b.onLoad({filter:/.*/,namespace:'browser-platform'},a=>({contents:shims[a.path],loader:'js'}));
  }
}]};
await build({...options,entryPoints:['browser/server.js'],outfile:'browser/upstream-server.js'});
await build({...options,entryPoints:['browser/bridge.js'],outfile:'multiplayer_upstream.js'});
console.log('Built upstream server '+lock.commit);
