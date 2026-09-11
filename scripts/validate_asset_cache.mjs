import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
import {indexedDB, IDBObjectStore} from 'fake-indexeddb';
const helper = await readFile(new URL('../browser/asset-cache.js', import.meta.url), 'utf8');
let downloads = 0;
function context(idb = indexedDB) {
  const ctx = vm.createContext({indexedDB: idb, URL, Blob, document: {baseURI: 'https://game.example/'}, ASSET_REVISIONS: {'love.wasm': 'one'},
    fetch: async () => { downloads++; return new Response('asset'); }});
  vm.runInContext(helper, ctx);
  return ctx;
}
let ctx = context();
assert.equal(await (await ctx.cachedAsset('love.wasm')).text(), 'asset');
ctx = context(); // Simulated new page, same persisted database.
await ctx.cachedAsset('love.wasm');
assert.equal(downloads, 1);
ctx.ASSET_REVISIONS['love.wasm'] = 'two';
await ctx.cachedAsset('love.wasm');
assert.equal(downloads, 2);
const base = 'https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@';
await ctx.cachedAsset(base + 'a'.repeat(40) + '/love.js');
await context().cachedAsset(base + 'a'.repeat(40) + '/love.js');
assert.equal(downloads, 3);
await ctx.cachedAsset(base + 'b'.repeat(40) + '/love.js');
assert.equal(downloads, 4);
const db = await ctx.assetDB();
const count = await new Promise(resolve => {
  const request = db.transaction('assets').objectStore('assets').count();
  request.onsuccess = () => resolve(request.result);
});
assert.equal(count, 2, 'new revisions replace old data');
const put = IDBObjectStore.prototype.put;
IDBObjectStore.prototype.put = () => {throw new DOMException('Full', 'QuotaExceededError');};
ctx.ASSET_REVISIONS['love.wasm'] = 'three';
assert.equal(await (await ctx.cachedAsset('love.wasm')).text(), 'asset');
IDBObjectStore.prototype.put = put;
assert.equal(await (await context({open() {throw Error('Disabled');}}).cachedAsset('love.wasm')).text(), 'asset');

// Execute the shipped archive loaders, including the split Pokermon loader.
let network = 0;
async function launch(mode, altered = false) {
  const dir = mode === 'multiplayer' ? '' : mode + '/';
  let source = await readFile(new URL('../' + dir + 'game.js', import.meta.url), 'utf8');
  if (altered) source = source.replace(/package_uuid: "[^"]+"/, 'package_uuid: "updated"');
  const memory = new Uint8Array(40 * 1024 * 1024);
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(Error('Archive load stalled')), 3000);
    const Module = {persistenceDatabase: '/home/web_user/love-' + mode, calledRun: true,
      locateFile: p => dir + p, HEAPU8: memory, getMemory: () => 0,
      addRunDependency() {}, FS_createDataFile() {},
      removeRunDependency(name) { if (name === 'datafile_game.data') {clearTimeout(timeout);resolve();}}};
    class XHR {
      open() {} send() {network++;this.status=200;this.response=new ArrayBuffer(8);queueMicrotask(()=>this.onload());}
    }
    vm.runInNewContext(source, {Module, indexedDB, console, ArrayBuffer, Uint8Array,
      XMLHttpRequest: XHR, window:{indexedDB, encodeURIComponent, location:{pathname:'/index.html'}}});
  });
}
for (const mode of ['vanilla','bunco','paperback','pokermon','multiplayer']) await launch(mode);
assert.equal(network, 6); // Four single archives and two Pokermon parts.
for (const mode of ['vanilla','bunco','paperback','pokermon','multiplayer']) await launch(mode);
assert.equal(network, 6, 'switching modes must retain every cached archive');
await launch('bunco', true);
assert.equal(network, 7, 'changed package UUID downloads the updated archive');
console.log('Persistent assets, revisions, quota/disabled storage, five-mode reuse and split archive cache passed');
