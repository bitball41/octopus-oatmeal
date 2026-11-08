// wasm_api.cpp — Immolate's search engine for the browser.
//
// Brainstorm Rerolled loads Immolate as a native library through LuaJIT's
// FFI and searches on native threads. The browser game runs plain Lua 5.1 in
// WebAssembly with neither, so this file builds the unmodified Immolate
// sources as a single-threaded WebAssembly module instead. Each browser Web
// Worker instantiates it, configures the active filter once and scans the
// blocks of seed IDs the page hands it (browser/brainstorm-host.js).
//
// brainstorm_api.cpp is included whole so this file reuses its parameter
// parsing (buildConfig, the key table) exactly; its thread pool is never
// started here (see shim/thread).
#include "brainstorm_api.cpp"

#include <cstdlib>

#define BSW_EXPORT(name) extern "C" __attribute__((export_name(#name)))

namespace {
FilterConfig g_cfg;
std::unique_ptr<Prefilter> g_prefilter;
bool g_configured = false;
std::string g_seed;
} // namespace

BSW_EXPORT(bsw_alloc) char *bsw_alloc(int bytes) { return (char *)std::malloc(bytes); }
BSW_EXPORT(bsw_free) void bsw_free(char *p) { std::free(p); }
BSW_EXPORT(bsw_api_version) int bsw_api_version() { return BS_API_VERSION; }
BSW_EXPORT(bsw_build_info) const char *bsw_build_info() {
  static std::string info = std::string("Immolate ") + IMMOLATE_VERSION + " (WebAssembly)";
  return info.c_str();
}
BSW_EXPORT(bsw_last_error) const char *bsw_last_error() { return bs_last_error(); }

// Sets the filter every later call uses. Same fields as bs_params.
// Returns 1, or 0 with bsw_last_error() saying why.
BSW_EXPORT(bsw_configure)
int bsw_configure(const char *tag, const char *voucher, const char *pack,
                  int souls, int observatory, int perkeo, int copy_money,
                  int retcon, int bean, int burglar, const char *filter_spec) {
  bs_params p{};
  p.api_version = BS_API_VERSION;
  p.tag = tag;
  p.voucher = voucher;
  p.pack = pack;
  p.souls = souls;
  p.observatory = observatory;
  p.perkeo = perkeo;
  p.copy_money = copy_money;
  p.retcon = retcon;
  p.bean = bean;
  p.burglar = burglar;
  p.custom_filter = "No Filter";
  p.filter_spec = filter_spec;
  FilterConfig cfg;
  g_configured = false;
  if (!buildConfig(&p, cfg)) return 0;
  g_cfg = cfg;
  g_prefilter.reset(new Prefilter(g_cfg));
  g_configured = true;
  return 1;
}

// ID of a seed string (1..bsw_id_max()), or -1 if it is not a valid seed.
BSW_EXPORT(bsw_seed_id) double bsw_seed_id(const char *seed) {
  if (!seed || !validSeedString(seed)) return -1;
  return (double)Seed(std::string(seed)).getID();
}
BSW_EXPORT(bsw_id_max) double bsw_id_max() { return (double)SEED_ID_MAX; }

// The seed string of an ID.
BSW_EXPORT(bsw_seed_string) const char *bsw_seed_string(double id) {
  g_seed = Seed((long long)id).tostring();
  return g_seed.c_str();
}

// 1 if `seed` passes the configured filter, 0 if not, -1 on a bad seed.
BSW_EXPORT(bsw_check_seed) int bsw_check_seed(const char *seed) {
  if (!g_configured || !seed || !validSeedString(seed)) return -1;
  Seed s{std::string(seed)};
  Instance inst(s);
  return brainstormFilter(inst, g_cfg) >= 1 ? 1 : 0;
}

// Tests `count` consecutive seed IDs from `firstId` (not wrapping past
// "ZZZZZZZZ") exactly as a native worker thread does. Returns the first
// matching ID, or -1.
BSW_EXPORT(bsw_scan) double bsw_scan(double firstId, double count) {
  if (!g_configured) return -1;
  std::atomic<bool> stop{false};
  std::atomic<uint64_t> checked{0};
  return (double)scanRange(g_cfg, g_prefilter.get(), (long long)firstId,
                           (long long)count, stop, checked);
}

// C++ runtime hooks Ubuntu's wasm32-wasi libc++ references but does not ship.
// The module is built without exceptions: an allocation failure (the only
// throw in reach) traps instead. thread_local destructors would only run at
// thread exit, which a reactor module never reaches.
extern "C" {
void *__cxa_allocate_exception(unsigned long) { __builtin_trap(); }
void __cxa_throw(void *, void *, void (*)(void *)) { __builtin_trap(); }
int __cxa_thread_atexit(void (*)(void *), void *, void *) { return 0; }
}
