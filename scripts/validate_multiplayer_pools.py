#!/usr/bin/env python3
"""Multiplayer pools must not depend on each player's profile progress.

Runs the packed get_current_pool against a fully unlocked profile and a
partly locked/undiscovered one. In a lobby both must build identical Joker
and Tag pools (so one shared seed gives both players the same run); outside
a lobby the profile still gates the pools as in vanilla.
"""
import io
import json
import sys
import zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


def archive_files(path=None):
    if path:
        data = Path(path).read_bytes()
    else:
        data = (ROOT / 'game.data').read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {n: z.read(n) for n in z.namelist()}


files = archive_files(sys.argv[1] if len(sys.argv) > 1 else None)
source = files['functions/common_events.lua'].decode()
helper_start = source.index('local function octopus_shared_pools()')
helper = source[helper_start:source.index('\nend', helper_start) + 4]
start = source.index('function get_current_pool(')
pool_fn = source[start:source.index('\nfunction ', start + 1)]

ENV = '''
function EMPTY(t) for k in pairs(t or {}) do t[k] = nil end return t or {} end
SMODS = {ObjectTypes = {}, Rarities = {}, showman = function() return false end,
    add_to_pool = function() return true end}
MP = {LOBBY = {}, should_exclude_from_pool = function() return false end}
local jokers, tags = {}, {}
for i = 1, 12 do jokers[i] = {key = 'j_test' .. i, set = 'Joker', rarity = 1} end
local tag_requires = {tag_negative = 'e_negative', tag_foil = 'e_foil', tag_buffoon = 'p_buffoon_mega_1'}
for _, key in ipairs({'tag_buffoon', 'tag_double', 'tag_foil', 'tag_juggle', 'tag_negative'}) do
    tags[#tags + 1] = {key = key, set = 'Tag', requires = tag_requires[key]}
end
G = {ARGS = {}, P_JOKER_RARITY_POOLS = {[1] = jokers}, P_CENTER_POOLS = {Tag = tags},
    P_CENTERS = {e_negative = {}, e_foil = {}, p_buffoon_mega_1 = {}},
    GAME = {used_jokers = {}, used_vouchers = {}, banned_keys = {}, pool_flags = {},
        round_resets = {ante = 1}, hands = {}}}
function set_profile(full)
    for i, j in ipairs(jokers) do j.unlocked = full or i % 3 ~= 0 end
    for _, c in pairs(G.P_CENTERS) do c.discovered = full end
end
function pool(kind)
    local p = kind == 'Joker' and get_current_pool('Joker', 'Common') or get_current_pool('Tag')
    return table.concat(p, ',')
end
'''

lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute(ENV)
lua.execute(helper + '\n' + pool_fn)
run = lua.eval('''function(full, lobby, kind)
    MP.LOBBY.code = lobby and 'ROOM' or nil
    set_profile(full)
    return pool(kind)
end''')
for kind in ('Joker', 'Tag'):
    full, partial = run(True, True, kind), run(False, True, kind)
    assert full == partial, (kind, full, partial)
    assert 'UNAVAILABLE' not in full and full.count(',') >= 4, full
    assert run(False, False, kind) != run(True, False, kind), kind + ' pools stopped honouring the profile outside multiplayer'
print('Multiplayer pools: locked/undiscovered and fully unlocked profiles build identical Joker and Tag pools in a lobby; single-player still uses the profile')

# Certificate's guaranteed seal must not consume a shared 'stdseal' roll.
utils = files['Mods/Steamodded/src/utils.lua'].decode()
assert "local seal_poll = guaranteed and 1 or pseudorandom(pseudoseed(key or 'stdseal'" in utils, \
    'The Order seal poll patch was skipped'
print("Multiplayer seals: guaranteed seals leave the shared 'stdseal' stream untouched")
