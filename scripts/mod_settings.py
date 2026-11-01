#!/usr/bin/env python3
"""Mod-build settings fixes: pixel smoothing default and working high contrast.

`apply(files)` runs inside every Steamodded pack build (see finish_smods_pack).
Running this file patches the already-published mod archives in place, so the
change ships without a full upstream rebuild:

    python3 scripts/mod_settings.py            # patch every mod release
    python3 scripts/mod_settings.py paperback  # just one

Custom builds get the same Lua when the browser assembles them
(browser/custom-runtime.js). Vanilla and Vanilla + Handy are never touched.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = 'browser/mod_settings.lua'
SOURCE = ROOT / 'browser/lua' / MODULE
REQUIRE = b'require "browser.mod_settings"'
# Release folders of Steamodded builds ('' is the root multiplayer build).
RELEASES = ['paperback', 'bunco', 'pokermon', 'cryptid', 'entropy', 'fish-and-chips', '']


def apply(files):
    """Ship the module and load it after main.lua defines Game (idempotent)."""
    files[MODULE] = SOURCE.read_bytes()
    if REQUIRE not in files['main.lua']:
        files['main.lua'] = files['main.lua'].rstrip(b'\n') + b'\n' + REQUIRE + b'\n'
    return files


def patch_release(folder):
    import build_upstream as b
    directory = ROOT / folder if folder else ROOT
    parts_file = directory / 'parts.json'
    parts = json.loads(parts_file.read_text()) if parts_file.exists() else ['game.data']
    blob = b''.join((directory / part).read_bytes() for part in parts)
    files = b.unpack(blob)
    if files.get(MODULE) == SOURCE.read_bytes() and REQUIRE in files['main.lua']:
        print(f'{folder or "multiplayer"}: already current')
        return
    apply(files)
    # Keep each release's split size (Fish and Chips uses 10 MiB parts).
    part_size = (directory / parts[0]).stat().st_size if len(parts) > 1 else b.PART_SIZE
    for part in parts:
        (directory / part).unlink()
    if parts_file.exists():
        parts_file.unlink()
    b.emit_archive(files, directory, (directory / 'game.js').read_text(), part_size=part_size)


def main(argv):
    sys.path.insert(0, str(ROOT / 'scripts'))
    for folder in argv or RELEASES:
        if folder not in RELEASES:
            raise SystemExit(f'Unknown mod release folder: {folder}')
        patch_release(folder)


if __name__ == '__main__':
    main(sys.argv[1:])
