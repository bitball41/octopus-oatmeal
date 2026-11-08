// Brainstorm Rerolled's Immolate seed searcher (brainstorm/immolate.wasm,
// built by scripts/build_brainstorm_wasm.py) wrapped for JavaScript. Shared by
// the page and its search workers (brainstorm/host.js) and by the tests.
// Plain script, no imports: the host inlines it into each worker.
function createImmolate(wasmModule) {
  let memory;
  const encoder = new TextEncoder(), decoder = new TextDecoder();
  const view = () => new DataView(memory.buffer);
  // The few WASI calls libc makes at startup; Immolate never prints or exits.
  const wasi = {
    environ_get: () => 0,
    environ_sizes_get: (count, size) => { view().setUint32(count, 0, true); view().setUint32(size, 0, true); return 0; },
    fd_close: () => 0,
    fd_seek: () => 0,
    fd_write: (fd, iovs, n, written) => {
      let total = 0;
      for (let i = 0; i < n; i++) total += view().getUint32(iovs + i * 8 + 4, true);
      view().setUint32(written, total, true);
      return 0;
    },
    proc_exit: code => { throw new Error('Immolate exited with code ' + code); },
  };
  const exports = new WebAssembly.Instance(wasmModule, {wasi_snapshot_preview1: wasi}).exports;
  memory = exports.memory;
  exports._initialize();
  const read = pointer => {
    const bytes = new Uint8Array(memory.buffer);
    let end = pointer;
    while (bytes[end]) end++;
    return decoder.decode(bytes.subarray(pointer, end));
  };
  // Copies strings into wasm memory for one call.
  const withStrings = (values, call) => {
    const pointers = values.map(value => {
      const bytes = encoder.encode(String(value ?? '') + '\0');
      const pointer = exports.bsw_alloc(bytes.length);
      new Uint8Array(memory.buffer).set(bytes, pointer);
      return pointer;
    });
    try { return call(...pointers); } finally { pointers.forEach(p => exports.bsw_free(p)); }
  };
  return {
    apiVersion: exports.bsw_api_version(),
    info: read(exports.bsw_build_info()),
    idMax: exports.bsw_id_max(),
    // Same fields as Brainstorm Rerolled's native.start options.
    configure(options) {
      const o = options || {};
      const ok = withStrings([o.tag, o.voucher, o.pack, o.filter_spec], (tag, voucher, pack, spec) =>
        exports.bsw_configure(tag, voucher, pack, o.souls | 0, +!!o.observatory, +!!o.perkeo,
          +!!o.copy_money, +!!o.retcon, +!!o.bean, +!!o.burglar, spec));
      if (!ok) throw new Error(read(exports.bsw_last_error()));
    },
    seedId: seed => withStrings([seed], pointer => exports.bsw_seed_id(pointer)),
    seedString: id => read(exports.bsw_seed_string(id)),
    check: seed => withStrings([seed], pointer => exports.bsw_check_seed(pointer)),
    // First matching seed ID in [first, first + count), or -1.
    scan: (first, count) => exports.bsw_scan(first, count),
  };
}
