#!/usr/bin/env python3
"""Vanilla vs modded archive split, Red Deck copy, and simplified lobby."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def archive(path):
    z = zipfile.ZipFile(path)
    return z, set(z.namelist())


def main():
    vanilla_path = ROOT / 'vanilla' / 'game.data'
    modded_path = ROOT / 'game.data'
    assert vanilla_path.is_file(), 'vanilla/game.data missing'
    assert modded_path.is_file(), 'modded game.data missing'

    vanilla, vanilla_names = archive(vanilla_path)
    modded, modded_names = archive(modded_path)

    assert not any(n.startswith('Mods/Steamodded/') for n in vanilla_names)
    assert not any(n.startswith('Mods/Multiplayer/') for n in vanilla_names)
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

    assert any(n.startswith('Mods/Steamodded/') for n in modded_names)
    assert any(n.startswith('Mods/Multiplayer/') for n in modded_names)
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

    print('Vanilla/modded split, simplified lobby and Red Deck unlocked copy passed')


if __name__ == '__main__':
    main()
