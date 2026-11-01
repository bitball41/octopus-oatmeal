#!/usr/bin/env python3
"""Mod-build fixes: pixel smoothing default, working high contrast, CRT colour pass.

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
# Steamodded moves the CRT pass into its ScreenShader loop, which the browser
# builds skip (see patch_compatibility.py). That left mods with no CRT shader at
# all: duller, washed-out colours than Vanilla. Restore Vanilla's own CRT pass.
CRT_ANCHOR = ('        G.screenwipe_amt = G.screenwipe_amt and (0.95*G.screenwipe_amt + 0.05*((self.screenwipe and 0.4 or '
              'self.screenglitch and 0.4) or 0)) or 1\n')
CRT_MARKER = "G.SHADERS['CRT']:send('distortion_fac'"
CRT_BLOCK = '''        G.SETTINGS.GRAPHICS.crt = G.SETTINGS.GRAPHICS.crt*0.3
        G.SHADERS['CRT']:send('distortion_fac', {1.0 + 0.07*G.SETTINGS.GRAPHICS.crt/100, 1.0 + 0.1*G.SETTINGS.GRAPHICS.crt/100})
        G.SHADERS['CRT']:send('scale_fac', {1.0 - 0.008*G.SETTINGS.GRAPHICS.crt/100, 1.0 - 0.008*G.SETTINGS.GRAPHICS.crt/100})
        G.SHADERS['CRT']:send('feather_fac', 0.01)
        G.SHADERS['CRT']:send('bloom_fac', 0)
        G.SHADERS['CRT']:send('time',400 + G.TIMERS.REAL)
        --G.SHADERS['CRT']:send('noise_fac',0.001*G.SETTINGS.GRAPHICS.crt/100)
        G.SHADERS['CRT']:send('crt_intensity', 0.16*G.SETTINGS.GRAPHICS.crt/100)
        G.SHADERS['CRT']:send('glitch_intensity', 0)--0.1*G.SETTINGS.GRAPHICS.crt/100 + (G.screenwipe_amt) + 1)
        G.SHADERS['CRT']:send('scanlines', G.CANVAS:getPixelHeight()*0.75/G.CANV_SCALE)
        G.SHADERS['CRT']:send('mouse_screen_pos', G.video_control and {love.graphics.getWidth( )/2, love.graphics.getHeight( )/2} or {G.ARGS.eased_cursor_pos.sx, G.ARGS.eased_cursor_pos.sy})
        G.SHADERS['CRT']:send('screen_scale', G.TILESCALE*G.TILESIZE)
        G.SHADERS['CRT']:send('hovering', 1)
        love.graphics.setShader( G.SHADERS['CRT'])
        G.SETTINGS.GRAPHICS.crt = G.SETTINGS.GRAPHICS.crt/0.3
'''
# Release folders of Steamodded builds ('' is the root multiplayer build).
RELEASES = ['paperback', 'bunco', 'pokermon', 'cryptid', 'entropy', 'fish-and-chips', '']


def apply(files):
    """Ship the module and load it after main.lua defines Game (idempotent)."""
    files[MODULE] = SOURCE.read_bytes()
    game = files['game.lua'].decode()
    if CRT_MARKER not in game:
        if game.count(CRT_ANCHOR) != 1:
            raise RuntimeError('game.lua: CRT anchor not found exactly once')
        files['game.lua'] = game.replace(CRT_ANCHOR, CRT_ANCHOR + CRT_BLOCK).encode()
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
    if files.get(MODULE) == SOURCE.read_bytes() and REQUIRE in files['main.lua'] and CRT_MARKER.encode() in files['game.lua']:
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
