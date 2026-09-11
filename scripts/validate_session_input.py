#!/usr/bin/env python3
"""Exercise the packed Lua 5.1 input callbacks and network dispatcher."""
import sys
import zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime

root = Path(__file__).resolve().parents[1]
z = zipfile.ZipFile(sys.argv[1] if len(sys.argv) > 1 else root / 'game.data')
required = {'browser/platform.lua', 'browser/menu.lua', 'browser/nativefs.lua',
            'Mods/Multiplayer/core.lua', 'Mods/Multiplayer/networking/action_handlers.lua',
            'Mods/Steamodded/src/ui.lua', 'SMODS/preflight/core.lua', 'json.lua'}
assert required <= set(z.namelist()), required - set(z.namelist())
lua = LuaRuntime(unpack_returned_tuples=True)
compile_lua = lua.eval('function(s, n) local f,e=loadstring(s,n); return f~=nil,e end')
for name in z.namelist():
    if name.endswith('.lua'):
        ok, err = compile_lua(z.read(name).decode(), '@' + name)
        assert ok, err
print('All packed Lua modules compile under Lua 5.1; required modules present')

def function_block(source, anchor):
    begin = source.index(anchor)
    end = source.find('\nfunction ', begin + 1)
    return source[begin:end if end != -1 else len(source)]

lua.execute('''
love = {}; Controller = {}; G = {FUNCS={}, CONTROLLER={held_keys={},locks={}}, C={WHITE={1,1,1}}}
function copy_table(t) return t end
function ease_colour() end
function TRANSPOSE_TEXT_INPUT(n)
 local text=G.CONTROLLER.text_input_hook.config.ref_table.text
 text.current_position=math.max(0,math.min(#text.ref_table.value,text.current_position+n))
end
function MODIFY_TEXT_INPUT(a)
 local t=a.text_table; local s=t.ref_table.value
 if a.delete then t.ref_table.value=s:sub(1,a.pos-1)..s:sub(a.pos+1)
 else t.ref_table.value=s:sub(1,a.pos-1)..a.letter..s:sub(a.pos) end
end
function reset_input(all_caps)
 local c=G.CONTROLLER
 c.capslock=false;c.held_keys={};c.submitted=false
 c.text_input_hook={parent={parent={config={}}},config={ref_table={
  text={ref_table={value=''},ref_value='value',current_position=0},colour={1,1,1},
  extended_corpus=true,max_length=100,all_caps=all_caps,
  callback=function() c.submitted=true end}}}
end
''')
main = z.read('main.lua').decode()
controller = z.read('engine/controller.lua').decode()
buttons = z.read('functions/button_callbacks.lua').decode()
lua.execute(function_block(main, 'function love.textinput(text)'))
lua.execute(function_block(controller, 'function Controller:key_press_update(key, dt)'))
a = buttons.index('G.FUNCS.text_input_key = function(args)')
b = buttons.index('\n--Helper function for G.FUNCS.text_input_key', a)
lua.execute(buttons[a:b])
lua.execute('''
function press(key,text)
 Controller.key_press_update(G.CONTROLLER,key,0)
 if text then love.textinput(text) end
end
function value() return G.CONTROLLER.text_input_hook.config.ref_table.text.ref_table.value end
reset_input(false)
press('1','1'); assert(value()=='1', 'one physical 1 inserted twice')
press('a','A'); assert(value()=='1A', 'Shift text changed or duplicated')
press('a','a');press('a','a');assert(value()=='1Aaa','legitimate repeated characters lost')
press('space',' ');press('kp2','2');assert(value()=='1Aaa 2','space/keypad duplicated')
press('backspace');assert(value()=='1Aaa ','backspace not exactly once')
G.CONTROLLER.capslock=true
press('b','b');assert(value()=='1Aaa b','SDL CapsLock+Shift casing overridden')
press('enter');assert(G.CONTROLLER.submitted and not G.CONTROLLER.text_input_hook,'Enter failed')
reset_input(true)
press('a','a');press('b','b');press('b','b');assert(value()=='ABB','native all-caps/repeats failed')
''')
print('Packed input: single insertion, repeats, Shift, CapsLock, spaces, keypad, backspace, Enter, all-caps passed')

# Run the actual packed dispatcher, including its LuaJIT-origin logging, against
# real decoded protocol values. A log must not throw before invoking a handler.
lua.execute(z.read('json.lua').decode().replace('return json', 'package.loaded.json = json'))
lua.execute('''
local packets={
 '{"action":"lobbyInfo","isHost":false,"guestReady":true,"hostCached":true}',
 '{"action":"lobbyOptions","modifiers":{"timer":true}}',
 '{"action":"startGame","seed":"ABC123"}'
}
love.thread={getChannel=function() return {pop=function() return table.remove(packets,1) end} end}
Game={update=function() end}; received={}
function sendTraceMessage() end
function sendWarnMessage(message) error(message) end
''')
network = z.read('Mods/Multiplayer/networking/action_handlers.lua').decode()
a = network.index('local network_to_ui_channel =')
lua.execute('''
local json=require('json');local no_log_actions={};local last_game_seed
local HANDLERS=setmetatable({}, {__index=function(_,action)
 return function(p) received[action]=p end
end})
''' + network[a:])
lua.execute('''
Game:update(0)
assert(received.lobbyInfo.isHost==false and received.lobbyInfo.guestReady==true)
assert(received.lobbyOptions.modifiers.timer==true)
assert(received.startGame.seed=='ABC123')
''')
print('Packed dispatcher: boolean lobby/ready state, nested options and startGame reach handlers unchanged')
if len(sys.argv) == 1:
    assert (root/'game.data').read_bytes() == (root/'build/game.data').read_bytes()
    print('Production game.data matches build/game.data byte-for-byte')
