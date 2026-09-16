#!/usr/bin/env python3
"""Regression coverage through the shipped Lua update and input entry points."""
import json
import re
import zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime
ROOT = Path(__file__).resolve().parents[1]
z = zipfile.ZipFile(ROOT/'game.data')
lua = LuaRuntime(unpack_returned_tuples=True)
for module, path in [('json','json.lua'), ('browser.joker_order','browser/joker_order.lua')]:
    lua.globals().package.loaded[module] = lua.execute(z.read(path).decode())
lua.execute('''
files={}; love={filesystem={
 getInfo=function(n) return files[n] and {} end,
 read=function(n) return files[n] end,
 remove=function(n) files[n]=nil end,
 getDirectoryItems=function() local t={} for n in pairs(files) do t[#t+1]=n end return t end,
 getSaveDirectory=function() return '/save' end
},thread={getChannel=function() error('unexpected channel') end},
 timer={getTime=function() return 1 end},keyboard={isDown=function() return false end}}
package.loaded['browser.format']={install=function() end}
package.loaded['browser.nativefs']={}
''')
lua.globals().package.loaded['browser.clipboard'] = lua.execute(z.read('browser/clipboard.lua').decode())
lua.globals().package.loaded['browser.platform'] = lua.execute(z.read('browser/platform.lua').decode())
lua.execute('''
Card={};SMODS={};Game={update=function() end}
G={FUNCS={},CONTROLLER={},SETTINGS={paused=false},STAGES={RUN=1},STAGE=1,
 GAME={},P_CENTERS={},jokers={cards={},config={card_limit=5}}}
MP={ACTIONS={},LOBBY={username='Test',blind_col=1},UI={update_connection_status=function() end}}
function sendTraceMessage() end
function sendWarnMessage(e) error(e) end
''')
cheat_src = z.read('browser/cheats.lua').decode()
lua.globals().package.loaded['browser.cheats'] = lua.execute(cheat_src)
lua.execute(z.read('Mods/Multiplayer/networking/action_handlers.lua').decode())
lua.execute('''
G.update=function(self,dt) Game.update(self,dt) end
started=true;lastTime=0
function timer_checkpoint() end
files['octopus_upstream_000000000000.json']='{"action":"connected"}'
''')
main = z.read('main.lua').decode()
assert 'require("browser.cheats").poll()' in main, 'global cheat poll hook missing from packed main.lua'
a=main.index('function love.update( dt )'); b=main.index('\nfunction ',a+1)
lua.execute(main[a:b]); lua.globals().love.update(0)
lua.execute('''assert(MP.LOBBY.connected==true,'love.update failed to deliver connected through the actual inbox and dispatcher')
assert(next(files)==nil, 'inbox file was not consumed')''')
print('Real love.update -> filesystem inbox -> real upstream connected handler passed')
# Execute the exact ordered grant with card-area doubles; ensure repeat typing
# cannot duplicate the grant and partial inventories are preserved.
lua.execute('''
for _,k in ipairs(require('browser.joker_order')) do G.P_CENTERS[k]={key=k} end
function create_card(_,area,a,b,c,d,key)
 return {config={center=G.P_CENTERS[key]},add_to_deck=function(self) self.added=true end}
end
function G.jokers:emplace(card) self.cards[#self.cards+1]=card end
function G.jokers:align_cards() end
G.E_MANAGER={add_event=function(_,e) e.func() end}
function Event(e) return e end
local card=create_card('Joker',G.jokers,nil,nil,nil,nil,'j_blueprint')
card.keep_me=true;G.jokers:emplace(card)
''')
cheats = lua.globals().package.loaded['browser.cheats']; lua.globals().cheats=cheats
lua.execute('''
G.CONTROLLER.text_input_hook={}
for c in ('liminal'):gmatch('.') do cheats.keypressed(c) end
assert(#G.jokers.cards==1,'cheat fired while editing text')
G.CONTROLLER.text_input_hook=nil
for c in ('liminal'):gmatch('.') do cheats.keypressed(c) end
assert(#G.jokers.cards==148 and G.jokers.config.card_limit>=148)
for i,k in ipairs(require('browser.joker_order')) do assert(G.jokers.cards[i].config.center.key==k) end
assert(G.jokers.cards[2].keep_me, 'existing Blueprint was replaced')
for c in ('liminal'):gmatch('.') do cheats.keypressed(c) end
assert(#G.jokers.cards==148,'repeated cheat duplicated cards')
''')
print('Liminal: exact 148-key order, existing card preserved, capacity, text-field suppression and repeat guard passed')

# Lotion is a queued global code: entering it outside a run must not mutate the
# current menu state, and the packed source must contain the exact god-run spec.
lua.execute('''
G.STAGE=0
for c in ('lotion'):gmatch('.') do cheats.keypressed(c) end
assert(#G.jokers.cards==148, 'lotion mutated inventory outside a run')
G.STAGE=1
assert(cheats.poll()==false, 'lotion applied before its full run objects existed')
''')
joker_block = re.search(r"local LOTION_JOKERS = \{(.*?)\n\}", cheat_src, re.S)
voucher_block = re.search(r"local LOTION_VOUCHERS = \{(.*?)\n\}", cheat_src, re.S)
assert joker_block and voucher_block
joker_keys = re.findall(r"'(j_[^']+)'", joker_block.group(1))
voucher_keys = re.findall(r"'(v_[^']+)'", voucher_block.group(1))
assert joker_keys == [
    'j_baron',
    'j_brainstorm', 'j_brainstorm', 'j_brainstorm', 'j_brainstorm',
    'j_blueprint', 'j_blueprint', 'j_blueprint', 'j_blueprint',
    'j_mime',
]
assert voucher_keys == [
    'v_paint_brush', 'v_palette',
    'v_grabber', 'v_nacho_tong',
    'v_directors_cut', 'v_retcon',
    'v_overstock_norm', 'v_overstock_plus',
    'v_clearance_sale', 'v_liquidation',
]
for required in [
    "buffer:sub(-6) == 'lotion'",
    "G.P_CENTERS.b_plasma",
    "while #G.playing_cards > 52 do",
    "while #G.playing_cards < 52 do",
    "G.P_CARDS.H_K",
    "G.P_CARDS.H_A",
    "G.P_CENTERS.m_steel",
    "G.P_CENTERS.m_glass",
    "card:set_seal('Red'",
    "polychrome = true",
    "for i = 1, 60 do",
    "'c_cryptid'",
    "hand.level = 101",
    "hand.chips = 1005",
    "hand.mult = 101",
    "G.GAME.dollars = 300",
]:
    assert required in cheat_src, f'missing lotion preset fragment: {required}'
print('Lotion: global queue and exact Plasma/Joker/voucher/deck/High Card/$300/60-Cryptid preset passed')

# Real clipboard module: async completion, normalization, cancellation/stale UI.
lua.execute('''
local clipboard=require('browser.clipboard')
local field={children={{children={{}}}}}
local e={UIBox={get_UIE_by_ID=function() return field end}}
G.FUNCS.text_input_key=function(args) inputs[#inputs+1]=args.key end
inputs={};G.OVERLAY_MENU={}
clipboard.request(e)
files['octopus_clipboard.json']='{"id":1,"text":"  xeqh7cp9\\\\n  "}'
-- JSON above contains a literal escaped backslash sequence; use encoder.
files['octopus_clipboard.json']=require('json').encode({id=1,text='  xeqh7cp9  '})
clipboard.poll()
assert(table.concat(inputs,'',17,24)=='XEQH7CP9' and inputs[25]=='return')
inputs={};clipboard.request(e)
files['octopus_clipboard.json']=require('json').encode({id=2,text='',cancelled=true})
clipboard.poll();assert(#inputs==0,'cancel cleared existing seed')
clipboard.request(e);G.OVERLAY_MENU={}
files['octopus_clipboard.json']=require('json').encode({id=3,text='AAAA1111'})
clipboard.poll();assert(#inputs==0,'late clipboard changed a closed field')
''')
print('Clipboard: async seed entry, normalization, cancellation and stale overlay guard passed')
