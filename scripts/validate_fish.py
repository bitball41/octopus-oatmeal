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
