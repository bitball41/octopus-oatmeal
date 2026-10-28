// Run the shipped WASM, save restore and archive loader together. Rendering is
// skipped so the startup dependency checks can also run without a GPU/browser.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {IDBFactory} from 'fake-indexeddb';

const [engine, loader, wasm, archive] = await Promise.all(
  ['love.js', 'game.js', 'love.wasm', 'game.data'].map(path =>
    readFile(new URL('../' + path, import.meta.url))),
);
const saveName = '/home/web_user/love';
const savePath = saveName + '/profile.jkr';
const original = new TextEncoder().encode('existing multiplayer progress');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(check, label) {
  const end = Date.now() + 3000;
  while (!check()) {
    if (Date.now() > end) throw new Error('Timed out: ' + label);
    await sleep(5);
  }
}
function open(factory, name, version) {
  return new Promise((resolve, reject) => {
    const request = version ? factory.open(name, version) : factory.open(name);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains('FILE_DATA')) {
        request.result.createObjectStore('FILE_DATA')
          .createIndex('timestamp', 'timestamp', {unique: false});
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
async function seed(factory, version) {
  const db = await open(factory, saveName, version);
  await new Promise((resolve, reject) => {
    const tx = db.transaction('FILE_DATA', 'readwrite');
    tx.objectStore('FILE_DATA').put({timestamp: new Date(), mode: 0o100666, contents: original}, savePath);
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
  return db;
}
function saved(db, path = savePath) {
  return new Promise((resolve, reject) => {
    const request = db.transaction('FILE_DATA').objectStore('FILE_DATA').get(path);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
async function boot(idb) {
  class XHR {
    open() {}
    send() {
      this.status = 200;
      this.response = archive.buffer.slice(archive.byteOffset, archive.byteOffset + archive.byteLength);
      queueMicrotask(() => this.onload());
    }
  }
  const context = vm.createContext({
    indexedDB: idb, WebAssembly, TextEncoder, TextDecoder, URL, crypto, performance,
    ArrayBuffer, Uint8Array, Int8Array, Uint16Array, Int16Array, Uint32Array, Int32Array, Float32Array, Float64Array,
    XMLHttpRequest: XHR, console: {log() {}, info() {}, warn() {}, error() {}},
    // Accelerate only long guards; callbacks otherwise keep their real order.
    setTimeout: (fn, ms) => setTimeout(fn, Math.min(ms, 250)), clearTimeout,
    setInterval() {}, clearInterval() {},
    document: {currentScript: {src: 'https://game.example/love.js'}, addEventListener() {}},
    navigator: {userAgent: 'startup-test'},
    location: {href: 'https://game.example/index.html', pathname: '/index.html'},
    addEventListener() {}, encodeURIComponent,
  });
  context.window = context; context.self = context;
  const module = context.Module = {
    INITIAL_MEMORY: 256000000, noInitialRun: true, persistenceDatabase: saveName,
    wasmBinary: wasm.buffer.slice(wasm.byteOffset, wasm.byteOffset + wasm.byteLength),
    locateFile: path => 'https://game.example/' + path,
    printErr() {}, setStatus() {},
    monitorRunDependencies(left) {this.remainingDependencies = left;},
  };
  vm.runInContext(loader.toString(), context);
  vm.runInContext(engine.toString(), context);
  let timer;
  try {
    await Promise.race([
      vm.runInContext('Love(Module)', context),
      new Promise((_, reject) => {timer = setTimeout(() => reject(new Error('Preparing stalled: ' + JSON.stringify(module.persistence))), 3000);}),
    ]);
  } finally {clearTimeout(timer);}
  assert.equal(module.remainingDependencies, 0);
  assert.equal(module.calledRun, true);
  assert.equal(module.finishedDataFileDownloads, 1);
  return module;
}

for (const version of [null, 1, 21, 22]) {
  const factory = new IDBFactory();
  // Keep the old connection OPEN: the original forced version-21 open hangs
  // here, exactly one of the two startup dependencies remains unresolved.
  const held = version ? await seed(factory, version) : null;
  const module = await boot(factory);
  assert.equal(module.persistence.state, 'ready');
  module.FS_createDataFile(saveName, 'new-save', new Uint8Array([7, 8]), true, true);
  module.flushPersistentStorage('startup-test');
  await until(() => module.persistence.hasFlushed, 'save flush');
  const db = held || await open(factory, saveName);
  assert.deepEqual(Array.from((await saved(db, saveName + '/new-save')).contents), [7, 8]);
  if (held) assert.deepEqual(Array.from((await saved(db)).contents), Array.from(original), 'restored progress survives the first flush');
  if (held) assert.equal(db.version, version, 'opening a compatible save must not force a version change');
  const nextVersion = db.version + 1;
  db.close();
  const upgraded = await open(factory, saveName, nextVersion);
  upgraded.close();
  console.log('PASS: real runtime boot, archive, restore/flush and connection release; save version', version ?? 'new');
}

for (const failure of ['blocked', 'silent']) {
  const factory = new IDBFactory();
  const held = await seed(factory, 1);
  let pending, lateClosed = false;
  const idb = {open(name, ...args) {
    if (name !== saveName) return factory.open(name, ...args);
    pending = {};
    if (failure === 'blocked') queueMicrotask(() => pending.onblocked?.());
    return pending;
  }};
  const module = await boot(idb);
  assert.equal(module.persistence.state, 'error');
  module.flushPersistentStorage('must-not-overwrite');
  assert.equal(module.persistence.hasFlushed, undefined);
  assert.deepEqual(Array.from((await saved(held)).contents), Array.from(original));
  // A late request completion must not restore files over an active game or
  // enable a writeback from the empty fallback filesystem.
  pending.result = {close() {lateClosed = true;}};
  pending.onsuccess();
  assert.equal(lateClosed, true);
  assert.equal(module.persistence.state, 'error');
  assert.equal(module.remainingDependencies, 0);
  held.close();
  console.log('PASS: ' + failure + ' storage releases startup once, preserves saved progress and ignores late completion');
}
