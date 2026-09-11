#!/usr/bin/env python3
"""Desktop-compatible seed application, shared by both browser builds."""
import io
import zipfile
from pathlib import Path
from patch_seed_input import replace_once
ROOT = Path(__file__).resolve().parents[1]

def patch(name, data):
    if name == 'main.lua':
        text = data.decode()
        text = replace_once(text, 'require "engine/object"',
            'local seed_rng = require "browser/seed_rng"\n'
            'math.random, math.randomseed = seed_rng.random, seed_rng.randomseed\n'
            'require "engine/object"')
        text = text.replace('-- math.randomseed( G.SEED )', 'math.randomseed( G.SEED )')
        data = text.encode()
    elif name == 'functions/misc_functions.lua':
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
    return data

def apply(files):
    for name in list(files):
        files[name] = patch(name, files[name])
    files["browser/seed_rng.lua"] = (ROOT / "browser/seed_rng.lua").read_bytes()

def main():
    with zipfile.ZipFile(ROOT / "game.data") as z:
        files = {n:z.read(n) for n in z.namelist()}
    apply(files)
    with zipfile.ZipFile(ROOT / "game.data", "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items(): z.writestr(name, data)
    from patch_seed_input import main as refresh_archive
    refresh_archive()

if __name__ == "__main__": main()
