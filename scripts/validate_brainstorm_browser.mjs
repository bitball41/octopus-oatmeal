// Run with: node scripts/validate_brainstorm_browser.mjs
// (BRAINSTORM_BUILD=handy node scripts/validate_brainstorm_browser.mjs for a Custom Build)
// Boots Vanilla + Brainstorm from the launcher in Chromium, checks Brainstorm's
// predictions against the game's own rolls, then drives its keys: Shift+A
// auto-reroll (Charm Tag + The Soul), Shift+T reroll and X+1 load state.
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
      if(!source.endsWith(tail))throw new Error('brainstorm.lua must end with return Brainstorm');
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
  // BRAINSTORM_BUILD=handy,paperback checks a Custom Build instead of Vanilla + Brainstorm.
  const mods=(process.env.BRAINSTORM_BUILD||'').split(',').filter(Boolean);
  if(mods.length){
    await page.goto(url+'/index.html');
    await page.waitForFunction(()=>window.OctopusLaunch&&window.OctopusLaunch.custom);
    await page.evaluate(mods=>window.OctopusLaunch.custom([...mods,'brainstorm'],{}),mods);
  } else await page.goto(url+'/index.html#brainstorm');
  // Cryptid opens with a first-launch intro; click its Next button until the menu is up.
  if(mods.includes('cryptid'))for(let i=0;i<240&&!seen('PROBE MENU PASSED');i++){await page.waitForTimeout(2500);await page.mouse.click(598,537);}
  await waitFor('PROBE READY FOR AUTOREROLL',Number(process.env.BRAINSTORM_BOOT_SECONDS||240));
  await page.mouse.click(600,400);
  await chord('Shift','a');
  await waitFor('PROBE AUTOREROLL STARTED',10);
  await waitFor('PROBE READY FOR FAST REROLL',300);
  // A plain T (no Shift) must not reroll.
  await page.keyboard.press('t');await page.waitForTimeout(2500);
  if(seen('PROBE FAST REROLL PASSED'))throw new Error('T without Shift rerolled the run');
  await chord('Shift','t');
  await waitFor('PROBE READY FOR LOAD STATE',30);
  await chord('x','1');
  await waitFor('PROBE BRAINSTORM ALL PASSED',30);
  console.log((mods.length?'Custom Build ('+mods.join(' + ')+') + Brainstorm':'Vanilla + Brainstorm')+' browser check passed');
} finally {
  mkdirSync(root+'/build/mod-smoke',{recursive:true});
  if(page)await page.screenshot({path:root+'/build/mod-smoke/brainstorm.png'}).catch(()=>{});
  writeFileSync(root+'/build/mod-smoke/brainstorm.log',logs.join('\n'));
  await browser.close();server.close();
}
