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
  let engine = null, wasmModule = null, workerURL = null, engineSource = '', loadError = 'still loading';
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
    if (job.pump) { clearTimeout(job.pump); job.pump = null; }
  }

  function fail(job, message) {
    job.status = 'error';
    job.error = message;
    console.error('[Brainstorm-Rerolled] search stopped: ' + message);
    stopWorkers(job);
  }

  function finish(job, foundId, count) {
    job.checked += count;
    if (foundId >= 0 && job.status === 'running') {
      job.status = 'found';
      job.seed = engine.seedString(foundId);
      stopWorkers(job);
    }
  }

  // The next block of seed IDs: start, start+1, ... wrapping from "ZZZZZZZZ"
  // back to "1", so every seed is visited once. Blocks a failed worker was
  // scanning come back first.
  function nextUnit(job, size) {
    if (job.retry.length) return job.retry.pop();
    if (job.offset >= job.total) return null;
    const first = (job.start - 1 + job.offset) % job.total + 1;
    const count = Math.min(size, job.total - job.offset, job.total - first + 1);
    job.offset += count;
    return {first, count};
  }

  function dispatch(job, worker) {
    if (job.status !== 'running') return;
    worker.unit = nextUnit(job, BLOCK);
    if (worker.unit) return worker.postMessage({type: 'scan', first: worker.unit.first, count: worker.unit.count});
    if (job.workers.every(w => !w.unit)) { job.status = 'exhausted'; stopWorkers(job); }
  }

  // A worker failed: put its block back and start a replacement. After
  // repeated failures, search on the page instead.
  function workerFailed(job, worker, message) {
    if (job.status !== 'running') return;
    console.warn('[Brainstorm-Rerolled] search worker failed: ' + message);
    worker.terminate();
    job.workers = job.workers.filter(w => w !== worker);
    if (worker.unit) job.retry.push(worker.unit);
    job.failures++;
    if (job.failures <= 2 * job.size) return addWorker(job);
    if (!job.workers.length) searchOnPage(job, 'search workers keep failing (' + message + ')');
  }

  function addWorker(job) {
    let worker;
    try { worker = new Worker(workerURL); } catch (error) {
      if (!job.workers.length) searchOnPage(job, 'search workers unavailable (' + (error && error.message || error) + ')');
      return;
    }
    job.workers.push(worker);
    worker.onmessage = event => {
      const m = event.data;
      if (job.status !== 'running') return;
      if (m.type === 'ready') return dispatch(job, worker);
      if (m.type === 'error') return workerFailed(job, worker, m.message);
      worker.unit = null;
      finish(job, m.found, m.count);
      dispatch(job, worker);
    };
    worker.onerror = event => {
      event.preventDefault();
      workerFailed(job, worker, (event.message || 'error') + (event.lineno ? ' (line ' + event.lineno + ')' : ''));
    };
    worker.onmessageerror = () => workerFailed(job, worker, 'message could not be read');
    try {
      worker.postMessage({type: 'init', module: wasmModule, options: job.options});
    } catch (error) {
      workerFailed(job, worker, String(error && error.message || error));
    }
  }

  // Fallback when Web Workers cannot run: scan on the page in short slices
  // between frames. Slower, but the game keeps drawing.
  function searchOnPage(job, reason) {
    console.warn('[Brainstorm-Rerolled] ' + reason + '; searching on the page instead');
    stopWorkers(job);
    let local;
    try { local = new Function(engineSource + '\nreturn createImmolate;')()(wasmModule); local.configure(job.options); }
    catch (error) { return fail(job, reason + '; page search failed: ' + (error && error.message || error)); }
    job.onPage = true;
    const step = () => {
      job.pump = null;
      if (job.status !== 'running') return;
      const until = performance.now() + 8;
      try {
        while (job.status === 'running' && performance.now() < until) {
          const unit = nextUnit(job, 1 << 14);
          if (!unit) { job.status = 'exhausted'; return; }
          finish(job, local.scan(unit.first, unit.count), unit.count);
        }
      } catch (error) { return fail(job, 'page search failed: ' + (error && error.message || error)); }
      if (job.status === 'running') job.pump = setTimeout(step, 0);
    };
    job.pump = setTimeout(step, 0);
  }

  function start(o) {
    engine.configure(o); // throws a readable error for a bad filter
    // Like the native library: begin at the mod's random start seed, so
    // repeated searches give different seeds.
    let startId = o.start_seed ? engine.seedId(o.start_seed) : 1;
    if (startId < 1) throw new Error("invalid start seed '" + o.start_seed + "'");
    const job = {id: nextJob++, status: 'running', seed: null, error: null, checked: 0, options: o,
      startSeed: engine.seedString(startId), start: startId, offset: 0, total: engine.idMax,
      workers: [], retry: [], failures: 0, size: workerCount(), pump: null, onPage: false};
    jobs.set(job.id, job);
    if (typeof Worker !== 'function') searchOnPage(job, 'Web Workers are not available');
    else for (let i = 0; i < job.size && job.status === 'running' && !job.onPage; i++) addWorker(job);
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
        if (!job) return {status: 'error', error: 'search ' + request.job + ' is not running on this page'};
        return {status: job.status, seed: job.seed, checked: job.checked, start_seed: job.startSeed,
          error: job.error, on_page: job.onPage};
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
        engineSource = source;
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
