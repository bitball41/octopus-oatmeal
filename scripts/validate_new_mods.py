#!/usr/bin/env python3
"""Validate the published Entropy and quality-of-life archives and shared saves."""
import io
import json
import re
import zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

def archive(folder):
    directory = ROOT/folder
    parts = json.loads((directory/'parts.json').read_text()) if (directory/'parts.json').exists() else ['game.data']
    chunks = []
    for part in parts:
        chunk = (directory/part).read_bytes()
        assert 0 < len(chunk) <= 20*1024*1024, (folder, part)
        chunks.append(chunk)
    blob = b''.join(chunks)
    source = (directory/'game.js').read_text()
    assert int(re.search(r'remote_package_size:\s*(\d+)', source)[1]) == len(blob)
    return zipfile.ZipFile(io.BytesIO(blob))

check = LuaRuntime(unpack_returned_tuples=True).eval('function(s,n) local f,e=loadstring(s,n); return f~=nil,e end')
handy = archive('vanilla-handy')
entropy = archive('entropy')
for z in (handy, entropy):
    for name in z.namelist():
        if name.endswith('.lua'):
            ok, error = check(z.read(name).decode(), name)
            assert ok, (name, error)
assert 'Mods/JokerDisplay/JokerDisplay.lua' in handy.namelist()
assert 'Mods/Overflow/Overflow.lua' in handy.namelist()
assert not any(name.startswith('Mods/Steamodded/') for name in handy.namelist())
assert 'Mods/Entropy/Entropy.lua' in entropy.namelist()
assert 'Mods/Spectrallib/main.lua' in entropy.namelist()
assert 'Mods/Handy/index.lua' in entropy.namelist()
assert not any(name.startswith('Mods/Cryptid/') for name in entropy.namelist())
assert "^E[123]$" in entropy.read('game.lua').decode()
assert 'self:load_profile(G.SETTINGS.profile)' in entropy.read('game.lua').decode()
assert 'const int hcount = 17;' in entropy.read('Mods/Entropy/assets/shaders/freaky.fs').decode()
assert 'sample_i < 22' in entropy.read('Mods/Entropy/assets/shaders/pulseoutline.fs').decode()
for name in ('index.html', 'balatro.html'):
    text = (ROOT/name).read_text()
    assert 'id="mode-entropy"' in text and 'bindMode("mode-entropy", "entropy")' in text
    assert 'persist: "/home/web_user/love-entropy"' in text
    assert 'Includes JokerDisplay overlays and Overflow' in text

# Plain Vanilla must expand saved stacks without losing quantity or mutating the source.
lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute('''
function copy_table(t)
    local r={}; for k,v in pairs(t) do r[k]=type(v)=='table' and copy_table(v) or v end; return r
end
CardArea={load=function(self,saved) self.saved=saved; return 'loaded' end}
''')
lua.execute((ROOT/'browser/lua/browser/vanilla_stacks.lua').read_text())
lua.execute('''
local source={config={card_count=4},cards={
    {key='c_pluto',overflow_amount=3,ability={test=7}}, {key='c_mars'}
}}
local area=setmetatable({}, {__index=CardArea})
assert(area:load(source)=='loaded')
assert(#area.saved.cards==4 and area.saved.cards[3].key=='c_pluto')
assert(area.saved.cards[1] ~= area.saved.cards[2])
area.saved.cards[1].ability.test=8
assert(source.cards[1].ability.test==7 and source.cards[1].overflow_amount==3)
local original={config={},cards={{key='j_joker'}}}
area:load(original); assert(area.saved==original)
local previous=area.saved
local ok,err=pcall(function()area:load({cards={{overflow_amount=10001}}})end)
assert(not ok and err:find('Vanilla + Handy',1,true) and area.saved==previous)
''')
# Profile metadata must be loaded before mod discovery, including a saved E2/E3.
source = entropy.read('game.lua').decode()
start = source.index('function Game:start_up()')
end = source.index('    self:init_item_prototypes()', start)
startup = source[start:end] + '    self:init_item_prototypes()\nend\n'
start = source.index('function Game:load_profile(')
end = source.index('\nfunction Game:set_language', start)
load_profile = source[start:end]
lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute(entropy.read('browser/bignum_compare.lua').decode())
lua.execute("""
Game={};Cryptid={}
EventManager=function()return {}end
Controller=function()return {}end
boot_timer=function()end
love={thread={newThread=function()return {start=function()end}end,getChannel=function()return {}end},
      filesystem={getDirectoryItems=function()return {}end,getInfo=function()return nil end},
      joystick={loadGamepadMappings=function()end}}
function profile_init_table()return {ver=0,career_stats={}}end
function Game:load_all_files()end
function Game:set_render_settings()end
function Game:set_language()end
function Game:init_item_prototypes()
    assert(self.PROFILES[self.SETTINGS.profile].marker==123)
    assert(self.PROFILES[self.SETTINGS.profile].career_stats)
    self.prototype_test_passed=true
end
""")
lua.execute(load_profile+startup)
lua.execute("""
for _,profile in ipairs({'E1','E2','E3'})do
    G=setmetatable({VERSION='1.0.1o',PROFILES={},SETTINGS={GRAPHICS={}},C={SO_1={},SUITS={}},
        FILES={['settings.jkr']={profile=profile,profile_counters={[profile]=9}},
               [profile..'/profile.jkr']={marker=123,ver=7}}},{__index=Game})
    G:start_up()
    assert(G.prototype_test_passed and G.SETTINGS.profile==profile)
end
""")
print('Entropy/QoL: Lua 5.1 compilation, package sizes, preset isolation, selector and shared-stack saves passed')
