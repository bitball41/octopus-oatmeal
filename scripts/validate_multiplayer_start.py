#!/usr/bin/env python3
"""Run the packed cleanup on a Cryptid overlay that has no tutorial character."""
import io,json,sys,zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime
from multiplayer_start import apply
ROOT=Path(__file__).resolve().parents[1]
if len(sys.argv)>1:
    archive=zipfile.ZipFile(sys.argv[1])
else:
    recipe=json.loads((ROOT/'custom/manifest.json').read_text())['builds']['Cryptid+Multiplayer']
    archive=zipfile.ZipFile(io.BytesIO(b''.join((ROOT/'custom'/p).read_bytes() for p in recipe['overlay']['parts'])))
files={n:archive.read(n) for n in archive.namelist()}
original=files['game.lua'].decode();apply(files)

def function(text,anchor):
    start=text.index(anchor);end=text.find('\nfunction ',start+1)
    return text[start:end if end>=0 else len(text)]

def runtime(source,with_character=False):
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
    function noop() end
    Game={};CardArea={};removed=0;character_removed=0
    G={in_delete_run=false,ROOM={},STAGE=1,STAGE_OBJECTS={[1]={}},GAME={won=true},I={},
      OVERLAY_TUTORIAL={remove=function() removed=removed+1 end},
      E_MANAGER={clear_queue=noop},CONTROLLER={mod_cursor_context_layer=noop}}
    function remove_all() end
    ''')
    if with_character:
        lua.execute('G.OVERLAY_TUTORIAL.Jimbo={remove=function() character_removed=character_removed+1 end}')
    lua.execute(function(source,'function Game:delete_run()'))
    return lua

if original!=files['game.lua'].decode():
    old=runtime(original)
    ok,error=old.execute('return pcall(Game.delete_run,G)')
    assert not ok and 'Jimbo' in error, error
for character in (False,True):
    lua=runtime(files['game.lua'].decode(),character)
    lua.execute('Game.delete_run(G);assert(removed==1 and G.OVERLAY_TUTORIAL==nil and G.in_delete_run==false and G.STATE==-1 and G.GAME.won==false)')
    assert lua.eval('character_removed')==int(character)
# Run the actual delayed notification callback after its UI has been removed.
text=files['functions/common_events.lua'].decode();a=text.index('            if not G.achievement_notification or not G.ROOM then return true end');b=text.index('\n          return true',a)
lua=LuaRuntime();lua.execute('G={};function notification_callback()\n'+text[a:b]+'\nreturn true end;assert(notification_callback())')
# Cryptid intro remains pending in a peer room and resumes in single-player.
intro=files['Mods/Cryptid/lib/gameset.lua'].decode()
a=intro.index('G.FUNCS.cry_intro_controller = function()');b=intro.index('\nend',a)+4
lua=LuaRuntime();lua.execute('G={FUNCS={}};MP={LOBBY={code="ROOM"}}')
lua.execute(intro[a:b]);lua.execute('G.FUNCS.cry_intro_controller()')
lua.execute('MP.LOBBY.code=nil;G.SETTINGS={profile=1,paused=true};G.PROFILES={[1]={}};G.FUNCS.cry_intro_controller();assert(G.PROFILES[1].cry_intro_progress and not G.PROFILES[1].cry_intro_complete)')
print('Multiplayer cleanup: Cryptid popup without Jimbo, normal tutorial character, and expired notification callback passed')
