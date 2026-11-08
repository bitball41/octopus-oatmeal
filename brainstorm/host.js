// Brainstorm Rerolled's seed search for the browser.
//
// The mod's Lua (brainstorm/lua/native.lua) calls window.OctopusBrainstorm.call
// through print("callJavascriptFunction ..."), which the page evaluates
// synchronously; the answer is written to <save folder>/brainstorm_reply.lua as
// a Lua table before the print returns. Searches run in Web Workers, each with
// its own copy of Immolate (brainstorm/immolate.wasm via brainstorm/engine.js),
// scanning blocks of seed IDs handed out here, as the native library's worker
// threads do. The game itself keeps the page's main thread.
(function () {
  'use strict';
  const BLOCK = 1 << 18; // seeds per work unit, ~0.15 s on one worker
  let engine = null, wasmModule = null, workerURL = null, loadError = 'still loading';
  const jobs = new Map();
  let nextJob = 1;

  const WORKER = `
let engine;
onmessage = event => {
  const m = event.data;
  try {
    if (m.type === 'init') {
      engine = createImmolate(m.module);
      engine.configure(m.options);
      postMessage({type: 'ready'});
    } else if (m.type === 'scan') {
      postMessage({type: 'done', first: m.first, count: m.count, found: engine.scan(m.first, m.count)});
    }
  } catch (error) {
    postMessage({type: 'error', message: String(error && error.message || error)});
  }
};`;

  function workerCount() {
    const cores = Number(navigator.hardwareConcurrency) || 2;
    return Math.max(1, Math.min(cores - 1, 8)); // leave a core for the game
  }

  // A Lua table literal for `value` (plain ASCII strings, numbers, booleans).
  function lua(value) {
    if (value === null || value === undefined) return 'nil';
    if (typeof value === 'boolean') return String(value);
    if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '0';
    if (typeof value === 'string')
      return '"' + value.replace(/[^\x20-\x7e]/g, '?').replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"';
    return '{' + Object.entries(value).filter(([, v]) => v !== null && v !== undefined)
      .map(([k, v]) => '[' + lua(k) + ']=' + lua(v)).join(',') + '}';
  }

  function reply(directory, value) {
    const Module = window.Module;
    const name = 'brainstorm_reply.lua';
    try { Module.FS_unlink(directory + '/' + name); } catch (_) {}
    Module.FS_createDataFile(directory, name, new TextEncoder().encode('return ' + lua(value)), true, true, true);
  }

  function options(o) {
    o = o || {};
    return {tag: o.tag || '', voucher: o.voucher || '', pack: o.pack || '', souls: o.souls | 0,
      observatory: !!o.observatory, perkeo: !!o.perkeo, copy_money: !!o.copy_money, retcon: !!o.retcon,
      bean: !!o.bean, burglar: !!o.burglar, filter_spec: o.filter_spec || '',
      start_seed: typeof o.start_seed === 'string' ? o.start_seed : ''};
  }

  function stopWorkers(job) {
    for (const worker of job.workers) worker.terminate();
    job.workers = [];
  }

  // Hands `worker` the next block of seed IDs: start, start+1, ... wrapping
  // from "ZZZZZZZZ" back to "1", so every seed is visited once.
  function dispatch(job, worker) {
    if (job.status !== 'running') return;
    if (job.offset >= job.total) {
      job.idle++;
      if (job.idle === job.workers.length) { job.status = 'exhausted'; stopWorkers(job); }
      return;
    }
    const first = (job.start - 1 + job.offset) % job.total + 1;
    const count = Math.min(BLOCK, job.total - job.offset, job.total - first + 1);
    job.offset += count;
    worker.postMessage({type: 'scan', first, count});
  }

  function start(o) {
    engine.configure(o); // throws a readable error for a bad filter
    // Like the native library: begin at the mod's random start seed, so
    // repeated searches give different seeds.
    let startId = o.start_seed ? engine.seedId(o.start_seed) : 1;
    if (startId < 1) throw new Error("invalid start seed '" + o.start_seed + "'");
    const job = {id: nextJob++, status: 'running', seed: null, error: null, checked: 0,
      startSeed: engine.seedString(startId), start: startId, offset: 0, total: engine.idMax, idle: 0, workers: []};
    jobs.set(job.id, job);
    for (let i = 0; i < workerCount(); i++) {
      const worker = new Worker(workerURL);
      job.workers.push(worker);
      worker.onmessage = event => {
        const m = event.data;
        if (job.status !== 'running') return;
        if (m.type === 'ready') return dispatch(job, worker);
        if (m.type === 'error') { job.status = 'error'; job.error = m.message; stopWorkers(job); return; }
        job.checked += m.count;
        if (m.found >= 0) {
          job.status = 'found';
          job.seed = engine.seedString(m.found);
          stopWorkers(job);
          return;
        }
        dispatch(job, worker);
      };
      worker.onerror = event => {
        if (job.status !== 'running') return;
        job.status = 'error'; job.error = event.message || 'search worker failed'; stopWorkers(job);
      };
      worker.postMessage({type: 'init', module: wasmModule, options: o});
    }
    return job;
  }

  function handle(request) {
    if (!engine) return {error: 'Seed search engine unavailable: ' + loadError};
    const job = jobs.get(request.job);
    switch (request.op) {
      case 'info':
        return {api_version: engine.apiVersion, info: engine.info + ', ' + workerCount() + ' workers'};
      case 'check':
        engine.configure(options(request.options));
        return {match: engine.check(String(request.seed || '1')) === 1};
      case 'start':
        return {job: start(options(request.options)).id};
      case 'poll':
        if (!job) return {status: 'error'};
        return {status: job.status, seed: job.seed, checked: job.checked, start_seed: job.startSeed};
      case 'cancel':
        if (job && job.status === 'running') { job.status = 'cancelled'; stopWorkers(job); }
        return {};
      case 'free':
        if (job) { if (job.status === 'running') job.status = 'cancelled'; stopWorkers(job); jobs.delete(job.id); }
        return {};
    }
    return {error: 'unknown request ' + request.op};
  }

  window.OctopusBrainstorm = {
    // Loads the engine. `fetchAsset(url)` resolves to a Blob or Response.
    async init(base, fetchAsset) {
      try {
        const [source, bytes] = await Promise.all([
          fetchAsset(base + 'brainstorm/engine.js').then(r => r.text()),
          fetchAsset(base + 'brainstorm/immolate.wasm').then(r => r.arrayBuffer()),
        ]);
        wasmModule = await WebAssembly.compile(bytes);
        engine = new Function(source + '\nreturn createImmolate;')()(wasmModule);
        workerURL = URL.createObjectURL(new Blob([source, WORKER], {type: 'text/javascript'}));
        loadError = null;
      } catch (error) {
        engine = null;
        loadError = String(error && error.message || error);
        console.warn('[Brainstorm-Rerolled] search engine unavailable', error);
      }
    },
    // Called by the game; answers by writing the reply file.
    call(directory, request) {
      let result;
      try { result = handle(request || {}); } catch (error) { result = {error: String(error && error.message || error)}; }
      reply(directory, result);
    },
    // For tests and the console.
    get engine() { return engine; },
    jobs,
  };
})();
