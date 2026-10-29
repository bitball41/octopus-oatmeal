// Exercise optional controller startup through the shipped LÖVE WASM.
import assert from 'node:assert/strict';
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import vm from 'node:vm';
import {zipSync,strToU8} from 'fflate';
const root=resolve(new URL('..',import.meta.url).pathname);
const temporary=await mkdtemp(join(tmpdir(),'optional-gamepads-'));
try {
 await writeFile(join(temporary,'game.love'),zipSync({
  'conf.lua':strToU8(`function love.conf(t)
   t.window=false
   for key in pairs(t.modules) do t.modules[key]=false end
   t.modules.event=true; t.modules.timer=true; t.modules.joystick=true
  end`),
  'main.lua':strToU8(`print('OPTIONAL_GAMEPAD_BOOT_OK')
   function love.run() return function() return 0 end end`),
 }));
 await writeFile(join(temporary,'boot.cjs'),`
  const fs=require('fs'),vm=require('vm');
  global.__dirname=${JSON.stringify(root)};global.require=require;
  Object.defineProperty(global,'navigator',{value:{},configurable:true});
  global.alert=message=>console.error(message);
  global.Module={arguments:['./game.love'],INITIAL_MEMORY:256000000,
   wasmBinary:fs.readFileSync(${JSON.stringify(join(root,'love.wasm'))}),
   print:console.log,printErr:console.error,
   preRun:[function(){Module.FS_createDataFile('/','game.love',fs.readFileSync(${JSON.stringify(join(temporary,'game.love'))}),true,true,true)}]};
  vm.runInThisContext(fs.readFileSync(${JSON.stringify(join(root,'love.js'))},'utf8')+'\\nglobal.Love=Love;');
  Love(Module);
 `);
 const result=spawnSync(process.execPath,[join(temporary,'boot.cjs')],{encoding:'utf8',timeout:10000});
 assert.equal(result.status,0,result.stderr);
 assert.match(result.stdout,/OPTIONAL_GAMEPAD_BOOT_OK/,result.stderr);
 assert.doesNotMatch(result.stderr,/before the game window|Could not initialize SDL joystick/);
 const engine=await readFile(join(root,'love.js'),'utf8');
 const begin=engine.indexOf('    function _emscripten_sample_gamepad_data()');
 const end=engine.indexOf('    function __registerBeforeUnloadEventCallback',begin);
 const scope={navigator:{getGamepads(){throw new Error('Gamepad access denied');}},JSEvents:{}};
 vm.createContext(scope);vm.runInContext(engine.slice(begin,end),scope);
 assert.equal(scope._emscripten_sample_gamepad_data(),0);
 assert.equal(scope.JSEvents.lastGamepadState.length,0);
 const pads=[{id:'working controller'}];scope.navigator.getGamepads=()=>pads;
 assert.equal(scope._emscripten_sample_gamepad_data(),0);
 assert.equal(scope.JSEvents.lastGamepadState,pads);
 console.log('Optional controllers: WASM boots without Gamepad API; denied access falls back; supported controllers remain available');
}finally{await rm(temporary,{recursive:true,force:true});}
