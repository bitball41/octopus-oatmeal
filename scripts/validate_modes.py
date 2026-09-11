#!/usr/bin/env python3
"""Vanilla / Paperback / Bunco / Pokermon / multiplayer archive split, Red Deck copy, and simplified lobby."""
import io
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSDELIVR_LIMIT = 20 * 1024 * 1024


def archive(path):
    z = zipfile.ZipFile(path)
    return z, set(z.namelist())


def concat_parts(dir_path):
    parts_file = dir_path / 'parts.json'
    assert parts_file.is_file(), f'{parts_file} missing'
    parts = json.loads(parts_file.read_text())
    assert parts, f'{parts_file} is empty'
    chunks = []
    for name in parts:
        path = dir_path / name
        assert path.is_file(), f'{path} missing'
        size = path.stat().st_size
        assert size <= JSDELIVR_LIMIT, f'{path} is {size} bytes; jsDelivr 403s files over 20 MB'
        assert size > 0, f'{path} is empty'
        chunks.append(path.read_bytes())
    blob = b''.join(chunks)
    packed = zipfile.ZipFile(io.BytesIO(blob))
    return packed, set(packed.namelist()), blob, parts


def compile_packed_lua(packed, names, label, compile_lua):
    for name in sorted(names):
        if name.endswith('.lua'):
            ok, err = compile_lua(packed.read(name).decode(), '@' + name)
            assert ok, f'{label} {name}: {err}'


def assert_smods_content_pack(packed, names, folder, main_lua, meta_json, label):
    assert any(n.startswith('Mods/Steamodded/') for n in names)
    assert any(n.startswith(f'Mods/{folder}/') for n in names)
    assert not any(n.startswith('Mods/Multiplayer/') for n in names)
    assert f'Mods/{folder}/{main_lua}' in names
    assert f'Mods/{folder}/{meta_json}' in names
    assert 'browser/platform.lua' in names
    assert 'browser/nativefs.lua' in names
    assert 'browser/menu.lua' not in names
    main = packed.read('main.lua').decode()
    assert 'require "browser.platform"' in main
    assert 'require("browser.cheats").keypressed(key)' in main
    assert 'Mods/Multiplayer' not in main
    overrides = packed.read('Mods/Steamodded/src/overrides.lua').decode()
    assert 'goto ' not in overrides
    return packed, names


def main():
    vanilla_path = ROOT / 'vanilla' / 'game.data'
    paperback_path = ROOT / 'paperback' / 'game.data'
    bunco_path = ROOT / 'bunco' / 'game.data'
    pokermon_dir = ROOT / 'pokermon'
    multiplayer_path = ROOT / 'game.data'
    assert vanilla_path.is_file(), 'vanilla/game.data missing'
    assert paperback_path.is_file(), 'paperback/game.data missing'
    assert bunco_path.is_file(), 'bunco/game.data missing'
    assert multiplayer_path.is_file(), 'multiplayer game.data missing'
    assert not (pokermon_dir / 'game.data').exists(), 'do not ship unsplit pokermon/game.data'

    vanilla, vanilla_names = archive(vanilla_path)
    paperback, paperback_names = archive(paperback_path)
    bunco, bunco_names = archive(bunco_path)
    pokermon, pokermon_names, pokermon_blob, pokermon_parts = concat_parts(pokermon_dir)
    modded, modded_names = archive(multiplayer_path)

    # jsDelivr hard-caps a single file at 20 MB. Downloaded launchers fetch
    # these archives from that CDN unless locateFile sends game.data to GitHub raw.
    for label, packed in (
        ('vanilla', vanilla_path),
        ('paperback', paperback_path),
        ('bunco', bunco_path),
        ('multiplayer', multiplayer_path),
    ):
        size = packed.stat().st_size
        assert size <= JSDELIVR_LIMIT, f'{label} game.data is {size} bytes; jsDelivr 403s files over 20 MB'

    poke_js = (pokermon_dir / 'game.js').read_text()
    assert f'var SPLIT_PACKAGE_PARTS = {json.dumps(pokermon_parts)};' in poke_js
    assert 'var SPLIT_PACKAGE_PARTS = [];' not in poke_js
    html = (ROOT / 'index.html').read_text()
    for name in pokermon_parts:
        assert name in html, f'launcher missing Pokermon part {name}'
    assert len(pokermon_parts) >= 2, 'Pokermon should be split into at least 2 CDN parts'

    assert not any(n.startswith('Mods/Steamodded/') for n in vanilla_names)
    assert not any(n.startswith('Mods/Multiplayer/') for n in vanilla_names)
    assert not any(n.startswith('Mods/paperback/') for n in vanilla_names)
    assert not any(n.startswith('Mods/Bunco/') for n in vanilla_names)
    assert not any(n.startswith('Mods/Pokermon/') for n in vanilla_names)
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

    assert_smods_content_pack(
        paperback, paperback_names, 'paperback', 'paperback.lua', 'metadata.json', 'paperback')
    overrides = paperback.read('Mods/Steamodded/src/overrides.lua').decode()
    assert 'pb_is_illegal_seq' in overrides
    assert '::pb_continue_rank_next::' not in overrides
    assert 'repeat' in overrides and 'until true' in overrides
    pb_shader = paperback.read('Mods/Steamodded/src/game_object.lua').decode()
    assert 'pcall(love.graphics.newShader' in pb_shader
    assert not any('lsp_def' in n or n.endswith('.DS_Store') or n.endswith('.md') for n in paperback_names)

    assert_smods_content_pack(
        bunco, bunco_names, 'Bunco', 'Bunco.lua', 'Bunco.json', 'bunco')
    assert not any(n.startswith('Mods/paperback/') for n in bunco_names)
    assert not any(n.startswith('Mods/Pokermon/') for n in bunco_names)
    assert 'Mods/Bunco/lovely.toml' in bunco_names
    bunco_cfg = bunco.read('Mods/Bunco/config.lua').decode()
    assert 'high_quality_shaders = false' in bunco_cfg
    headache = bunco.read('Mods/Bunco/assets/shaders/headache.fs').decode()
    assert 'float(frame) * 71.0' in headache
    assert headache.count('for (int bunc_k = 0; bunc_k <= 4; bunc_k++)') == 3
    assert 'for (float i =' not in headache
    assert 'float steps = 0.25' not in headache
    assert 'uv.x * 2.0)' in headache
    assert 'uv.x * 2)' not in headache
    for shader_name in (
        'Mods/Bunco/assets/shaders/glitter.fs',
        'Mods/Bunco/assets/shaders/fluorescent.fs',
    ):
        extra = bunco.read(shader_name).decode()
        assert 'uv.x * 2.0)' in extra
        assert 'uv.x * 2)' not in extra
    assert re.search(r'(?<!float\()frame \* 71\.0', headache) is None
    bunco_shader = bunco.read('Mods/Steamodded/src/game_object.lua').decode()
    assert 'pcall(love.graphics.newShader' in bunco_shader
    assert 'self.full_path:find("Bunco", 1, true)' in bunco_shader

    try:
        from lupa.lua51 import LuaRuntime
    except ImportError:
        from lupa import LuaRuntime
    lua = LuaRuntime(unpack_returned_tuples=True)
    compile_lua = lua.eval('function(s, n) local f,e=loadstring(s,n); return f~=nil,e end')
    compile_packed_lua(paperback, paperback_names, 'paperback', compile_lua)
    compile_packed_lua(bunco, bunco_names, 'bunco', compile_lua)

    assert_smods_content_pack(
        pokermon, pokermon_names, 'Pokermon', 'pokermon.lua', 'Pokermon.json', 'pokermon')
    assert not any(n.startswith('Mods/paperback/') for n in pokermon_names)
    assert not any(n.startswith('Mods/Bunco/') for n in pokermon_names)
    assert not any(n.startswith('Mods/Multiplayer/') for n in pokermon_names)
    poke_meta = pokermon.read('Mods/Pokermon/Pokermon.json').decode()
    assert 'Steamodded (>=1.0.0~BETA-1620a)' in poke_meta
    assert 'BETA-1814a' not in poke_meta
    poke_cfg = pokermon.read('Mods/Pokermon/config.lua').decode()
    assert '["poke_enable_animations"]=false' in poke_cfg
    assert '["pokemon_splash"]=false' in poke_cfg
    poke_shader = pokermon.read('Mods/Steamodded/src/game_object.lua').decode()
    assert 'pcall(love.graphics.newShader' in poke_shader
    assert 'self.full_path:find("Pokermon", 1, true)' in poke_shader
    poke_utils = pokermon.read('Mods/Steamodded/src/utils.lua').decode()
    assert 'part.control.V and args.vars.colours and args.vars.colours[tonumber(part.control.V)]' in poke_utils
    assert not pokermon.read('Mods/Pokermon/localization/vi.lua').startswith(b'\xef\xbb\xbf')
    assert not any(n.startswith('Mods/Pokermon/assets/2x/') for n in pokermon_names)
    assert not any(n.startswith('Mods/Pokermon/') and 'Natdex' in n and n.endswith('.png') for n in pokermon_names)
    poke_sprites = pokermon.read('Mods/Pokermon/pokesprites.lua').decode()
    assert 'texture_scaling = 1' in poke_sprites
    assert '"Natdex"' not in poke_sprites
    assert poke_sprites.count("frames = 1,") >= 4
    compile_packed_lua(pokermon, pokermon_names, 'pokermon', compile_lua)

    assert any(n.startswith('Mods/Steamodded/') for n in modded_names)
    assert any(n.startswith('Mods/Multiplayer/') for n in modded_names)
    assert not any(n.startswith('Mods/paperback/') for n in modded_names)
    assert not any(n.startswith('Mods/Bunco/') for n in modded_names)
    assert not any(n.startswith('Mods/Pokermon/') for n in modded_names)
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

    print('Vanilla/Paperback/Bunco/Pokermon/multiplayer split, simplified lobby and Red Deck unlocked copy passed')


if __name__ == '__main__':
    main()
