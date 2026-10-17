#!/usr/bin/env python3
"""Verify actual Lua 5.1 code, mixed OmegaNum comparisons and save round-trips."""
import io
import json
import zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

def main():
    directory = ROOT/'cryptid'
    parts = json.loads((directory/'parts.json').read_text())
    chunks = [(directory/name).read_bytes() for name in parts]
    assert all(0 < len(chunk) <= 18*1024*1024 for chunk in chunks)
    archive = zipfile.ZipFile(io.BytesIO(b''.join(chunks)))
    files = {name: archive.read(name) for name in archive.namelist()}
    for path in ['Mods/Cryptid/Cryptid.lua', 'Mods/Amulet/smods.lua', 'browser/bignum_compare.lua']:
        assert path in files, path
    assert not any(name.startswith('Mods/Multiplayer/') for name in files)
    assert files['Mods/Steamodded/version.lua'].decode().strip() == 'return "26.829.0"'
    assert 'Talisman.patch_ok = true' in files['main.lua'].decode()
    lua = LuaRuntime(unpack_returned_tuples=True)
    compile_lua = lua.eval('function(s,n) local f,e=loadstring(s,n); return f~=nil,e end')
    count = 0
    for name, data in files.items():
        if name.endswith('.lua'):
            ok, error = compile_lua(data.decode(), '@'+name)
            assert ok, f'{name}: {error}'
            count += 1
    preload = lua.eval('function(n,s) package.preload[n] = assert(loadstring(s,"@"..n)) end')
    for name, data in files.items():
        if name.startswith('big-num/') and name.endswith('.lua'):
            preload(name[:-4].replace('/','.'), data.decode())
    lua.execute(files['browser/bignum_compare.lua'].decode())
    lua.execute('''
        Big = require('big-num.omeganum')
        function to_big(v, sign) return Big:create(v, sign) end
        local a, b = to_big(125), to_big(5)
        assert((a+b):to_number() == 130)
        assert((a*b):to_number() == 625)
        assert((a/b):to_number() == 25)
        assert(a:clone():to_number() == 125)
        assert(__octopus_gt(a,124) and __octopus_lt(124,a))
        assert(__octopus_le(125,a) and __octopus_ge(a,125))
        assert(__octopus_eq(a,125) and __octopus_eq(125,a))
        assert(__octopus_ne(a,b) and not __octopus_eq(a,nil))
        assert(__octopus_lt(to_big(-5),0))
        assert(not __octopus_lt(Big.constants.NaN,0))
        assert(__octopus_gt(to_big('1e1000'), to_big('1e999')))
        local t = {}; assert(__octopus_eq(t,t) and __octopus_ne(t,{}))
        assert(__octopus_lt('a','b') and __octopus_eq(true,true))
        love = {filesystem={getSaveDirectory=function() return '/save' end}, system={}}
        function number_format(v) return tostring(v.number) end
        Object = {}
        Talisman = {}
        load = loadstring
    ''')
    lua.execute(files['engine/string_packer.lua'].decode())
    lua.execute(files['talisman/sanitizer.lua'].decode())
    shader_adapter = files['talisman/break_inf/sanitizer.lua'].decode()
    shader_adapter = shader_adapter[shader_adapter.index('local Shader ='):shader_adapter.index('local lg_translate')]
    lua.execute('debug.getregistry().Shader = {send=function(self,name,value) return value end}')
    lua.execute('local reg=debug.getregistry(); local config={sanitize_graphics=false}; local sanitizer={};\n' + shader_adapter)
    lua.execute('local s=debug.getregistry().Shader; assert(s:send("time",42)==42)')
    lua.execute('''
        local original = {chips=to_big('1e1000'), mult=to_big(125), ordinary='preserved'}
        local packed = STR_PACK(original)
        local restored = STR_UNPACK(packed)
        assert(Big.is(restored.chips) and __octopus_eq(restored.chips,original.chips))
        assert(__octopus_eq(restored.mult,125) and restored.ordinary=='preserved')
    ''')
    print(f'Cryptid: {count} Lua files compiled; CDN parts, arithmetic, comparisons and save round-trip passed')

if __name__ == '__main__':
    main()
