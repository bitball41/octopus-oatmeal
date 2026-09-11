"""Packed NativeFS regression: optional config, native read overloads, errors."""
from pathlib import Path
import zipfile
from lupa.lua51 import LuaRuntime
root = Path(__file__).resolve().parents[1]
z = zipfile.ZipFile(root / 'game.data')
lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute('''
files={['Mods/Steamodded/config.lua']='return {enabled=true}', ['config/Steamodded.jkr']='return {enabled=false}'}
reads=0
love={filesystem={
 getSaveDirectory=function() return '/save' end,
 getInfo=function(p) if files[p] then return {type='file'} end end,
 read=function(a,b,c)
  reads=reads+1
  local typed=type(b)=='string'; local p=typed and b or a
  assert(files[p], 'missing-file backend must not be called')
  if files[p]=='BROKEN' then error('read failed') end
  local bytes=files[p];local size=typed and c or b
  if size then bytes=string.sub(bytes,1,size) end
  return typed and a=='data' and {bytes=bytes} or bytes,#bytes
 end
}}
''')
lua.globals().NFS = lua.execute(z.read('browser/nativefs.lua').decode())
ui=z.read('Mods/Steamodded/src/ui.lua').decode()
a=ui.index('function SMODS.load_mod_config(mod)');b=ui.index('SMODS:load_mod_config()',a)
lua.execute('SMODS={};load=loadstring\n'+ui[a:b])
lua.execute('''
local mod={id='Steamodded',path='Mods/Steamodded/'}
assert(SMODS.load_mod_config(mod).enabled==false, 'saved config ignored')
files['config/Steamodded.jkr']=nil
local before=reads
local data,err=NFS.read('config/Steamodded.jkr')
assert(data==nil and type(err)=='string' and reads==before)
assert(SMODS.load_mod_config(mod).enabled==true, 'first boot defaults lost')
assert(NFS.read('/save/Mods/Steamodded/config.lua')=='return {enabled=true}')
assert(NFS.read('Mods/Steamodded/config.lua',6)=='return')
assert(NFS.read('Mods/Steamodded/config.lua','all')=='return {enabled=true}')
assert(NFS.read('data','Mods/Steamodded/config.lua',6).bytes=='return')
assert(NFS.read('string','Mods/Steamodded/config.lua',6)=='return')
files['config/Steamodded.jkr']='BROKEN'
data,err=NFS.read('config/Steamodded.jkr')
assert(data==nil and string.find(err,'read failed',1,true))
assert(SMODS.load_mod_config(mod).enabled==true)
-- Upstream serialization temporarily removes string's metatable. NativeFS
-- path normalization must not depend on colon-method lookup on strings.
local mt=getmetatable('');debug.setmetatable('',nil)
local ok,value=pcall(NFS.read,'Mods/Steamodded/config.lua')
debug.setmetatable('',mt)
assert(ok and value=='return {enabled=true}', 'string indexing regression')
''')
print('Packed NativeFS/config regression passed: first boot, saved config, typed/sized reads, backend error, string metatable isolation')
