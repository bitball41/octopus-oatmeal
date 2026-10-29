#!/usr/bin/env python3
"""Validate actual published recipes and randomizer behavior against Lua 5.1."""
import hashlib,io,json,zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'custom/manifest.json').read_text())
assert len(manifest['builds'])==64, 'Every supported mod subset must have a recipe'
seen={}
for key,recipe in manifest['builds'].items():
    assert key==('+'.join(sorted(recipe['mods'])) or 'base')
    for pack in [*recipe['packs'],recipe['overlay']]:
        if pack['sha256'] in seen:continue
        chunks=[]
        for name in pack['parts']:
            data=(ROOT/'custom'/name).read_bytes()
            assert 0<len(data)<=18*1024*1024
            chunks.append(data)
        blob=b''.join(chunks);assert hashlib.sha256(blob).hexdigest()==pack['sha256']
        seen[pack['sha256']]=set(zipfile.ZipFile(io.BytesIO(blob)).namelist())
for key in ['base','CardSleeves','Cryptid+Multiplayer','CardSleeves+Cryptid+Handy+Multiplayer']:
    spec=manifest['builds'][key];names=set().union(*(seen[p['sha256']] for p in [*spec['packs'],spec['overlay']]))
    assert 'Mods/ValueRandomizer/ValueRandomizer.lua' in names
    for mod in ['CardSleeves','Cryptid','Handy','Multiplayer','Bunco']:
        assert any(n.startswith('Mods/'+mod+'/') for n in names)==(mod in spec['mods']), (key,mod)

from validate_randomizer_design import validate
validate()
print('64 exact mod recipes, pack checksums/CDN sizes and selected-only mod contents passed')
