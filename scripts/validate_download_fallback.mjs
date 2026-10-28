import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
import {IDBFactory} from 'fake-indexeddb';
const helper=await readFile(new URL('../browser/asset-cache.js',import.meta.url),'utf8');
const ref='b7fbe2aa34b7818dc4b6574d88dd8a7e0a798e36';
const cdn=`https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@${ref}/`;
const raw=`https://raw.githubusercontent.com/bitball41/octopus-oatmeal/${ref}/`;
for(const path of ['custom-runtime.js','custom/manifest.json','custom/value-randomizer.lua','custom/packs/test.zip','love.wasm']){
 const calls=[];
 const ctx=vm.createContext({URL,Blob,ASSET_REVISIONS:{},indexedDB:new IDBFactory(),document:{baseURI:'https://game.example/'},
  fetch:async url=>{calls.push(url);return String(url).startsWith(cdn)?new Response('Forbidden',{status:403}):new Response('asset:'+path);}});
 vm.runInContext(helper,ctx);
 assert.equal(await (await ctx.cachedAsset(cdn+path)).text(),'asset:'+path);
 assert.deepEqual(calls,[cdn+path,raw+path]);
 await ctx.cachedAsset(cdn+path);assert.equal(calls.length,2,'cache must retain a successful fallback');
 assert.equal(ctx.archiveAssetURL(cdn+'cryptid/game.data.part1?v=test'),raw+'cryptid/game.data.part1?v=test');
 assert.equal(ctx.archiveAssetURL('vanilla/game.data'),'vanilla/game.data');
}
let calls=0;
const ctx=vm.createContext({window:{},warmupPromise:Promise.resolve({assetBase:cdn}),Promise,Error,
 loadScript:async()=>{if(++calls===1)throw Error('temporary failure');ctx.window.OctopusCustom={};}});
vm.runInContext(await readFile(new URL('../browser/mod-selector.js',import.meta.url),'utf8'),ctx);
await assert.rejects(ctx.customModule(),/temporary failure/);
await ctx.customModule();await ctx.customModule();assert.equal(calls,2,'a failed loader must be retryable and a successful one reused');
console.log('CDN 403 fallback: scripts, manifest, randomizer, pack and WASM preserve the commit, persist in cache and retry failed custom launches');
