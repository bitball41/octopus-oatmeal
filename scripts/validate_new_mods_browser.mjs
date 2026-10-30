// Run with: python scripts/prepare_mod_smoke.py && node scripts/validate_new_mods_browser.mjs
import {chromium} from 'playwright';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import http from 'node:http';
import path from 'node:path';
const root=path.resolve(new URL('../',import.meta.url).pathname);
const server=http.createServer((req,res)=>{
  try {
    let relative=decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/^\//,'')||'index.html';
    if(relative.startsWith('vanilla-handy/')||relative.startsWith('entropy/')) relative='build/mod-smoke/'+relative;
    const file=path.resolve(root,relative);
    if(!file.startsWith(root+path.sep))throw new Error('outside test root');
    res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.wasm')?'application/wasm':file.endsWith('.html')?'text/html':'application/octet-stream');
    res.end(readFileSync(file));
  }catch{res.statusCode=404;res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const url='http://127.0.0.1:'+server.address().port;
let browser;
try {
  for(const [mode,success] of [['handy','PROBE CONSTELLATION NIL CONTEXT PASSED'],['entropy','PROBE ENTROPY HAND SCORED']]) {
    if(process.env.TEST_MOD && process.env.TEST_MOD!==mode)continue;
    browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--no-zygote','--single-process','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
    const context=await browser.newContext({viewport:{width:1200,height:800}});
    const page=await context.newPage(); const logs=[];let completed=false;
    page.on('console',m=>{logs.push(m.text());if(m.text().includes('PROBE'))console.log(m.text());});page.on('pageerror',e=>logs.push('PAGEERROR '+e.stack));
    await page.goto(url+'/#'+mode);
    for(let i=0;i<100;i++) {
      await page.waitForTimeout(1000);
      if(logs.some(x=>x.includes(success))){completed=true;break;}
      if(logs.some(x=>x.includes('Oops! The game crashed')||x.includes('[Lua Error in love.update]')||x.startsWith('PAGEERROR ')))break;
      if(i===5)await page.mouse.click(600,400);
      if(mode==='entropy' && i>5 && i%5===0)await page.mouse.click(600,540);
    }
    mkdirSync(root+'/build/mod-smoke',{recursive:true});
    await page.screenshot({path:root+'/build/mod-smoke/'+mode+'.png'});
    writeFileSync(root+'/build/mod-smoke/'+mode+'.log',logs.join('\n'));
    if(completed)console.log(mode+' browser integration passed');
    if(!completed)throw new Error(mode+' browser probe failed; see build/mod-smoke/'+mode+'.log');
    await browser.close();browser=null;
  }
}finally{if(browser)await browser.close();server.close();}
