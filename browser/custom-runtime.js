import {unzipSync, zipSync, strToU8, strFromU8} from 'fflate';

const MODS = {handy:'Handy',paperback:'Paperback',bunco:'Bunco',cryptid:'Cryptid',multiplayer:'Multiplayer',sleeves:'CardSleeves'};
// Cryptid keeps its own M1/M2/M3 profiles, so it can never read a Vanilla save.
export function canUseVanillaSave(selected) {
  return !selected.includes('cryptid');
}
export function normalizeBuild(selected, bounds={}, options={}) {
  const mods=[...new Set(selected)].filter(id=>id in MODS || id==='randomizer').sort();
  if(!mods.length) throw new Error('Select at least one mod.');
  const randomizer=mods.includes('randomizer');
  const min=Number(bounds.min ?? 0.1),max=Number(bounds.max ?? 10);
  if(randomizer && (!Number.isFinite(min)||!Number.isFinite(max)||min<0||max<min||max>1000000))
    throw new Error('Use a minimum multiplier of 0 or more and a maximum multiplier up to 1,000,000. The maximum must be at least the minimum.');
  const key=mods.filter(id=>id in MODS).map(id=>MODS[id]).sort().join('+')||'base';
  const identity=mods.join('-')+(randomizer?'-designed-v3-'+min+'-'+max:'');
  const vanillaSave=!!options.vanillaSave && canUseVanillaSave(mods);
  return {mods,key,identity,randomizer,min,max,multiplayer:mods.includes('multiplayer'),vanillaSave,
    persist:vanillaSave?'/home/web_user/love-vanilla':'/home/web_user/love-custom-'+identity,
    cache:'/home/web_user/love-custom-'+identity};
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
  files['browser/mod_settings.lua']=new Uint8Array(await (await fetchAsset(base+'browser/lua/browser/mod_settings.lua')).arrayBuffer());
  const loader=strToU8('\nrequire "browser.mod_settings"\n');
  if(!strFromU8(files['main.lua'],true).includes('require "browser.mod_settings"')) {
    const main=new Uint8Array(files['main.lua'].length+loader.length);
    main.set(files['main.lua']);main.set(loader,files['main.lua'].length);files['main.lua']=main;
  }
  if(build.randomizer) files['Mods/ValueRandomizer/ValueRandomizer.lua']=new Uint8Array(await (await fetchAsset(base+'custom/value-randomizer.lua')).arrayBuffer());
  const config={randomizer:build.randomizer,min:build.min,max:build.max,range_mode:'multiplier',randomizer_policy:'designed-v3',mods:build.mods,identity:build.identity,vanilla_save:build.vanillaSave};
  files['browser/build_config.json']=strToU8(JSON.stringify(config));
  status('Assembling your build…');
  const archive=zipSync(files,{level:0});
  return {archive,config,recipe};
}
window.OctopusCustom={normalizeBuild,assembleBuild,canUseVanillaSave};
