// Run with: node scripts/validate_brainstorm_browser.mjs
// (BRAINSTORM_BUILD=handy for a Custom Build; BRAINSTORM_WORKERS=none or failing
// to check the search falls back to the page when Web Workers cannot run)
// Boots Vanilla + Brainstorm Rerolled + Handy from the launcher in Chromium, checks
// that its WebAssembly searcher agrees with the game's own rolls, then drives
// its keys: Z+1 save state, Shift+A auto-reroll with the Charm + Soul starter
// filter (plain A must not search), Shift+R reroll and X+1 load state.
import {chromium} from 'playwright';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import http from 'node:http';
import path from 'node:path';
const root=path.resolve(new URL('../',import.meta.url).pathname);
const probe=readFileSync(root+'/scripts/probes/brainstorm.lua','utf8');
const server=http.createServer((req,res)=>{
  try {
    const relative=decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/^\//,'')||'index.html';
    const file=path.resolve(root,relative);
    if(!file.startsWith(root+path.sep))throw new Error('outside test root');
    let body=readFileSync(file);
    if(relative==='browser/brainstorm.lua') {
      const source=body.toString();const tail='\nreturn Brainstorm\n';
      if(!source.endsWith(tail))throw new Error('browser/brainstorm.lua must end with return Brainstorm');
      body=Buffer.from(source.slice(0,-tail.length)+'\n'+probe+tail);
    }
    res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.wasm')?'application/wasm':file.endsWith('.html')?'text/html':'application/octet-stream');
    res.end(body);
  }catch{res.statusCode=404;res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const url='http://127.0.0.1:'+server.address().port;
const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const logs=[];let page;
const seen=text=>logs.some(x=>x.includes(text));
async function waitFor(text,seconds){
  for(let i=0;i<seconds*4;i++){
    if(seen(text))return;
    if(logs.some(x=>x.includes('PROBE FAILED')||x.includes('Oops! The game crashed')||x.includes('[Lua Error')||x.startsWith('PAGEERROR ')))break;
    await page.waitForTimeout(250);
  }
  throw new Error('Brainstorm browser check stopped before: '+text);
}
// Hold keys for a few frames, as a person does.
async function chord(modifier,key){
  await page.keyboard.down(modifier);await page.waitForTimeout(80);
  await page.keyboard.down(key);await page.waitForTimeout(80);
  await page.keyboard.up(key);await page.waitForTimeout(40);await page.keyboard.up(modifier);
}
try {
  page=await (await browser.newContext({viewport:{width:1200,height:800}})).newPage();
  page.on('console',m=>{logs.push(m.text());if(m.text().includes('PROBE'))console.log(m.text());});
  page.on('pageerror',e=>logs.push('PAGEERROR '+e.stack));
  // BRAINSTORM_WORKERS=none (no Web Workers) or failing (every worker
  // crashes): the search must still finish on the page.
  const workers=process.env.BRAINSTORM_WORKERS;
  if(workers==='none')await page.addInitScript(()=>{delete window.Worker;});
  if(workers==='failing')await page.addInitScript(()=>{const Real=window.Worker;window.Worker=class extends Real{constructor(){super(URL.createObjectURL(new Blob(['onmessage=()=>{throw new Error("test worker crash")}'],{type:'text/javascript'})));}};});
  // BRAINSTORM_BUILD=handy,paperback checks a Custom Build instead of Vanilla + Brainstorm.
  const mods=(process.env.BRAINSTORM_BUILD||'').split(',').filter(Boolean);
  if(mods.length){
    await page.goto(url+'/index.html');
    await page.waitForFunction(()=>window.OctopusLaunch&&window.OctopusLaunch.custom);
    await page.evaluate(mods=>window.OctopusLaunch.custom([...mods,'brainstorm'],{}),mods);
  } else await page.goto(url+'/index.html#brainstorm');
  await waitFor('PROBE READY FOR SAVE STATE',Number(process.env.BRAINSTORM_BOOT_SECONDS||240));
  await page.mouse.click(600,400);
  await chord('z','1');
  await waitFor('PROBE READY FOR AUTOREROLL',30);
  // A plain A (no Shift) must not search.
  await page.keyboard.press('a');await page.waitForTimeout(2500);
  if(seen('PROBE AUTOREROLL STARTED'))throw new Error('A without Shift started a search');
  await chord('Shift','a');
  await waitFor('PROBE AUTOREROLL STARTED',10);
  await waitFor('PROBE READY FOR FAST REROLL',300);
  await chord('Shift','r');
  await waitFor('PROBE READY FOR LOAD STATE',30);
  await chord('x','1');
  await waitFor('PROBE BRAINSTORM ALL PASSED',30);
  if(workers&&!seen('searching on the page instead'))throw new Error('the search did not fall back to the page');
  console.log((mods.length?'Custom Build ('+mods.join(' + ')+') + Brainstorm Rerolled':'Vanilla + Brainstorm Rerolled + Handy')+' browser check passed');
} finally {
  mkdirSync(root+'/build/mod-smoke',{recursive:true});
  if(page)await page.screenshot({path:root+'/build/mod-smoke/brainstorm.png'}).catch(()=>{});
  writeFileSync(root+'/build/mod-smoke/brainstorm.log',logs.join('\n'));
  await browser.close();server.close();
}
