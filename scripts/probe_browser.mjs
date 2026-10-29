import {chromium} from 'playwright';
import {readFile,writeFile} from 'node:fs/promises';
import {unzipSync,zipSync,strToU8} from 'fflate';
import {spawn} from 'node:child_process';
const debugLua=`
local update_debug=love.update
function love.update(dt,...)
 if love.filesystem.getInfo('probe.lua') then
  local source=love.filesystem.read('probe.lua'); love.filesystem.remove('probe.lua')
  local fn,err=loadstring(source,'@probe.lua')
  if fn then local ok,e=xpcall(fn,debug.traceback); print('PROBE_RESULT '..tostring(ok)..' '..tostring(e)) else print('PROBE_ERROR '..tostring(err)) end
 end
 return update_debug(dt,...)
end
`;
const errorLua="love.errorhandler=function(m) print('PROBE_CRASH '..tostring(m)..debug.traceback()); return function() end end\n";
function patchArchive(bytes){const files=unzipSync(bytes);files['main.lua']=strToU8(errorLua+new TextDecoder().decode(files['main.lua'])+debugLua);return zipSync(files,{level:0});}
let activeLogs=[];setTimeout(async()=>{await writeFile('timeout-browser.log',activeLogs.join('\n'));console.log('TIMEOUT_LOG',activeLogs.slice(-100).join('\n'));process.exit(2);},150000).unref();
const server=spawn('python3',['-m','http.server','8765','--bind','127.0.0.1'],{stdio:'ignore'});
const browser=await chromium.launch({headless:true,args:['--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
for(const mode of ['custom']) {
 const page=await browser.newPage();let logs=[];activeLogs=logs;
 page.on('console',m=>{const line=m.type()+': '+m.text();logs.push(line);if(/error|PROBE|Error|failed/i.test(line))console.log(mode,line)});
 page.on('pageerror',e=>console.log(mode,'PAGEERROR',e.stack));
 page.on('dialog',async d=>{console.log(mode,'DIALOG',d.message());await d.dismiss()});
 if(mode==='handy') {
  const bytes=patchArchive(new Uint8Array(await readFile('vanilla-handy/game.data')));
  await page.route('**/vanilla-handy/game.data*',async route=>route.fulfill({body:Buffer.from(bytes)}));
  await page.route('**/vanilla-handy/game.js*',async route=>{
   const body=(await readFile('vanilla-handy/game.js','utf8')).replace(/remote_package_size: \d+/, 'remote_package_size: '+bytes.length).replace(/end: \d+/, 'end: '+bytes.length);
   await route.fulfill({body,contentType:'text/javascript'});
  });
 }
 if(mode==='custom') {
  await page.route('**/index.html',async route=>{
   const body=(await readFile('index.html','utf8')).replace('window.__octopusBuild=result.config;', 'result=await window.patchProbeArchive(result);window.__octopusBuild=result.config;');
   await route.fulfill({body,contentType:'text/html'});
  });
  await page.addInitScript(({debugLua,errorLua})=>{window.patchProbeArchive=async result=>{
   const {unzipSync,zipSync,strToU8}=await import('/node_modules/fflate/esm/browser.js');
   const files=unzipSync(result.archive);const lobby='Mods/Multiplayer/ui/lobby/lobby.lua';files['main.lua']=strToU8(errorLua+new TextDecoder().decode(files['main.lua'])+debugLua);result.archive=zipSync(files,{level:0});return result;
  };},{debugLua,errorLua});
 }
 if(mode==='handy-file') {
  await page.route('https://api.github.com/**',r=>r.fulfill({json:{sha:'a'.repeat(40)},headers:{'access-control-allow-origin':'*'}}));
  await page.route(url=>['cdn.jsdelivr.net','raw.githubusercontent.com'].includes(url.hostname) && url.pathname.includes('bitball41/octopus-oatmeal'),async r=>{
   const path=new URL(r.request().url()).pathname.match(/[a-f0-9]{40}\/(.*)/)[1];
   await r.fulfill({body:await readFile(path),contentType:path.endsWith('.js')?'text/javascript':'application/octet-stream',headers:{'access-control-allow-origin':'*'}});
  });
 }
 await page.goto(mode==='handy-file'?'file://'+process.cwd()+'/index.html#handy':'http://127.0.0.1:8765/index.html');
 if(mode==='custom') await page.evaluate(()=>window.OctopusLaunch.custom(['cryptid','multiplayer'],{}));
 await page.waitForTimeout(25000);
 await page.screenshot({path:mode+'-boot.png'});
 console.log(mode,'STATUS',await page.locator('#loading-status').textContent());
 const probe=async source=>{
  await page.evaluate(source=>{const path=Module.persistence.mountpoint+'/game';Module.FS_createDataFile(path,'probe.lua',new TextEncoder().encode(source),true,true,true);},source);
  await page.waitForTimeout(6000);
 };
 if(mode==='custom')await probe(`print('PROBE_STATE '..tostring(G.STAGE)..' '..tostring(G.STATE)..' '..tostring(G.OVERLAY_MENU))`);
 if(mode==='custom') {
  await probe(`local function trace(f,depth) if depth>8 then return end;local i=debug.getinfo(f);print('PROBE_FUNC '..depth..' '..i.source..':'..i.linedefined);for n=1,15 do local k,v=debug.getupvalue(f,n);if not k then break end;if type(v)=='function' then print('PROBE_UPVALUE '..k);trace(v,depth+1) end end end;trace(G.FUNCS.start_run,0);G.FUNCS.exit_overlay_menu();G.E_MANAGER.queues.unlock={};G.SETTINGS.paused=false;MP.LOBBY.connected=true;MP.LOBBY.code='TESTX';MP.LOBBY.is_host=true;MP.LOBBY.host={username='Test'};MP.LOBBY.guest={username='Other'};MP.reset_game_states();G.FUNCS.lobby_start_run(nil,{seed='TEST1234',stake=1})`);
  await probe(`for k,q in pairs(G.E_MANAGER.queues) do for i,e in ipairs(q) do local x=debug.getinfo(e.func);print('PROBE_EVENT '..k..' '..i..' '..tostring(e.trigger)..' '..tostring(e.delay)..' '..tostring(e.timer)..' '..tostring(e.time)..' '..tostring(e.created_on_pause)..' '..x.source..':'..x.linedefined) end end;print('PROBE_TIMERS '..G.TIMERS.REAL..' '..G.TIMERS.TOTAL)`);
  await page.screenshot({path:'custom-start.png'});
  await probe(`print('PROBE_RUN '..tostring(G.STAGE)..' '..tostring(G.STATE)..' wipe='..tostring(G.screenwipe)..' paused='..tostring(G.SETTINGS.paused))`);
 }
 await writeFile(mode+'-browser.log',logs.join('\n'));await page.close();
}
}finally{await browser.close();server.kill();}
