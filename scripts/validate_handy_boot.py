#!/usr/bin/env python3
"""Load the complete packed Handy module tree with a virtual filesystem and UI stubs."""
import io,json,zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime
p=Path(__file__).resolve().parents[1]/'cryptid'
z=zipfile.ZipFile(io.BytesIO(b''.join((p/n).read_bytes() for n in json.loads((p/'parts.json').read_text()))))
lua=LuaRuntime(unpack_returned_tuples=True)
lua.execute(z.read('browser/bignum_compare.lua').decode())
lua.execute(z.read('engine/object.lua').decode())
fs={n:z.read(n).decode() for n in z.namelist() if n.endswith(('.lua','.json'))}
lua.globals().packed=lua.table_from(fs)
lua.execute('''
load=loadstring
function noop() end
function HEX() return {} end
function EMPTY(t) for k in pairs(t) do t[k]=nil end return t end
function copy_table(t) local r={} for k,v in pairs(t or {}) do r[k]=type(v)=='table' and copy_table(v) or v end return r end
function localize(v) return type(v)=='table' and {} or v end
function attention_text() end
function play_sound() end
function juice_card() end
function ease_discard() end
function ease_hands_played() end
function ease_dollars() end
function delay() end
function draw_card() end
function level_up_hand() end
function update_hand_text() end
function add_round_eval_row() end
function UIBox_button(args) return {config=args} end
function create_UIBox_options() return {nodes={{nodes={{nodes={{nodes={}}}}}}}} end
function create_UIBox_game_over() return {nodes={}} end
function create_UIBox_win() return {nodes={}} end
function create_UIBox_hand_tip() end
function create_UIBox_debug_tools() end
function get_compressed() return nil end
function nuGC() end
function save_run() end
Game={start_up=noop,set_render_settings=noop}; Moveable={juice_up=noop}; Card={}; CardArea={}; Tag={};
Controller={}; UIElement={}; Node={}; EventManager={add_event=noop,update=noop,clear_queue=noop};Event={handle=noop}
G={FUNCS={},UIDEF={},C={CHIPS={},DARK_EDITION={},RED={},ORANGE={}},
SETTINGS={GRAPHICS={texture_scaling=1}},STATES={},UIT={},TIMERS={},CONTROLLER={held_keys={},locks={}}}
love={event={quit=noop},update=noop,timer={getTime=function() return 0 end},
keyboard={isDown=function() return false end},mouse={},system={},filesystem={}}
function love.filesystem.getSaveDirectory() return '/save' end
function love.filesystem.getInfo(path)
 if packed[path] then return {type='file'} end
 for n in pairs(packed) do if n:sub(1,#path+1)==path..'/' then return {type='directory'} end end
end
function love.filesystem.read(path) return packed[path] end
function love.filesystem.getDirectoryItems(path)
 local names={};local seen={}
 for n in pairs(packed) do
  if n:sub(1,#path+1)==path..'/' then
   local part=n:sub(#path+2):match('[^/]+')
   if part and not seen[part] then names[#names+1]=part;seen[part]=true end
  end
 end
 table.sort(names);return names
end
function love.filesystem.write() return true end
function love.filesystem.createDirectory() return true end
function love.filesystem.newFileData() end
Handy_main_file_path='Mods/Handy'
package.preload['browser.nativefs']=assert(loadstring(packed['browser/nativefs.lua']))
package.preload['handy/nativefs']=function() return require('browser.nativefs') end
package.preload['handy/json']=assert(loadstring(packed['handy/json.lua']))
package.preload['browser.handy']=assert(loadstring(packed['browser/handy.lua']))
''')
lua.execute(fs['Mods/Handy/index.lua'])
print('Handy full bootstrap passed',lua.eval('Handy.version'))

lua.execute("""
local opts=create_UIBox_options()
local buttons=opts.nodes[1].nodes[1].nodes[1].nodes
assert(#buttons==1 and buttons[1].config.button=='handy_options')
assert(Handy.cc.dangerous_actions_sell_all_same.enabled)
assert(Handy.cc.dangerous_actions_sell_all_same.keys_1[1]=='Shift')
assert(Handy.cc.dangerous_actions_sell_all_same.keys_1[2]=='Right Mouse')
assert(Handy.cc.dangerous_actions_sell_all.keys_1[1]=='Ctrl')
assert(not Handy.cc.dangerous_actions_remove_all.enabled)
Handy.speed_multiplier.value=1024
assert(Handy.speed_multiplier.get_limited_value()==512)
Handy.animation_skip.value=5
assert(Handy.animation_skip.get_limited_value()==4)
""")
print('Handy Options entry, default sale bindings and speed/animation caps passed')
