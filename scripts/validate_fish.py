#!/usr/bin/env python3
"""Verify Fish and Chips browser archive and mode wiring before publishing."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "fish-and-chips"


def validate_archive():
    parts = json.loads((DEST / "parts.json").read_text())
    assert len(parts) >= 2, "Fish and Chips should have a split archive"
    assert all((DEST / p).stat().st_size <= 20 * 1024 * 1024 for p in parts)
    blob = b"".join((DEST / p).read_bytes() for p in parts)
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        names = set(archive.namelist())
        needed = {
            "Mods/FishAndChips/main.lua",
            "Mods/FishAndChips/src/fishminigamemechanics.lua",
            "Mods/FishAndChips/src/mod_menu.lua",
            "Mods/PotatoPatchUtils/main.lua",
            "Mods/Steamodded/src/preflight/loader.lua",
            "browser/platform.lua",
        }
        assert 'Mods/FishAndChips/assets/2x/core/soup.png' in names, 'Fish 2x core sprites are missing'
        assert 'Mods/FishAndChips/assets/2x/breukel/markerels.png' in names, 'Fish mixed-case asset alias missing'
        assert sum(name.startswith('Mods/FishAndChips/assets/2x/') and name.endswith('.png') for name in names) >= 200
        missing = needed - names
        assert not missing, f"Missing content: {sorted(missing)}"
        assert not any(n.startswith("Mods/Multiplayer/") for n in names)
        assert not any(n.startswith("Mods/Cryptid/") for n in names)
        try:
            from lupa.lua51 import LuaRuntime
        except ImportError:
            from lupa import LuaRuntime
        lua = LuaRuntime(unpack_returned_tuples=True)
        compile_lua = lua.eval("function(s, n) local f,e=loadstring(s,n); return f~=nil,e end")
        for path in sorted(n for n in names if n.endswith(".lua")):
            ok, error = compile_lua(archive.read(path).decode("utf-8"), "@" + path)
            assert ok, f"Lua syntax failure in {path}: {error}"
        assert 'function M.getNormalizedPath' in archive.read('browser/nativefs.lua').decode('utf-8'), 'Steamodded NativeFS path shim missing'
        # love.js cannot recover from a failed shader compile, so the WebGL 1
        # repairs must be present in every packaged shader.
        smods = archive.read('Mods/Steamodded/src/game_object.lua').decode('utf-8')
        assert 'vec2[8](' not in smods, 'Steamodded atlas scaling shader still uses a GLSL 3 array'
        assert 'if self.image_data and self.image_data.release then' in smods, 'Atlas reload memory release missing'
        import re
        for path in sorted(n for n in names if n.startswith('Mods/FishAndChips/assets/shaders/') and n.endswith('.fs')):
            code = archive.read(path).decode('utf-8')
            assert not re.search(r'\b\w+\s*\[\s*\d*\s*\]\s*\(', code), f'GLSL 3 array constructor in {path}'
            assert not re.search(r'\b(?:extern|uniform)\b[^;(){}]*=', code), f'Uniform initializer in {path}'
    report = json.loads((ROOT / "build" / "patch-report-fish-and-chips.json").read_text())
    failures = [r for r in report if r["status"] not in ("applied", "not-applicable")]
    assert not failures, f"{len(failures)} unresolved Lovely patches"
    print(f"Fish and Chips archive: {len(parts)} valid chunks, {len(names)} entries, {len(report)} patches")


def validate_launcher():
    for filename in ("index.html", "balatro.html"):
        s = (ROOT / filename).read_text()
        assert 'id="mode-fish"' in s
        assert 'bindMode("mode-fish", "fish");' in s
        assert '"fish-and-chips/"' in s
        assert 'love-fish-and-chips' in s
        assert '#mode-fish {background:' in s
        assert 'image-rendering: pixelated' not in s, "Do not disable smoothing in CSS"
    print("Fish and Chips mode appears in both launchers; smoothing CSS unchanged")


if __name__ == "__main__":
    validate_archive()
    import sys
    if "--launcher" in sys.argv:
        validate_launcher()
