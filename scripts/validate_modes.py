#!/usr/bin/env python3
"""Vanilla / Paperback / multiplayer archive split, Red Deck copy, and simplified lobby."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def archive(path):
    z = zipfile.ZipFile(path)
    return z, set(z.namelist())


def main():
    vanilla_path = ROOT / 'vanilla' / 'game.data'
    paperback_path = ROOT / 'paperback' / 'game.data'
    multiplayer_path = ROOT / 'game.data'
    assert vanilla_path.is_file(), 'vanilla/game.data missing'
    assert paperback_path.is_file(), 'paperback/game.data missing'
    assert multiplayer_path.is_file(), 'multiplayer game.data missing'

    vanilla, vanilla_names = archive(vanilla_path)
    paperback, paperback_names = archive(paperback_path)
    modded, modded_names = archive(multiplayer_path)

    assert not any(n.startswith('Mods/Steamodded/') for n in vanilla_names)
    assert not any(n.startswith('Mods/Multiplayer/') for n in vanilla_names)
    assert not any(n.startswith('Mods/paperback/') for n in vanilla_names)
    assert 'browser/vanilla.lua' in vanilla_names
    assert 'browser/cheats.lua' in vanilla_names
    assert 'browser/clipboard.lua' in vanilla_names
    assert 'browser/joker_order.lua' in vanilla_names
    assert 'browser/menu.lua' not in vanilla_names
    assert 'browser/platform.lua' not in vanilla_names
    vanilla_main = vanilla.read('main.lua').decode()
    assert 'require "browser.vanilla"' in vanilla_main
    assert 'require("browser.cheats").keypressed(key)' in vanilla_main
    assert 'require("browser.clipboard").poll()' in vanilla_main
    assert 'require "browser.platform"' not in vanilla_main

    assert any(n.startswith('Mods/Steamodded/') for n in paperback_names)
    assert any(n.startswith('Mods/paperback/') for n in paperback_names)
    assert not any(n.startswith('Mods/Multiplayer/') for n in paperback_names)
    assert 'Mods/paperback/paperback.lua' in paperback_names
    assert 'Mods/paperback/metadata.json' in paperback_names
    assert 'browser/platform.lua' in paperback_names
    assert 'browser/nativefs.lua' in paperback_names
    assert 'browser/menu.lua' not in paperback_names
    paperback_main = paperback.read('main.lua').decode()
    assert 'require "browser.platform"' in paperback_main
    assert 'require("browser.cheats").keypressed(key)' in paperback_main
    assert 'Mods/Multiplayer' not in paperback_main
    overrides = paperback.read('Mods/Steamodded/src/overrides.lua').decode()
    assert 'pb_is_illegal_seq' in overrides
    assert 'goto ' not in overrides
    assert '::pb_continue_rank_next::' not in overrides
    assert 'repeat' in overrides and 'until true' in overrides

    try:
        from lupa.lua51 import LuaRuntime
    except ImportError:
        from lupa import LuaRuntime
    lua = LuaRuntime(unpack_returned_tuples=True)
    compile_lua = lua.eval('function(s, n) local f,e=loadstring(s,n); return f~=nil,e end')
    for name in sorted(paperback_names):
        if name.endswith('.lua'):
            ok, err = compile_lua(paperback.read(name).decode(), '@' + name)
            assert ok, f'paperback {name}: {err}'

    assert any(n.startswith('Mods/Steamodded/') for n in modded_names)
    assert any(n.startswith('Mods/Multiplayer/') for n in modded_names)
    assert not any(n.startswith('Mods/paperback/') for n in modded_names)
    assert 'browser/menu.lua' in modded_names
    assert 'browser/platform.lua' in modded_names
    menu = modded.read('browser/menu.lua').decode()
    assert "ruleset_mp_vanilla" in menu
    assert "gamemode_mp_attrition" in menu
    assert 'function G.FUNCS.create_lobby' in menu

    back = modded.read('back.lua').decode()
    locked = back.index('if not back_config.unlocked then')
    unlocked_else = back.index('\n    else', locked)
    assert 'demo_locked' in back[locked:unlocked_else], 'demo lock leaked out of the locked branch'
    assert "name_to_check == 'Red Deck'" in back[unlocked_else:], 'Red Deck description is not on the unlocked path'
    red = [line for line in modded.read('game.lua').decode().splitlines() if 'b_red=' in line.replace(' ', '')][0]
    assert 'demo = false' in red and 'unlocked = true' in red

    love = (ROOT / 'love.js').read_text()
    assert 'Module["persistenceDatabase"]' in love
    assert 'var persistenceMountpoint = "/home/web_user/love";' in love

    print('Vanilla/Paperback/multiplayer split, simplified lobby and Red Deck unlocked copy passed')


if __name__ == '__main__':
    main()
