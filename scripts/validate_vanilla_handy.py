#!/usr/bin/env python3
"""Verify standalone Handy retains Vanilla's save schema in both directions."""
import zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
vanilla = zipfile.ZipFile(ROOT/'vanilla/game.data')
handy = zipfile.ZipFile(ROOT/'vanilla-handy/game.data')
names = set(handy.namelist())
assert 'Mods/Handy/index.lua' in names
assert not any(n.startswith(('Mods/Cryptid/', 'Mods/Steamodded/', 'SMODS/', 'Mods/Amulet/')) for n in names)
assert (ROOT/'vanilla-handy/game.data').stat().st_size < 20*1024*1024
lua = LuaRuntime(unpack_returned_tuples=True)
compile_lua = lua.eval('function(s,n) local f,e=loadstring(s,n);return f~=nil,e end')
for name in names:
    if name.endswith('.lua'):
        ok, error = compile_lua(handy.read(name).decode(), '@'+name)
        assert ok, (name, error)


def function(source, anchor):
    start = source.index(anchor)
    end = source.find('\nfunction ', start+1)
    return source[start:end if end >= 0 else len(source)].strip()


assert vanilla.read('conf.lua') == handy.read('conf.lua')
assert vanilla.read('engine/string_packer.lua') == handy.read('engine/string_packer.lua')
for path, anchors in {
    'card.lua': ['function Card:save(', 'function Card:load('],
    'cardarea.lua': ['function CardArea:save(', 'function CardArea:load('],
    'game.lua': ['function Game:load_profile(', 'function Game:save_progress(', 'function Game:save_settings('],
    'functions/misc_functions.lua': ['function save_run('],
}.items():
    for anchor in anchors:
        assert function(vanilla.read(path).decode(), anchor) == function(handy.read(path).decode(), anchor), anchor


def runtime(archive):
    runtime = LuaRuntime()
    runtime.execute('love={filesystem={},system={}};Object={}')
    runtime.execute(archive.read('engine/string_packer.lua').decode())
    return runtime


plain, enhanced = runtime(vanilla), runtime(handy)
saved = plain.execute('''return STR_PACK({VERSION='1.0.1o',GAME={seeded=true,
    pseudorandom={seed='TEST1234'},dollars=143255,round=12,round_resets={ante=4}},
    cardAreas={jokers={cards={{save_fields={center='j_baron'},ability={set='Joker'}}}}},
    profile={unlocked={j_baron=true},stake=3},settings={profile=2}})''')
enhanced.globals().incoming = saved
roundtrip = enhanced.execute('''local run=STR_UNPACK(incoming)
    assert(run.GAME.dollars==143255 and run.GAME.pseudorandom.seed=='TEST1234')
    assert(run.cardAreas.jokers.cards[1].save_fields.center=='j_baron')
    assert(run.profile.unlocked.j_baron and run.settings.profile==2)
    run.GAME.dollars=run.GAME.dollars+25
    return STR_PACK(run)''')
plain.globals().incoming = roundtrip
plain.execute('''local run=STR_UNPACK(incoming)
    assert(run.GAME.dollars==143280 and run.GAME.round_resets.ante==4)
    assert(run.cardAreas.jokers.cards[1].ability.set=='Joker' and run.profile.stake==3)''')
print('Standalone Handy: Lua 5.1 compile, unchanged save/load functions, and Vanilla → Handy → Vanilla save round-trip passed')
