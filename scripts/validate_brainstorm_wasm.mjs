// Run with: node scripts/validate_brainstorm_wasm.mjs
// Checks brainstorm/immolate.wasm against Brainstorm Rerolled's own golden
// reference (Immolate/tests/golden_expected.txt in the pinned source): match
// counts and an FNV-1a hash of exactly which seeds pass, for 13 filters over
// 200,000 seeds, and the single-threaded search results. Then the in-game
// filter text: starter filters, a parse error, and seed ID round trips.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {unzipSync, strFromU8} from 'fflate';
const root = new URL('../', import.meta.url);
// engine.js is a plain script (the page inlines it into its workers).
const createImmolate = new Function(readFileSync(new URL('brainstorm/engine.js', root), 'utf8') + '\nreturn createImmolate;')();
const engine = createImmolate(new WebAssembly.Module(readFileSync(new URL('brainstorm/immolate.wasm', root))));
const lock = JSON.parse(readFileSync(new URL('vendor/upstream.json', root), 'utf8')).BrainstormRerolled;
const golden = strFromU8(unzipSync(new Uint8Array(readFileSync(new URL('vendor/' + lock.archive, root))))['Immolate/tests/golden_expected.txt']);
assert.equal(engine.apiVersion, 2);

const configs = {
  'charm': {tag: 'tag_charm'}, 'double': {tag: 'tag_double'},
  'charm+soul': {tag: 'tag_charm', souls: 1}, 'charm+soul+perkeo': {tag: 'tag_charm', souls: 1, perkeo: true},
  'overstock': {voucher: 'v_overstock_norm'}, 'telescope+double': {voucher: 'v_telescope', tag: 'tag_double'},
  'mega_arcana': {pack: 'p_arcana_mega'}, 'buffoon+uncommon': {pack: 'p_buffoon_normal', tag: 'tag_uncommon'},
  'observatory': {observatory: true}, 'copymoney': {copy_money: true}, 'bean': {bean: true},
  'burglar': {burglar: true}, 'retcon': {retcon: true},
};
// [filters]: every seed from AAAAAAAA for 200,000 IDs.
const start = engine.seedId('AAAAAAAA'), N = 200000;
for (const line of golden.split('[filters]')[1].split('[search]')[0].trim().split('\n').slice(1)) {
  const [, label, hits, hash, first] = line.match(/^(\S+)\s+hits=(\d+) hash=([0-9a-f]+) first=(.*)$/);
  engine.configure(configs[label]);
  let count = 0, h = 1469598103934665603n, firsts = '';
  for (let id = start, end = start + N; id < end;) {
    const match = engine.scan(id, end - id);
    if (match < 0) break;
    count++;
    let v = BigInt(match);
    for (let b = 0; b < 8; b++) { h ^= (v >> BigInt(b * 8)) & 0xffn; h = (h * 1099511628211n) & 0xffffffffffffffffn; }
    if (count <= 5) firsts += engine.seedString(match) + ',';
    id = match + 1;
  }
  assert.equal(count, Number(hits), label + ' hits');
  assert.equal(h.toString(16).padStart(16, '0'), hash, label + ' hash');
  assert.equal(firsts, first, label + ' first');
}
// [search]: single-threaded search from 1A2B3C4D, wrapping at ZZZZZZZZ.
for (const line of golden.split('[search]')[1].trim().split('\n')) {
  const [label, seed] = line.trim().split(/\s+/);
  engine.configure(configs[label]);
  const from = engine.seedId('1A2B3C4D');
  let found = engine.scan(from, Math.min(engine.idMax - from + 1, 5e7));
  assert(found >= 0, label + ' search found nothing');
  assert.equal(engine.seedString(found), seed, label + ' search');
}
// In-game filter text (Immolate/src/filterprog.hpp): the starter filters parse,
// match the old built-in options they replace, and mistakes are reported.
engine.configure({filter_spec: 'tag tag_charm ante=1 blind=small\nsoul ante=1 packs=1 size=5'});
assert.equal(engine.check('BNAAAAAA'), 1, 'Charm + Soul starter filter accepts a Charm + Soul seed');
assert.equal(engine.check('3BAAAAAA'), 0, 'Charm without The Soul is rejected');
assert.throws(() => engine.configure({filter_spec: 'tag tag_bogus ante=1'}), /tag_bogus|unknown/i);
assert.throws(() => engine.configure({tag: 'tag_bogus'}), /unknown tag/);
for (const seed of ['1', 'Z', 'AAAAAAAA', 'ZZZZZZZZ', '7NTPKW6P']) assert.equal(engine.seedString(engine.seedId(seed)), seed);
assert.equal(engine.seedId('O0'), -1, '0 is not a seed character');
assert.equal(engine.seedId('ZZZZZZZZ'), engine.idMax);
console.log(engine.info + ': golden filters (13 x 200,000 seeds), searches, filter text and seed IDs match Brainstorm Rerolled\'s reference');
