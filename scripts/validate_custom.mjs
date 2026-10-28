import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
globalThis.window={};
const {normalizeBuild,assembleBuild}=await import('../browser/custom-runtime.js');
assert.equal(normalizeBuild(['cryptid','multiplayer','randomizer'],{min:1,max:100}).identity,
  normalizeBuild(['randomizer','multiplayer','cryptid','cryptid'],{min:1,max:100}).identity);
assert.notEqual(normalizeBuild(['multiplayer','randomizer'],{min:1,max:100}).identity,
  normalizeBuild(['multiplayer','randomizer'],{min:1,max:10}).identity);
for(const bounds of [{min:10,max:1},{min:-1,max:3},{min:NaN,max:4},{min:0.1,max:0.2}])assert.throws(()=>normalizeBuild(['randomizer'],bounds));
const build=normalizeBuild(['cryptid','handy','multiplayer','sleeves','randomizer'],{min:3,max:3});
const fetchAsset=async path=>new Blob([await readFile(new URL('../'+path,import.meta.url))]);
const result=await assembleBuild(build,'',fetchAsset,()=>{});
const {unzipSync,strFromU8}=await import('fflate');
const files=unzipSync(result.archive),config=JSON.parse(strFromU8(files['browser/build_config.json']));
assert.equal(config.min,3);assert.equal(config.max,3);assert.equal(config.randomizer,true);
for(const path of ['Mods/Cryptid/Cryptid.lua','Mods/Multiplayer/core.lua','Mods/CardSleeves/CardSleeves.lua','Mods/Handy/index.lua'])assert(files[path],path);
assert(!files['Mods/Bunco/Bunco.lua']);
assert.match(strFromU8(files['card.lua']),/LiminalRandomizer.literal/);
console.log('Browser assembly: exact selected mods, normalized saves, range validation, verified packs and injected configuration passed');
