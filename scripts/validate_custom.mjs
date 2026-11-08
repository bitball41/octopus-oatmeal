import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
globalThis.window={};
const {normalizeBuild,assembleBuild,assembleBrainstormPreset,BRAINSTORM_FILES,BRAINSTORM_PRESET_DIR,CONTENT_MODS}=await import('../browser/custom-runtime.js');
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
// Brainstorm Rerolled is injected at launch; it keeps the build's save and multiplayer identity.
const withBrainstorm=normalizeBuild(['handy','sleeves','brainstorm']),plain=normalizeBuild(['handy','sleeves']);
assert.equal(withBrainstorm.brainstorm,true);assert.equal(plain.brainstorm,false);
assert.equal(withBrainstorm.key,plain.key);assert.equal(withBrainstorm.identity,plain.identity);assert.equal(withBrainstorm.persist,plain.persist);
assert.notEqual(withBrainstorm.archiveKey,plain.archiveKey);
// Its searcher predicts the base game, so not with mods that add cards.
for(const mod of CONTENT_MODS)assert.throws(()=>normalizeBuild(['handy',mod,'brainstorm']),/base game/);
const brainstormLoader=await readFile(new URL('../browser/brainstorm.lua',import.meta.url),'utf8');
const brainstormSources=Object.fromEntries(await Promise.all(BRAINSTORM_FILES.map(async name=>['brainstorm_rerolled/'+name+'.lua',await readFile(new URL('../brainstorm/lua/'+name+'.lua',import.meta.url),'utf8')])));
const brainstormFiles=unzipSync((await assembleBuild(withBrainstorm,'',fetchAsset,()=>{})).archive);
assert.equal(strFromU8(brainstormFiles['browser/brainstorm.lua']),brainstormLoader);
for(const [path,source] of Object.entries(brainstormSources))assert.equal(strFromU8(brainstormFiles[path]),source,path);
const brainstormMain=strFromU8(brainstormFiles['main.lua']);
assert.equal(brainstormMain.match(/require "browser\.brainstorm"/g).length,1);
assert(brainstormMain.indexOf('require "browser.mod_settings"')<brainstormMain.indexOf('require "browser.brainstorm"'));
assert.equal(JSON.parse(strFromU8(brainstormFiles['browser/build_config.json'])).brainstorm,true);
assert(!files['browser/brainstorm.lua']&&!files['brainstorm_rerolled/core.lua']&&!/browser\.brainstorm/.test(strFromU8(files['main.lua'])),'Brainstorm only when selected');
// Vanilla + Brainstorm Rerolled + Handy keeps every Vanilla + Handy file byte for byte and only adds Brainstorm.
assert.equal(BRAINSTORM_PRESET_DIR,'vanilla-handy/');
const vanillaFiles=unzipSync(new Uint8Array(await readFile(new URL('../vanilla-handy/game.data',import.meta.url))));
assert(vanillaFiles['Mods/Handy/index.lua']||Object.keys(vanillaFiles).some(n=>n.startsWith('Mods/Handy/')),'preset includes Handy');
const preset=unzipSync((await assembleBrainstormPreset('',fetchAsset,()=>{})).archive);
const added=['browser/brainstorm.lua',...Object.keys(brainstormSources)];
assert.deepEqual(Object.keys(preset).sort(),[...new Set([...Object.keys(vanillaFiles),...added])].sort());
for(const [path,source] of Object.entries(brainstormSources))assert.equal(strFromU8(preset[path]),source,path);
for(const [name,data] of Object.entries(vanillaFiles))if(name!=='main.lua'&&!added.includes(name))assert(Buffer.from(preset[name]).equals(Buffer.from(data)),name);
assert.equal(strFromU8(preset['main.lua']),strFromU8(vanillaFiles['main.lua'])+'\nrequire "browser.brainstorm"\n');
console.log('Brainstorm Rerolled: injected only when selected, after mod settings, keeping save identity, never with content mods; Vanilla + Brainstorm Rerolled + Handy is Vanilla + Handy plus the mod');
console.log('Browser assembly: exact selected mods, normalized saves, range validation, verified packs and injected configuration, mod settings and Vanilla save routing passed');
