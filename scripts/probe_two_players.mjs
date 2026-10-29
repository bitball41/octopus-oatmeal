import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import {readFile,writeFile} from 'node:fs/promises';
import {spawn} from 'node:child_process';
const rooms=new Map(),logs=[],replies=new Map();let sequence=0;
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const debugLua=`
local update_probe=love.update
function love.update(dt,...)
 if love.filesystem.getInfo('probe.lua') then
  local source=love.filesystem.read('probe.lua');love.filesystem.remove('probe.lua')
  local fn,err=loadstring(source,'@probe.lua');if fn then local ok,e=xpcall(fn,debug.traceback);if not ok then print('PROBE_FAILURE '..tostring(e)) end else print('PROBE_FAILURE '..tostring(err)) end
 end
 return update_probe(dt,...)
end
`;
const transport=`
PeerRoom.prototype.open=async function(code,role){this.code=code;this.role=role;window.__testPeer=this;await window.probeOpen(code,role);};
PeerRoom.prototype.send=async function(packet){return window.probeSend(this.code,this.role,packet);};
PeerRoom.prototype.close=async function(){};
`;
const server=spawn('python3',['-m','http.server','8765','--bind','127.0.0.1'],{stdio:'ignore'});
const browser=await chromium.launch({headless:true,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const watchdog=setTimeout(async()=>{await writeFile('two-player-browser.log',logs.join('\n'));process.exit(2)},240000);watchdog.unref();
async function until(fn,label,ms=15000){const end=Date.now()+ms;while(!fn()){if(Date.now()>end)throw Error('Timeout: '+label);await delay(50);}}
async function lua(page,code){const id=++sequence;await page.evaluate(({id,code})=>{
 const s=`local value=(function() ${code} end)(); print('PROBE_REPLY ${id} '..require('json').encode(value or {}))`;
 Module.FS_createDataFile('/home/web_user/love/game','probe.lua',new TextEncoder().encode(s),true,true,true);
 },{id,code});await until(()=>replies.has(id),'Lua request '+id);return replies.get(id);}
async function setup(label){
 const page=await browser.newPage();page.on('console',m=>{const t=label+' '+m.type()+': '+m.text();logs.push(t);if(/PROBE|error|Error/.test(t))console.log(t);const match=m.text().match(/^PROBE_REPLY (\d+) (.*)/s);if(match)replies.set(Number(match[1]),JSON.parse(match[2]));});
 page.on('pageerror',e=>{logs.push(label+' PAGEERROR '+e.stack);console.log(label,e.stack)});page.on('dialog',async d=>{console.log(label,'DIALOG',d.message());await d.dismiss()});
 await page.exposeFunction('probeOpen',async(code,role)=>{
  const room=rooms.get(code)||{};room[role]=page;rooms.set(code,room);
  if(room.host&&room.guest)setTimeout(async()=>{
   await room.host.evaluate(()=>{__testPeer.remote='guest';__testPeer.onPeer()});
   await room.guest.evaluate(()=>{__testPeer.remote='host';__testPeer.onPeer()});
  },0);
 });
 await page.exposeFunction('probeSend',async(code,role,packet)=>{
  const other=rooms.get(code)?.[role==='host'?'guest':'host'];if(!other)throw Error('Missing peer');
  await other.evaluate(packet=>__testPeer.onPacket(packet),packet);
 });
 await page.route('**/multiplayer_upstream.js*',async route=>route.fulfill({body:(await readFile('multiplayer_upstream.js','utf8'))+transport,contentType:'text/javascript'}));
 await page.route('**/index.html',async route=>route.fulfill({body:(await readFile('index.html','utf8')).replace('window.__octopusBuild=result.config;','result=await window.patchProbeArchive(result);window.__octopusBuild=result.config;'),contentType:'text/html'}));
 await page.addInitScript(({debugLua})=>{window.patchProbeArchive=async result=>{
  const {unzipSync,zipSync,strToU8}=await import('/node_modules/fflate/esm/browser.js');const files=unzipSync(result.archive);
  files['main.lua']=strToU8("love.errorhandler=function(m) print('PROBE_CRASH '..tostring(m)..debug.traceback());return function() end end\n"+new TextDecoder().decode(files['main.lua'])+debugLua);
  result.archive=zipSync(files,{level:0});return result;
 };},{debugLua});
 await page.goto('http://127.0.0.1:8765/index.html');await page.evaluate(()=>OctopusLaunch.custom(['cryptid','multiplayer'],{}));await delay(25000);
 for(let i=0;i<35;i++) {
  const state=await lua(page,"G.FUNCS.exit_overlay_menu();G.E_MANAGER.queues.unlock={};return {stage=G.STAGE,state=G.STATE,menu=G.STATES.MENU}");
  if(state.state===state.menu)return page;
  await delay(1500);
 }
 throw Error(label+' did not reach the main menu');
}
try {
 const [host,guest]=await Promise.all([setup('HOST'),setup('GUEST')]);
 await lua(host,"G.FUNCS.create_lobby(nil)");await until(()=>rooms.size,'host room');const code=[...rooms.keys()][0];
 await lua(guest,`Client.send({action='joinLobby',code='${code}'})`);
 await delay(6000);console.log('HOST LOBBY',await lua(host,"return {code=MP.LOBBY.code,guest=MP.LOBBY.guest.username,host=MP.LOBBY.is_host}"));
 await lua(guest,"MP.ACTIONS.ready_lobby()");await delay(2000);
 const ready=await lua(host,"return {ready=MP.LOBBY.ready_to_start}");assert.equal(ready.ready,true,'guest ready reaches host');
 await lua(host,"G.FUNCS.lobby_start_game(nil)");await delay(15000);
 for(const [label,page] of [['host',host],['guest',guest]]) {
  let state;
  for(let i=0;i<30;i++) {
   state=await lua(page,"return {stage=G.STAGE,run=G.STAGES.RUN,state=G.STATE,paused=not not G.SETTINGS.paused,loading=not not G.CONTROLLER.locks.load,seed=G.GAME.pseudorandom.seed}");
   if(state.stage===state.run&&!state.loading)break;
   await delay(1500);
  }
  console.log('FINAL',label,JSON.stringify(state));await page.screenshot({path:label+'-run.png'});
  assert.equal(state.stage,state.run,label+' enters a run');assert.equal(state.loading,false,label+' finishes loading');
 }
 assert(!logs.some(x=>/PROBE_CRASH|PROBE_FAILURE|Lua Error in love.update/.test(x)),'no Lua crashes');
 console.log('PASS: two real Cryptid multiplayer engines create, join, ready and start a run');
}finally{await writeFile('two-player-browser.log',logs.join('\n'));await browser.close();server.kill();clearTimeout(watchdog);}
