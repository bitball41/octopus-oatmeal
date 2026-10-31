// Smoke-test the actual Fish & Chips web runtime, not just Lua syntax.
// The standalone preset and its eight game.data chunks must exist first.
import { chromium } from 'playwright';
import { createServer } from 'node:http';
import { readFileSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const reportDir=path.join(root,'build','fish-browser-smoke');
mkdirSync(reportDir,{recursive:true});
const server=createServer((req,res)=>{
  try{
    const name=decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/^\/+/,'')||'index.html';
    const file=path.resolve(root,name);
    if(!file.startsWith(root+path.sep)||!existsSync(file))throw new Error('missing file');
    res.setHeader('Content-Type',file.endsWith('.html')?'text/html':file.endsWith('.js')?'text/javascript':file.endsWith('.wasm')?'application/wasm':'application/octet-stream');
    res.end(readFileSync(file));
  }catch(err){res.statusCode=404;res.end('Not found');}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base='http://127.0.0.1:'+server.address().port;
let browser,page,logs=[];
try{
  browser=await chromium.launch({
    headless:true,
    args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader']
  });
  const ctx=await browser.newContext({viewport:{width:1200,height:800}});
  page=await ctx.newPage();
  page.on('console',msg=>logs.push(msg.type().toUpperCase()+' '+msg.text()));
  page.on('pageerror',err=>logs.push('PAGEERROR '+err.stack));
  page.on('requestfailed',req=>logs.push('REQUESTFAILED '+req.url()+' '+req.failure()?.errorText));
  await page.goto(base+'/#fish',{waitUntil:'domcontentloaded'});
  let visible=false;
  for(let i=0;i<95;i++){
    await page.waitForTimeout(1000);
    if(i===7)await page.mouse.click(600,410);
    const state=await page.evaluate(()=>{
      const c=document.getElementById('canvas');
      return {
        mode:window.__octopusMode,
        visible:!!c&&getComputedStyle(c).visibility==='visible'&&c.width>0&&c.height>0,
        width:c?.width,
        height:c?.height,
        loading:!!document.querySelector('#loading-overlay:not(.hidden)'),
      };
    });
    if(state.visible){visible=true;console.log('Fish browser canvas rendered',JSON.stringify(state));break;}
    if(logs.some(x=>/PAGEERROR|Oops! The game crashed|\[Lua Error|Aborted\(|RuntimeError:|out of memory/i.test(x)))break;
  }
  if(visible)await page.waitForTimeout(7000);
  await page.screenshot({path:path.join(reportDir,'fish-browser.png')});
  writeFileSync(path.join(reportDir,'fish-browser.log'),logs.join('\n'));
  const fatal=logs.filter(x=>/PAGEERROR|Oops! The game crashed|\[Lua Error|Aborted\(|RuntimeError:|out of memory/i.test(x));
  console.log('FISH FULL LOG START\n'+logs.slice(0,140).join('\n')+'\nFISH FULL LOG END');
  console.log('FISH FATAL ERRORS\n'+fatal.join('\n'));
  if(!visible||fatal.length)throw new Error('Fish & Chips browser startup failed: rendered='+visible+' errors='+fatal.length);
  console.log('Fish & Chips browser startup passed');
} finally {
  if(browser)await browser.close();
  await new Promise(resolve=>server.close(resolve));
}
