#!/usr/bin/env python3
"""Verify actual Lua 5.1 code, mixed OmegaNum comparisons and save round-trips."""
import io
import json
import zipfile
import subprocess
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

def validate_startup(files):
    """Exercise real startup through prototype discovery with persisted settings."""
    source = files['game.lua'].decode()
    start = source.index('function Game:start_up()')
    end = source.index('    self:init_item_prototypes()', start)
    startup = source[start:end] + '    self:init_item_prototypes()\nend\n'
    start = source.index('function Game:load_profile(')
    end = source.index('\nfunction Game:set_language', start)
    load_profile = source[start:end]
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(files['browser/bignum_compare.lua'].decode())
    lua.execute('''
        Game = {}
        Cryptid = {}
        EventManager = function() return {} end
        Controller = function() return {} end
        boot_timer = function() end
        love = {
            thread = {
                newThread = function() return {start=function() end} end,
                getChannel = function() return {} end
            },
            filesystem = {getDirectoryItems=function() return {} end},
            joystick = {loadGamepadMappings=function() end}
        }
        function profile_init_table() return {ver=0, career_stats={}} end
        function Game:load_all_files() end
        function Game:set_render_settings() end
        function Game:set_language() end
        function Game:init_item_prototypes()
            assert(self.PROFILES[self.SETTINGS.profile].marker == 123)
            assert(self.PROFILES[self.SETTINGS.profile].career_stats)
            assert(self.PROFILES[self.SETTINGS.profile].ver == 9)
            self.prototype_test_passed = true
        end
    ''')
    lua.execute(load_profile + startup)
    lua.execute('''
        for _, profile in ipairs({'M1','M2','M3'}) do
            G = setmetatable({
                VERSION='1.0.1o', PROFILES={},
                SETTINGS={GRAPHICS={}},
                C={SO_1={}, SUITS={}},
                FILES={['settings.jkr']={profile=profile, profile_counters={[profile]=9}},
                    [profile..'/profile.jkr']={marker=123, ver=7}}
            }, {__index=Game})
            G:start_up()
            assert(G.prototype_test_passed and G.SETTINGS.profile==profile)
        end
    ''')


def validate_compiler(lua):
    fixture = '''
        local calls = 0
        local function once(v) calls=calls+1; return v end
        local big = to_big(125)
        assert(once(big) >= once(125))
        assert(calls == 2)
        assert(big == 125 and 125 == big and big ~= 126)
        assert(not (big == nil) and not (big == true) and not (big == '125'))
        assert(#{} < 1 and type(big) == 'table' and not false == true)
        assert((1+2)*3 >= 9 and 'a' < 'b')
        local native_type = type
        type = function(v) return Big.is(v) and 'cdata' or native_type(v) end
        assert(big > 124 and big == 125)
        type = native_type
    '''
    compiled = subprocess.run(['node', str(ROOT/'scripts/compile_cryptid_lua.mjs')],
        input=json.dumps({'fixture.lua':fixture}), text=True, capture_output=True, check=True)
    result = json.loads(compiled.stdout)['fixture.lua']
    assert '__octopus_ge(once(big), once(125))' in result
    assert "big == nil" in result and '#{} < 1' in result
    lua.execute(result)


def validate_geometry(files):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(files['browser/bignum_compare.lua'].decode())
    lua.execute('''
        function copy_table(t)
            local result={}
            for k,v in pairs(t) do result[k]=v end
            return result
        end
        function EMPTY(t) return {} end
        function point_translate(p,t) p.x,p.y=p.x+t.x,p.y+t.y end
        function point_rotate(p,r)
            p.x,p.y=p.x*math.cos(r)-p.y*math.sin(r),p.x*math.sin(r)+p.y*math.cos(r)
        end
        G = {
            SETTINGS={paused=false}, I={NODE={},MOVEABLE={}},
            MOVEABLES={}, STAGE=1, STAGE_OBJECTS={{}}, COLLISION_BUFFER=0,
            TIMERS={REAL=0}, FRAMES={MOVE=0},
            exp_times={xy=math.exp(-50/60),scale=math.exp(-60/60),r=math.exp(-190/60),max_vel=70/60}
        }
    ''')
    for path in ['engine/object.lua','engine/node.lua','engine/moveable.lua']:
        source = files[path].decode()
        if path != 'engine/object.lua':
            assert '__octopus_' not in source, 'Geometry should use native comparisons'
        lua.execute(source)
    lua.execute('''
        G.ROOM=Node({T={x=0,y=0,w=20,h=10}})
        G.ROOM:set_container(G.ROOM)
        local major=Moveable(0,0,1,2)
        local child=Moveable(0,0,1,1)
        child:set_role({role_type='Minor',major=major,offset={x=0.2,y=0.3}})
        major.T.x,major.T.y=4,3
        for frame=1,180 do
            G.FRAMES.MOVE=frame; G.TIMERS.REAL=frame/60
            major:move(1/60); child:move(1/60)
        end
        assert(math.abs(major.VT.x-4)<0.01 and math.abs(major.VT.y-3)<0.01)
        assert(math.abs(child.T.x-4.2)<0.01 and math.abs(child.T.y-3.3)<0.01)
        assert(major:collides_with_point({x=4.5,y=3.5}))
        assert(not major:collides_with_point({x=8,y=8}))
        major.T.r=math.pi/4
        assert(major:collides_with_point({x=4.5,y=4}))
        -- Geometry keeps native math even after the score library replaces it.
        for _,key in ipairs({'abs','min','max','sin','cos','sqrt'}) do
            math[key]=function() error('Score math entered the geometry loop') end
        end
        G.FRAMES.MOVE=181; major.T.x=5; major:move(1/60)
    ''')

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
        assert(not __octopus_eq(Big.constants.NaN,Big.constants.NaN))
        assert(__octopus_ne(Big.constants.NaN,Big.constants.NaN))
        assert(__octopus_gt(to_big('1e1000'), to_big('1e999')))
        local t = {}; assert(__octopus_eq(t,t) and __octopus_ne(t,{}))
        assert(__octopus_lt('a','b') and __octopus_eq(true,true))
        love = {filesystem={getSaveDirectory=function() return '/save' end}, system={}}
        function number_format(v) return tostring(v.number) end
        Object = {}
        Talisman = {}
        load = loadstring
    ''')
    validate_compiler(lua)
    validate_startup(files)
    validate_geometry(files)
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
    print(f'Cryptid: {count} Lua files compiled; profile reload, geometry, compiler, arithmetic, comparisons and save round-trip passed')

if __name__ == '__main__':
    main()
