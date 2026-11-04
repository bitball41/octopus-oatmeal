#!/usr/bin/env python3
"""Mod builds: pixel smoothing defaults Off but can be turned On; High Contrast works;
mod unlocks, discoveries and the profile (Unlock All, wins, stats) survive a reload.

Runs browser/lua/browser/mod_settings.lua against small Game/G/SMODS stubs, then
checks every published Steamodded archive loads it and Vanilla builds do not.
"""
import io
import json
import sys
import zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'browser/lua/browser/mod_settings.lua').read_text()
REQUIRE = 'require "browser.mod_settings"'

STUBS = r'''
calls = {}
Game = {}
function Game:set_render_settings() calls.render = self.SETTINGS.GRAPHICS.texture_scaling end
function Game:start_up() self:set_render_settings() end
function Game:save_settings() calls.saved = (calls.saved or 0) + 1 end
-- The browser base's save_progress: rewrites meta from the current prototypes.
function Game:save_progress()
    local meta = G.FILES[G.SETTINGS.profile .. '/meta.jkr'] or {}
    G.FILES[G.SETTINGS.profile .. '/meta.jkr'] = meta
    meta.unlocked = meta.unlocked or {}; meta.discovered = meta.discovered or {}; meta.alerted = meta.alerted or {}
    for _, pool in ipairs({self.P_CENTERS, self.P_BLINDS, self.P_TAGS}) do
        for k, v in pairs(pool) do
            meta.unlocked[k], meta.discovered[k], meta.alerted[k] = v.unlocked or nil, v.discovered or nil, v.alerted or nil
        end
    end
    calls.progress = meta
end
G = setmetatable({}, {__index = Game})
G.SETTINGS = {GRAPHICS = {texture_scaling = 2}}
G.C = {SO_1 = {Hearts = 'h1', Spades = 's1', bunc_Fleurons = 'f1'}, SO_2 = {Hearts = 'h2', Spades = 's2', bunc_Fleurons = 'f2'}, SUITS = {}}
G.I = {CARD = {}}
G.FUNCS = {}
function G.FUNCS.refresh_contrast_mode()
    calls.original = (calls.original or 0) + 1
    G.C.SUITS.Hearts = G.C['SO_' .. (G.SETTINGS.colourblind_option and 2 or 1)].Hearts
end
function G.FUNCS.update_suit_colours(suit)
    local p = G.SETTINGS.colour_palettes[suit]
    G.C.SUITS[suit] = G.C['SO_' .. (p == 'hc' and 2 or 1)][suit]
end
local function image() local i = {filter = 'unset'}; function i:setFilter(a) self.filter = a end; return i end
G.ASSET_ATLAS = {Joker = {image = image()}, cry_atlas = {image = image()}, pixel_only = {image = image(), force_pixel = true}}
G.ANIMATION_ATLAS = {blind_chips = {image = image()}}
function G.FUNCS.change_pixel_smoothing(args)
    G.SETTINGS.GRAPHICS.texture_scaling = args.to_key
    G.ASSET_ATLAS.late_mod = {image = image()}  -- re-injected after set_render_settings
end
love = {filesystem = {}}
function love.filesystem.getInfo(path) return config_json and path == 'browser/build_config.json' and {type = 'file'} or nil end
function love.filesystem.read() return config_json end
package.preload.json = function() return {decode = function(s) return loadstring('return ' .. s)() end} end
'''


def runtime(settings=None, config=None, smods=True):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(STUBS)
    if config is not None:
        lua.globals().config_json = config
    if settings:
        lua.execute(settings)
    if smods:
        lua.execute("""
            SMODS = {Suits = {Hearts = {}, Spades = {}, bunc_Fleurons = {}}, DeckSkins = {
                default = {palette_map = {lc = {}, hc = {}}}, art_only = {palette_map = {art = {}}}}}
            G.SETTINGS.colour_palettes = G.SETTINGS.colour_palettes or {Hearts = 'lc', Spades = 'lc', bunc_Fleurons = 'lc'}
            G.SETTINGS.CUSTOM_DECK = {Collabs = {Hearts = 'default', Spades = 'art_only', bunc_Fleurons = 'default'}}
            card_front = {config = {card = {}}, children = {front = {}}, ability = {effect = 'Base'}}
            function card_front:set_sprites() calls.sprites = (calls.sprites or 0) + 1 end
            G.I.CARD[1] = card_front
        """)
    lua.execute(SOURCE)
    return lua


def check_pixel_smoothing():
    # Fresh mod save: Off.
    lua = runtime()
    lua.execute('G:start_up()')
    assert lua.eval('calls.render') == 1, 'fresh mod save should start with smoothing Off'
    assert lua.eval('G.SETTINGS.octopus_mod_pixel_default') is True

    # Older mod saves still holding the previous default are moved to Off once.
    lua = runtime('G.SETTINGS = {GRAPHICS = {texture_scaling = 2}}')
    lua.execute('G:start_up()')
    assert lua.eval('calls.render') == 1

    # A player who turned it On afterwards keeps it On (and it can be toggled again).
    lua = runtime('G.SETTINGS = {octopus_mod_pixel_default = true, GRAPHICS = {texture_scaling = 2}}')
    lua.execute('G:start_up()')
    assert lua.eval('calls.render') == 2, 'saved On choice must be respected'
    lua.execute('G.SETTINGS.GRAPHICS.texture_scaling = 1; G:set_render_settings()')
    assert lua.eval('calls.render') == 1
    lua.execute('G.SETTINGS.GRAPHICS.texture_scaling = 2; G:set_render_settings()')
    assert lua.eval('calls.render') == 2

    # Custom build on the Vanilla save keeps Vanilla's smoothing.
    lua = runtime(config='{vanilla_save = true}')
    lua.execute('G:start_up()')
    assert lua.eval('calls.render') == 2, 'Vanilla save keeps its own smoothing setting'
    lua = runtime(config='{vanilla_save = false}')
    lua.execute('G:start_up()')
    assert lua.eval('calls.render') == 1


def check_texture_filters():
    lua = runtime()
    lua.execute('G:start_up()')
    filters = lambda: {k: lua.eval(f'G.{t}.{k}.image.filter') for t, k in [('ASSET_ATLAS', 'Joker'), ('ASSET_ATLAS', 'cry_atlas'), ('ANIMATION_ATLAS', 'blind_chips')]}
    assert set(filters().values()) == {'nearest'}, filters()
    lua.execute('G.FUNCS.change_pixel_smoothing({to_key = 2})')
    assert set(filters().values()) == {'linear'}, 'every loaded texture must follow the toggle'
    assert lua.eval('G.ASSET_ATLAS.late_mod.image.filter') == 'linear', 'atlases injected by the toggle are covered'
    assert lua.eval('G.ASSET_ATLAS.pixel_only.image.filter') == 'unset', 'force_pixel atlases stay as their mod made them'
    lua.execute('G.FUNCS.change_pixel_smoothing({to_key = 1})')
    assert set(filters().values()) == {'nearest'}


def check_high_contrast():
    lua = runtime()
    lua.execute('G:start_up()')
    lua.execute('G.SETTINGS.colourblind_option = true; G.FUNCS.refresh_contrast_mode()')
    palettes = lua.eval('G.SETTINGS.colour_palettes')
    assert palettes['Hearts'] == 'hc', 'High Contrast must switch plain palettes'
    assert palettes['bunc_Fleurons'] == 'hc', 'mod suits follow the toggle'
    assert palettes['Spades'] == 'lc', 'a deck skin without an hc palette is left alone'
    assert lua.eval('G.C.SUITS.Hearts') == 'h2' and lua.eval('G.C.SUITS.bunc_Fleurons') == 'f2'
    assert lua.eval('calls.original') == 1 and lua.eval('calls.sprites') >= 1 and lua.eval('calls.saved') >= 1
    lua.execute('G.SETTINGS.colourblind_option = false; G.FUNCS.refresh_contrast_mode()')
    assert lua.eval('G.SETTINGS.colour_palettes.Hearts') == 'lc' and lua.eval('G.C.SUITS.Hearts') == 'h1'

    # Custom palette choices from Customize Deck are kept.
    lua = runtime()
    lua.execute("G:start_up(); G.SETTINGS.colour_palettes.Hearts = 'art'")
    lua.execute('G.SETTINGS.colourblind_option = true; G.FUNCS.refresh_contrast_mode()')
    assert lua.eval('G.SETTINGS.colour_palettes.Hearts') == 'art'

    # Saves where High Contrast was already On (while it did nothing) are fixed at boot.
    lua = runtime('G.SETTINGS = {colourblind_option = true, GRAPHICS = {}}')
    lua.execute('G:start_up()')
    assert lua.eval('G.SETTINGS.colour_palettes.Hearts') == 'hc'

    # Without Steamodded palettes the toggle behaves exactly as before.
    lua = runtime(smods=False)
    lua.execute('G:start_up(); G.SETTINGS.colourblind_option = true; G.FUNCS.refresh_contrast_mode()')
    assert lua.eval('calls.original') == 1 and lua.eval('calls.saved') is None


def check_unlocks_survive_reload():
    # Steamodded boot: save_progress runs while mod items are still locked,
    # before SAVE_UNLOCKS restores them from meta.jkr. Their entries must stay.
    lua = runtime("""
        G.SETTINGS.profile = 1
        G.PROFILES = {{}}
        G.FILES = {['1/meta.jkr'] = {unlocked = {j_joker = true, j_mod_a = true}, discovered = {j_joker = true, j_mod_a = true}, alerted = {j_mod_a = true}}}
        G.P_CENTERS = {j_joker = {unlocked = true, discovered = true, alerted = true}, j_mod_a = {unlocked = false, discovered = false}, j_mod_b = {unlocked = false, discovered = false}, c_demo = {demo = true}}
        G.P_BLINDS = {bl_mod = {discovered = false}}
        G.P_TAGS = {}
    """)
    lua.execute('G:save_progress()')
    meta = lambda flag, key: lua.eval(f"calls.progress.{flag}.{key}")
    assert meta('unlocked', 'j_mod_a') and meta('discovered', 'j_mod_a') and meta('alerted', 'j_mod_a'), 'mod unlocks were dropped on save'
    assert meta('unlocked', 'j_joker') and not meta('unlocked', 'j_mod_b'), 'save_progress must not invent unlocks'
    # Newly unlocked items are still recorded.
    lua.execute('G.P_CENTERS.j_mod_b.unlocked = true; G:save_progress()')
    assert meta('unlocked', 'j_mod_b')
    # A deleted profile (meta cleared) does not come back.
    lua.execute("G.FILES['1/meta.jkr'] = nil; G.P_CENTERS = {}; G:save_progress()")
    assert not meta('unlocked', 'j_mod_a')

    # Unlock All profiles whose mod unlocks were already lost get every loaded item back.
    lua = runtime("""
        G.SETTINGS.profile = 2
        G.PROFILES = {{}, {all_unlocked = true}}
        G.FILES = {['2/meta.jkr'] = {unlocked = {j_joker = true}, discovered = {j_joker = true}, alerted = {j_joker = true}}}
        G.P_CENTERS = {j_joker = {unlocked = true, discovered = true, alerted = true}, j_mod_a = {unlocked = false}, c_wip = {wip = true}}
        G.P_BLINDS = {bl_mod = {}}
        G.P_TAGS = {tag_mod = {}}
    """)
    lua.execute('G:save_progress()')
    for flag in ('unlocked', 'discovered', 'alerted'):
        for key in ('j_mod_a', 'bl_mod', 'tag_mod'):
            assert meta(flag, key), f'Unlock All profile lost {flag} {key}'
    assert not meta('unlocked', 'c_wip'), 'wip items stay locked, as with the Unlock All button'


def check_profile_survives_boot():
    # Browser start_up order: init_item_prototypes (save_progress) runs before
    # load_profile. The saved profile must be loaded, not overwritten by {}.
    boot = """
        G.SETTINGS.profile = 1
        G.SETTINGS.profile_counters = {}
        G.PROFILES = {{}, {}, {}}
        G.FILES = {['1/profile.jkr'] = {all_unlocked = true, career_stats = {c_wins = 4}}, ['1/meta.jkr'] = {}}
        G.P_CENTERS, G.P_BLINDS, G.P_TAGS = {j_mod_a = {unlocked = false}}, {}, {}
        function Game:load_profile(p)
            calls.loads = (calls.loads or 0) + 1
            G.PROFILES[p] = {}
            for k, v in pairs(G.FILES[p .. '/profile.jkr'] or {}) do G.PROFILES[p][k] = v end
        end
    """
    lua = runtime(boot)
    lua.execute('G:save_progress(); G.FILES["1/profile.jkr"] = G.PROFILES[1]; G:load_profile(1)')
    assert lua.eval('G.PROFILES[1].all_unlocked') is True, 'boot save_progress wiped the saved profile'
    assert lua.eval('G.PROFILES[1].career_stats.c_wins') == 4
    assert lua.eval('calls.progress.unlocked.j_mod_a'), 'restored Unlock All profile re-unlocks mod content'
    lua.execute('G:save_progress(); G:save_settings()')
    assert lua.eval('calls.loads') == 2, 'the profile is loaded once before the first save, then left alone'

    # Builds that load the profile before prototypes (Cryptid, Entropy) are not reloaded.
    lua = runtime(boot)
    lua.execute('G:load_profile(1); G.PROFILES[1].fresh = true; G:save_settings(); G:save_progress()')
    assert lua.eval('calls.loads') == 1 and lua.eval('G.PROFILES[1].fresh') is True


def release_files(folder):
    directory = ROOT / folder if folder else ROOT
    parts_file = directory / 'parts.json'
    parts = json.loads(parts_file.read_text()) if parts_file.exists() else ['game.data']
    return zipfile.ZipFile(io.BytesIO(b''.join((directory / p).read_bytes() for p in parts)))


def compiled_source():
    # Cryptid-flavour builds compile mixed numeric comparisons in every Lua file.
    sys.path.insert(0, str(ROOT / 'scripts'))
    from cryptid_browser import compile_comparisons
    files = {'browser/mod_settings.lua': SOURCE.encode(), 'main.lua': b''}
    compile_comparisons(files)
    return files['browser/mod_settings.lua'].decode()


def check_releases():
    for folder in ['paperback', 'bunco', 'pokermon', 'cryptid', 'entropy', 'fish-and-chips', '']:
        z = release_files(folder)
        packed = z.read('browser/mod_settings.lua').decode()
        assert packed in (SOURCE, compiled_source()), f'{folder or "multiplayer"}: stale mod_settings.lua'
        assert z.read('main.lua').decode().rstrip().endswith(REQUIRE), f'{folder or "multiplayer"}: mod_settings not loaded last'
        assert "love.graphics.setShader( G.SHADERS['CRT'])" in z.read('game.lua').decode(), f'{folder or "multiplayer"}: CRT colour pass missing'
    for folder in ['vanilla', 'vanilla-handy']:
        z = release_files(folder)
        assert 'browser/mod_settings.lua' not in z.namelist(), folder + ' must keep Vanilla settings behaviour'
        assert REQUIRE not in z.read('main.lua').decode()


check_pixel_smoothing()
check_texture_filters()
check_high_contrast()
check_unlocks_survive_reload()
check_profile_survives_boot()
if '--no-releases' not in sys.argv:
    check_releases()
print('Mod settings: smoothing defaults Off and stays toggleable, Vanilla save keeps its choice, High Contrast follows the toggle, mod unlocks and the profile survive a reload; all mod releases load it and keep the CRT colour pass')
