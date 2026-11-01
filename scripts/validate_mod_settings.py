#!/usr/bin/env python3
"""Mod builds: pixel smoothing defaults Off but can be turned On; High Contrast works.

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


def release_files(folder):
    directory = ROOT / folder if folder else ROOT
    parts_file = directory / 'parts.json'
    parts = json.loads(parts_file.read_text()) if parts_file.exists() else ['game.data']
    return zipfile.ZipFile(io.BytesIO(b''.join((directory / p).read_bytes() for p in parts)))


def check_releases():
    for folder in ['paperback', 'bunco', 'pokermon', 'cryptid', 'entropy', 'fish-and-chips', '']:
        z = release_files(folder)
        assert z.read('browser/mod_settings.lua').decode() == SOURCE, f'{folder or "multiplayer"}: stale mod_settings.lua'
        assert z.read('main.lua').decode().rstrip().endswith(REQUIRE), f'{folder or "multiplayer"}: mod_settings not loaded last'
    for folder in ['vanilla', 'vanilla-handy']:
        z = release_files(folder)
        assert 'browser/mod_settings.lua' not in z.namelist(), folder + ' must keep Vanilla settings behaviour'
        assert REQUIRE not in z.read('main.lua').decode()


check_pixel_smoothing()
check_high_contrast()
if '--no-releases' not in sys.argv:
    check_releases()
print('Mod settings: smoothing defaults Off and stays toggleable, Vanilla save keeps its choice, High Contrast follows the toggle; all mod releases load it')
