"""Exercise packed Steamodded constructor/Gradient registration under Lua 5.1."""
import sys
import zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime
root = Path(__file__).resolve().parents[1]
z = zipfile.ZipFile(sys.argv[1] if len(sys.argv) > 1 else root/'game.data')
lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute(z.read('engine/object.lua').decode())
lua.execute('''
SMODS = {}
-- No mod or prefix defaults exist for the built-in warning gradients.
function SMODS.merge_defaults(value) return value or {} end
warnings = {}
function sendWarnMessage(message) warnings[#warnings+1]=message end
G={C={RED={1,0,0,1}, GREEN={0,1,0,1}, WHITE={1,1,1,1}},TIMERS={REAL=0.25}}
''')
source = z.read('Mods/Steamodded/src/game_object.lua').decode()
a = source.index('    SMODS.GameObject = Object:extend()')
b = source.index('    function SMODS.GameObject:process_loc_text()', a)
lua.execute(source[a:b])
a = source.index('    SMODS.Gradients = {}')
b = source.index('    -------------------------------------------------------------------------------------------------', a)
lua.execute(source[a:b])
lua.execute('''
assert(SMODS.Gradients.warning_bg.registered)
assert(SMODS.Gradients.warning_text.registered)
assert(SMODS.Gradients.warning_bg.set==nil)
assert(SMODS.Gradients.warning_bg.cycle==1)
local count=#SMODS.Gradient.obj_buffer
SMODS.Gradient{key='warning_bg'}
assert(#SMODS.Gradient.obj_buffer==count and #warnings>0, 'duplicate registration changed')
local ok,err=pcall(function() SMODS.Gradient{} end)
assert(not ok and string.find(err,'Missing required parameter for GameObject declaration: key',1,true),
 'missing key must fail with the intended diagnostic')
local Named=SMODS.GameObject:extend{set='Test',obj_table={},obj_buffer={},required_params={'key','enabled'}}
local obj=Named{key='valid',enabled=false}
assert(obj.registered and obj.enabled==false, 'false is a valid required value')
ok,err=pcall(function() Named{key='invalid'} end)
assert(not ok and string.find(err,'Missing required parameter for Test declaration: enabled',1,true))
''')
print('Packed Lua 5.1 registration passed: both startup gradients, duplicates, missing keys, named classes and false-valued fields')
