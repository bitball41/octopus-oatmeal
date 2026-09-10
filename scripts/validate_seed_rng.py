#!/usr/bin/env python3
"""Compare the packed browser generator and seeded helpers with actual LuaJIT."""
import random
import re
import zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime
from lupa.luajit21 import LuaRuntime as JitRuntime

ROOT = Path(__file__).resolve().parents[1]
z = zipfile.ZipFile(ROOT / 'game.data')
browser = LuaRuntime(unpack_returned_tuples=True)
desktop = JitRuntime(unpack_returned_tuples=True)
rng = browser.execute(z.read('browser/seed_rng.lua').decode())
assert z.read('browser/seed_rng.lua') == (ROOT / 'browser/seed_rng.lua').read_bytes()
browser.globals().math.random = rng.random
browser.globals().math.randomseed = rng.randomseed
seeds = [0, 1, -1, .123456789, .9999, 42, 1e300, float('inf'), float('-inf')]
seeds += [random.Random(i).random() for i in range(30)]
for seed in seeds:
    rng.randomseed(seed)
    desktop.eval('math.randomseed')(seed)
    for i in range(100):
        args = [(), (52,), (-20, 100)][i % 3]
        assert rng.random(*args) == desktop.eval('math.random')(*args), (seed, i)
print(f'{len(seeds)*100:,} RNG outputs, including integer ranges and nonfinite seeds, match LuaJIT exactly')

source = z.read('functions/misc_functions.lua').decode()
# Load the actual packed implementations and card definitions, not copies.
helpers = source[source.index('function pseudoshuffle('):source.index('function tprint(')]
game = z.read('game.lua').decode()
start = game.index('self.P_CARDS = self.P_CARDS or {')
end = game.index('\n    }', start) + len('\n    }')
cards = game[start:end].replace('self.P_CARDS = self.P_CARDS or', 'G.P_CARDS =', 1)
for runtime in (browser, desktop):
    runtime.execute('G = {GAME = {pseudorandom = {}}}')
    runtime.execute(helpers)
    runtime.execute(cards)
    runtime.execute('''
function deck(seed)
    G.GAME.pseudorandom = {seed=seed, hashed_seed=pseudohash(seed)}
    local result = {}
    for i = 1, 52 do
        local _, key = pseudorandom_element(G.P_CARDS, pseudoseed('erratic'))
        result[i] = key
    end
    return table.concat(result, ',')
end
function shuffle(seed)
    G.GAME.pseudorandom = {seed=seed, hashed_seed=pseudohash(seed)}
    local result = {}
    for i = 1, 52 do result[i] = {sort_id=i} end
    pseudoshuffle(result, pseudoseed('shuffle'))
    for i = 1, 52 do result[i] = result[i].sort_id end
    return table.concat(result, ',')
end
''')

for seed in ['XEQH7CP9', '7LB2WVPK', 'AAAA1111', 'TEST1234', 'DFRU5D52']:
    actual = browser.globals().deck(seed)
    assert actual == desktop.globals().deck(seed), ('deck mismatch', seed)
    if seed in ('XEQH7CP9', '7LB2WVPK'):
        assert actual.split(',') == ['S_T'] * 52, actual
    assert browser.globals().deck(seed) == actual, 'restart changed deck'
    assert browser.globals().shuffle(seed) == desktop.globals().shuffle(seed), ('shuffle mismatch', seed)
assert browser.globals().deck('AAAA1111') != browser.globals().deck('TEST1234')
assert browser.globals().shuffle('AAAA1111') != browser.globals().shuffle('TEST1234')
print('XEQH7CP9 and 7LB2WVPK produce 52 tens of spades; ordinary decks/shuffles match LuaJIT and repeat')

main = z.read('main.lua').decode()
assert 'math.random, math.randomseed = seed_rng.random, seed_rng.randomseed' in main
assert '\nmath.randomseed( G.SEED )' in main
assert not re.search(r'--\s*(?:if seed then )?math.randomseed', source)
print('Packed runtime installs the generator and seed application is enabled')
