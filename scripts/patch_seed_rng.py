#!/usr/bin/env python3
"""Restore desktop-compatible seed application in the browser archive."""
import io
import zipfile
from pathlib import Path
from patch_seed_input import main as refresh_archive, replace_once

ROOT = Path(__file__).resolve().parents[1]
output = io.BytesIO()
with zipfile.ZipFile(ROOT / 'game.data') as original, zipfile.ZipFile(output, 'w') as rebuilt:
    for entry in original.infolist():
        if entry.filename == 'browser/seed_rng.lua':
            continue
        data = original.read(entry)
        if entry.filename == 'main.lua':
            text = data.decode()
            text = replace_once(text, 'require "engine/object"',
                'local seed_rng = require "browser/seed_rng"\n'
                'math.random, math.randomseed = seed_rng.random, seed_rng.randomseed\n'
                'require "engine/object"')
            text = text.replace('-- math.randomseed( G.SEED )', 'math.randomseed( G.SEED )')
            data = text.encode()
        elif entry.filename == 'functions/misc_functions.lua':
            text = data.decode().replace('\r\n', '\n')
            text = text.replace('-- if seed then math.randomseed(seed) end', 'if seed then math.randomseed(seed) end')
            text = text.replace('-- math.randomseed(seed)', 'math.randomseed(seed)')
            # Lua 5.1 tonumber("nan") is nil; desktop LuaJIT preserves NaN.
            # Keep exceptional hashes intact instead of crashing in math.abs.
            text = replace_once(text, 'function pseudoseed(key, predict_seed)',
                'local function seed_round(value)\n'
                '  if value ~= value then return value end\n'
                '  return tonumber(string.format("%.13f", value))\n'
                'end\n\nfunction pseudoseed(key, predict_seed)')
            text = text.replace('tonumber(string.format("%.13f", (2.134453429141+_pseed*1.72431234)%1))',
                                'seed_round((2.134453429141+_pseed*1.72431234)%1)')
            text = text.replace('tonumber(string.format("%.13f", (2.134453429141+G.GAME.pseudorandom[key]*1.72431234)%1))',
                                'seed_round((2.134453429141+G.GAME.pseudorandom[key]*1.72431234)%1)')
            data = text.encode()
        rebuilt.writestr(entry, data)
    entry = zipfile.ZipInfo('browser/seed_rng.lua', (2026, 9, 10, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    rebuilt.writestr(entry, (ROOT / 'browser/seed_rng.lua').read_bytes())
(ROOT / 'game.data').write_bytes(output.getvalue())
refresh_archive()
