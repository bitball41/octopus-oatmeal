// Run with: node scripts/validate_saved_builds.mjs
// Launcher saved builds, the Vanilla save option and its warning, on both launchers at desktop and phone width.
import {chromium} from 'playwright';
import {readFileSync} from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import assert from 'node:assert/strict';
const root=path.resolve(new URL('../',import.meta.url).pathname);
const server=http.createServer((req,res)=>{try{let rel=decodeURIComponent(new URL(req.url,'http://x').pathname).replace(/^\//,'')||'index.html';const f=path.resolve(root,rel);res.setHeader('Content-Type',f.endsWith('.js')?'text/javascript':f.endsWith('.html')?'text/html':'application/octet-stream');res.end(readFileSync(f));}catch{res.statusCode=404;res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const url='http://127.0.0.1:'+server.address().port;
const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox']});
for (const file of ['index.html','balatro.html']) {
  for (const width of [1200,390]) {
  const page=await (await browser.newContext({viewport:{width,height:900}})).newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url+'/'+file);
  assert.equal(await page.isHidden('#saved-builds'),true,'no saved builds yet');
  await page.click('#mode-custom');
  await page.check('input[value=paperback]');await page.check('input[value=bunco]');
  assert.equal(await page.isVisible('#vanilla-save-row'),true);
  await page.check('input[value=cryptid]');
  assert.equal(await page.isHidden('#vanilla-save-row'),true,'cryptid hides vanilla save');
  await page.uncheck('input[value=cryptid]');
  await page.check('#vanilla-save');
  assert.match(await page.textContent('#build-summary'),/Vanilla save/);
  // A Vanilla run in progress, stored the way IDBFS stores it.
  await page.evaluate(()=>new Promise(r=>{const q=indexedDB.open('/home/web_user/love-vanilla',21);q.onupgradeneeded=()=>{q.result.createObjectStore('FILE_DATA').createIndex('timestamp','timestamp');};q.onsuccess=()=>{const tx=q.result.transaction('FILE_DATA','readwrite');tx.objectStore('FILE_DATA').put({timestamp:new Date(),mode:33206,contents:new Uint8Array(1)},'/home/web_user/love/1/save.jkr');tx.oncomplete=()=>{q.result.close();r();};};}));
  await page.click('#launch-build');
  await page.waitForSelector('#vanilla-save-dialog[open]');
  await page.waitForSelector('#vanilla-save-run:not([hidden])');
  await page.click('#vanilla-save-cancel');
  assert.equal(await page.isHidden('#loading-overlay'),true,'cancel does not launch');
  assert.equal(await page.evaluate(()=>localStorage.getItem('octopus-saved-builds')),null,'cancel does not save the build');
  // Saved builds render and can be removed without launching.
  await page.evaluate(()=>localStorage.setItem('octopus-saved-builds',JSON.stringify([{key:'bunco-paperback@vanilla',mods:['bunco','paperback'],min:0.1,max:10,vanillaSave:true,lastPlayed:2},{key:'handy-randomizer-designed-v3-1-5',mods:['handy','randomizer'],min:1,max:5,vanillaSave:false,lastPlayed:1}])));
  await page.reload();
  assert.equal(await page.isVisible('#saved-builds'),true);
  const names=await page.$$eval('.saved-build-play',b=>b.map(x=>x.textContent));
  assert.deepEqual(names,['Bunco + PaperbackVanilla save','Handy + Randomizer 1×–5×Own save'].map(x=>x));
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  assert.equal(overflow,false,'no horizontal scroll');
  // Removing a saved build deletes its cached archive, and only that one.
  const putArchive=key=>page.evaluate(key=>new Promise(r=>{const q=indexedDB.open('octopus-saved-build-archives',1);q.onupgradeneeded=()=>q.result.createObjectStore('archives');q.onsuccess=()=>{const tx=q.result.transaction('archives','readwrite');tx.objectStore('archives').put({archive:new Uint8Array(4),config:{}},key);tx.oncomplete=()=>{q.result.close();r();};};}),key);
  const archiveKeys=()=>page.evaluate(()=>new Promise(r=>{const q=indexedDB.open('octopus-saved-build-archives',1);q.onsuccess=()=>{const k=q.result.transaction('archives').objectStore('archives').getAllKeys();k.onsuccess=()=>{q.result.close();r(k.result);};};}));
  await putArchive('bunco-paperback@vanilla');await putArchive('handy-randomizer-designed-v3-1-5');
  await page.click('.saved-build-remove >> nth=1');
  assert.equal(await page.$$eval('.saved-build',x=>x.length),1);
  await page.waitForFunction(()=>true);await page.waitForTimeout(200);
  assert.deepEqual(await archiveKeys(),['bunco-paperback@vanilla']);
  // Its vanilla-save entry asks for confirmation before launching.
  await page.click('.saved-build-play');
  await page.waitForSelector('#vanilla-save-dialog[open]');
  await page.keyboard.press('Escape');
  assert.equal(await page.isHidden('#loading-overlay'),true);
  assert.deepEqual(errors,[]);
  console.log(file+' at '+width+'px: saved builds, Vanilla save option, run-in-progress warning, cancel and cached-archive removal passed');
  }
}
await browser.close();server.close();
