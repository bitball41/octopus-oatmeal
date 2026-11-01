import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
globalThis.window={};
const {normalizeBuild,assembleBuild}=await import('../browser/custom-runtime.js');
assert.equal(normalizeBuild(['cryptid','multiplayer','randomizer'],{min:1,max:100}).identity,
  normalizeBuild(['randomizer','multiplayer','cryptid','cryptid'],{min:1,max:100}).identity);
assert.notEqual(normalizeBuild(['multiplayer','randomizer'],{min:1,max:100}).identity,
  normalizeBuild(['multiplayer','randomizer'],{min:1,max:10}).identity);
for(const bounds of [{min:10,max:1},{min:-1,max:3},{min:NaN,max:4}])assert.throws(()=>normalizeBuild(['randomizer'],bounds));
assert.equal(normalizeBuild(['randomizer'],{min:0.1,max:0.2}).min,0.1);
assert.equal(normalizeBuild(['randomizer']).min,0.1);
assert.equal(normalizeBuild(['randomizer']).max,10);
assert.match(normalizeBuild(['randomizer']).identity,/designed-v3/);
const build=normalizeBuild(['cryptid','handy','multiplayer','sleeves','randomizer'],{min:3,max:3});
const fetchAsset=async path=>new Blob([await readFile(new URL('../'+path,import.meta.url))]);
const result=await assembleBuild(build,'',fetchAsset,()=>{});
const {unzipSync,strFromU8}=await import('fflate');
const files=unzipSync(result.archive),config=JSON.parse(strFromU8(files['browser/build_config.json']));
assert.equal(config.min,3);assert.equal(config.max,3);assert.equal(config.randomizer,true);assert.equal(config.range_mode,'multiplier');
assert.equal(config.randomizer_policy,'designed-v3');
assert.equal(strFromU8(files['Mods/ValueRandomizer/ValueRandomizer.lua']),await readFile(new URL('../browser/value-randomizer.lua',import.meta.url),'utf8'));
for(const path of ['Mods/Cryptid/Cryptid.lua','Mods/Multiplayer/core.lua','Mods/CardSleeves/CardSleeves.lua','Mods/Handy/index.lua'])assert(files[path],path);
assert(!files['Mods/Bunco/Bunco.lua']);
// Handy brings JokerDisplay and Overflow, as in Vanilla + Handy; the CRT colour pass is kept.
for(const path of ['Mods/JokerDisplay/JokerDisplay.lua','Mods/Overflow/Overflow.lua'])assert(files[path],path);
assert.match(strFromU8(files['game.lua']),/love\.graphics\.setShader\( G\.SHADERS\['CRT'\]\)/);
assert.match(strFromU8(files['card.lua']),/LiminalRandomizer.literal/);
assert.equal(strFromU8(files['browser/mod_settings.lua']),await readFile(new URL('../browser/lua/browser/mod_settings.lua',import.meta.url),'utf8'));
assert.equal(strFromU8(files['main.lua']).match(/require "browser\.mod_settings"/g).length,1);
assert(strFromU8(files['main.lua']).trimEnd().endsWith('require "browser.mod_settings"'));
assert.equal(config.vanilla_save,false);
// Vanilla save: allowed without Cryptid, never with it; the custom save stays separate otherwise.
const ownSave=normalizeBuild(['paperback','bunco']);
assert.equal(ownSave.persist,'/home/web_user/love-custom-'+ownSave.identity);assert.equal(ownSave.vanillaSave,false);
const vanillaSave=normalizeBuild(['bunco','paperback'],{},{vanillaSave:true});
assert.equal(vanillaSave.persist,'/home/web_user/love-vanilla');assert.equal(vanillaSave.cache,'/home/web_user/love-custom-'+vanillaSave.identity);
assert.equal(vanillaSave.identity,ownSave.identity);
assert.equal(normalizeBuild(['handy','sleeves'],{},{vanillaSave:true}).persist,'/home/web_user/love-vanilla');
const cryptidBuild=normalizeBuild(['cryptid','paperback'],{},{vanillaSave:true});
assert.equal(cryptidBuild.vanillaSave,false);assert.notEqual(cryptidBuild.persist,'/home/web_user/love-vanilla');
const vanillaResult=await assembleBuild(vanillaSave,'',fetchAsset,()=>{});
const noHandy=unzipSync(vanillaResult.archive);
assert(!noHandy['Mods/JokerDisplay/JokerDisplay.lua']&&!noHandy['Mods/Overflow/Overflow.lua'],'JokerDisplay/Overflow only come with Handy');
assert.equal(JSON.parse(strFromU8(unzipSync(vanillaResult.archive)['browser/build_config.json'])).vanilla_save,true);
console.log('Browser assembly: exact selected mods, normalized saves, range validation, verified packs and injected configuration, mod settings and Vanilla save routing passed');
