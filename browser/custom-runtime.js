import {unzipSync, zipSync, strToU8, strFromU8} from 'fflate';

const MODS = {handy:'Handy',paperback:'Paperback',bunco:'Bunco',cryptid:'Cryptid',multiplayer:'Multiplayer',sleeves:'CardSleeves'};
// Add-ons are injected into any build at launch instead of compiled per combination.
const ADDONS = ['randomizer','brainstorm'];
// Mods that add cards to the game's pools, which Brainstorm Rerolled's
// searcher (Immolate) does not model.
export const CONTENT_MODS = ['cryptid','paperback','bunco'];
// Cryptid keeps its own M1/M2/M3 profiles, so it can never read a Vanilla save.
export function canUseVanillaSave(selected) {
  return !selected.includes('cryptid');
}
export function normalizeBuild(selected, bounds={}, options={}) {
  const mods=[...new Set(selected)].filter(id=>id in MODS || ADDONS.includes(id)).sort();
  if(!mods.length) throw new Error('Select at least one mod.');
  const randomizer=mods.includes('randomizer');
  if(mods.includes('brainstorm')&&mods.some(id=>CONTENT_MODS.includes(id)))
    throw new Error('Brainstorm Rerolled predicts the base game\u2019s cards, so it can\u2019t be combined with Cryptid, Paperback or Bunco.');
  const min=Number(bounds.min ?? 0.1),max=Number(bounds.max ?? 10);
  if(randomizer && (!Number.isFinite(min)||!Number.isFinite(max)||min<0||max<min||max>1000000))
    throw new Error('Use a minimum multiplier of 0 or more and a maximum multiplier up to 1,000,000. The maximum must be at least the minimum.');
  const key=mods.filter(id=>id in MODS).map(id=>MODS[id]).sort().join('+')||'base';
  // Brainstorm only adds keys, a settings tab and its own settings file, so it
  // keeps the build's save and multiplayer identity; only the archive differs.
  const brainstorm=mods.includes('brainstorm');
  const identity=mods.filter(id=>id!=='brainstorm').join('-')+(randomizer?'-designed-v3-'+min+'-'+max:'');
  const vanillaSave=!!options.vanillaSave && canUseVanillaSave(mods);
  return {mods,key,identity,archiveKey:identity+(brainstorm?'+brainstorm-rerolled':''),randomizer,brainstorm,min,max,multiplayer:mods.includes('multiplayer'),vanillaSave,
    persist:vanillaSave?'/home/web_user/love-vanilla':'/home/web_user/love-custom-'+identity,
    cache:'/home/web_user/love-custom-'+identity};
}
// Packs a Lua module into the archive and requires it at the end of main.lua.
async function injectModule(files,module,source,base,fetchAsset) {
  const path=module.replace(/\./g,'/')+'.lua';
  files[path]=new Uint8Array(await (await fetchAsset(base+source)).arrayBuffer());
  const line='require "'+module+'"';
  if(strFromU8(files['main.lua'],true).includes(line)) return;
  const loader=strToU8('\n'+line+'\n');
  const main=new Uint8Array(files['main.lua'].length+loader.length);
  main.set(files['main.lua']);main.set(loader,files['main.lua'].length);files['main.lua']=main;
}
// Brainstorm Rerolled's Lua: the loader (browser/brainstorm.lua, required at
// the end of main.lua) and the mod's files, read from brainstorm_rerolled/.
// Its search engine runs in the page (brainstorm/host.js).
export const BRAINSTORM_FILES=['core','ui','filter_builder','native'];
async function injectBrainstorm(files,base,fetchAsset) {
  for(const name of BRAINSTORM_FILES)
    files['brainstorm_rerolled/'+name+'.lua']=new Uint8Array(await (await fetchAsset(base+'brainstorm/lua/'+name+'.lua')).arrayBuffer());
  await injectModule(files,'browser.brainstorm','browser/brainstorm.lua',base,fetchAsset);
}
// Vanilla + Brainstorm Rerolled + Handy: the released Vanilla + Handy archive
// (Vanilla's game code with standalone Handy, JokerDisplay and Overflow) with
// Brainstorm Rerolled added. It shares the Vanilla save, as Vanilla + Handy does.
export const BRAINSTORM_PRESET_DIR='vanilla-handy/';
export async function assembleBrainstormPreset(base, fetchAsset, status) {
  status('Downloading Vanilla + Handy…');
  const files=unzipSync(new Uint8Array(await (await fetchAsset(base+BRAINSTORM_PRESET_DIR+'game.data')).arrayBuffer()));
  if(!files['main.lua']) throw new Error('The Vanilla + Handy download is incomplete. Please reload.');
  status('Adding Brainstorm…');
  await injectBrainstorm(files,base,fetchAsset);
  const archive=zipSync(files,{level:0});
  return {archive,config:{brainstorm:true,mods:['handy','brainstorm'],identity:'vanilla',vanilla_save:true}};
}
async function sha256(bytes) {
  const digest=await crypto.subtle.digest('SHA-256',bytes);
  return [...new Uint8Array(digest)].map(n=>n.toString(16).padStart(2,'0')).join('');
}
export async function assembleBuild(build, base, fetchAsset, status) {
  const manifest=JSON.parse(await (await fetchAsset(base+'custom/manifest.json')).text());
  const recipe=manifest.builds[build.key];
  if(!recipe) throw new Error('This combination is missing from this runtime release.');
  const files={};
  async function unpack(pack) {
    const chunks=await Promise.all(pack.parts.map(async path=>new Uint8Array(await (await fetchAsset(base+'custom/'+path)).arrayBuffer())));
    const blob=new Uint8Array(chunks.reduce((n,c)=>n+c.length,0));let offset=0;
    for(const chunk of chunks){blob.set(chunk,offset);offset+=chunk.length;}
    if(await sha256(blob)!==pack.sha256) throw new Error('Mod download failed its integrity check. Please reload.');
    Object.assign(files,unzipSync(blob));
  }
  let done=0;
  // Sequential inflation reduces peak memory on Chromebooks.
  for(const pack of [...recipe.packs,recipe.overlay]) {
    status('Preparing mods… '+(++done)+'/'+(recipe.packs.length+1));await unpack(pack);
  }
  // Mod settings fixes (pixel smoothing default, high contrast) also reach
  // combinations whose packs predate them.
  await injectModule(files,'browser.mod_settings','browser/lua/browser/mod_settings.lua',base,fetchAsset);
  // Brainstorm lives outside browser/lua so prebuilt archives never carry it.
  if(build.brainstorm) await injectBrainstorm(files,base,fetchAsset);
  if(build.randomizer) files['Mods/ValueRandomizer/ValueRandomizer.lua']=new Uint8Array(await (await fetchAsset(base+'custom/value-randomizer.lua')).arrayBuffer());
  const config={brainstorm:build.brainstorm,randomizer:build.randomizer,min:build.min,max:build.max,range_mode:'multiplier',randomizer_policy:'designed-v3',mods:build.mods,identity:build.identity,vanilla_save:build.vanillaSave};
  files['browser/build_config.json']=strToU8(JSON.stringify(config));
  status('Assembling your build…');
  const archive=zipSync(files,{level:0});
  return {archive,config,recipe};
}
window.OctopusCustom={normalizeBuild,assembleBuild,assembleBrainstormPreset,canUseVanillaSave};
