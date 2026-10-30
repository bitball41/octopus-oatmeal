#!/usr/bin/env python3
"""Update existing multiplayer Lua overlays without recompiling content mods."""
import hashlib,io,json,zipfile
from pathlib import Path
from multiplayer_start import apply
from patch_multiplayer import patch_game_js
ROOT=Path(__file__).resolve().parents[1]
TARGET='Mods/Multiplayer/ui/lobby/lobby.lua'

def patched(blob):
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        files={n:z.read(n) for n in z.namelist()}
    before=dict(files);apply(files)
    if before==files:return blob
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
    return out.getvalue()

path=ROOT/'custom/manifest.json';manifest=json.loads(path.read_text());count=0
for recipe in manifest['builds'].values():
    if not recipe['multiplayer']:continue
    spec=recipe['overlay'];blob=b''.join((ROOT/'custom'/part).read_bytes() for part in spec['parts'])
    updated=patched(blob)
    if updated==blob:continue
    digest=hashlib.sha256(updated).hexdigest();parts=[]
    for i,start in enumerate(range(0,len(updated),18*1024*1024)):
        name=f'packs/{digest}.{i}.zip';(ROOT/'custom'/name).write_bytes(updated[start:start+18*1024*1024]);parts.append(name)
    recipe['overlay']={'parts':parts,'sha256':digest};count+=1
path.write_text(json.dumps(manifest,separators=(',',':'))+'\n')
path=ROOT/'game.data';blob=path.read_bytes();updated=patched(blob)
if blob!=updated:
    path.write_bytes(updated)
    js=ROOT/'game.js';js.write_text(patch_game_js(updated,js.read_text()))
print(f'Updated {count} custom multiplayer combinations and the standalone multiplayer runtime')
