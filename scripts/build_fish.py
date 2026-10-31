#!/usr/bin/env python3
"""Build Fish and Chips + Potato Patch Utils as an isolated browser mode.

Upstream sources are pinned to commits. The existing preset archives and
rendering / smoothing settings are not changed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import zipfile
import json
import subprocess
import tempfile
from pathlib import Path

import build_upstream as browser

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "APotatoPatchUtils": (
        "https://github.com/Balatro-Potato-Patch/Potato-Patch-Utils",
        "c1df6cda90703d3408002d95a57de8b36abf152d",
        "PotatoPatchUtils",
    ),
    "FishAndChips": (
        "https://github.com/Balatro-Potato-Patch/Fish-and-Chips",
        "0ca961ed80240dc0d58b86ff4c7fa62f995b6520",
        "FishAndChips",
    ),
}


def download_sources(lock):
    cache = ROOT / "build" / "fish-sources"
    cache.mkdir(parents=True, exist_ok=True)
    for name, (url, commit, folder) in SOURCES.items():
        archive = cache / (name + ".zip")
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            subprocess.run(["git", "-C", tmp, "fetch", "--depth=1", url, commit],
                           check=True, stdout=subprocess.DEVNULL)
            fetched = subprocess.check_output(
                ["git", "-C", tmp, "rev-parse", "FETCH_HEAD"], text=True).strip()
            if fetched != commit:
                raise RuntimeError(f"{name}: fetched {fetched}, expected {commit}")
            subprocess.run(["git", "-C", tmp, "archive", "--format=zip",
                            "--output=" + str(archive), commit], check=True)
        if name == "FishAndChips":
            # Upstream Lovely target selectors sometimes start with a slash.
            # Our archive resolver already inserts the directory separator.
            with zipfile.ZipFile(archive) as source:
                files = {item.filename: source.read(item.filename)
                         for item in source.infolist() if not item.is_dir()}
            for path, data in files.items():
                if path.startswith("lovely/") and path.endswith(".toml"):
                    files[path] = data.replace(
                        b'=[SMODS FishAndChips "/',
                        b'=[SMODS FishAndChips "')
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as out:
                for path, data in files.items():
                    out.writestr(path, data)
        lock[name] = {
            "archive": "../build/fish-sources/" + archive.name,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        }
        browser.MOD_FOLDERS[name] = folder
        print(f"Pin {name}: {commit}")


def build(release=False, candidate=False):
    lock = json.loads((ROOT / "vendor" / "upstream.json").read_text())
    lock["Steamodded"] = lock["SteamoddedCryptid"]  # v26.829.0
    download_sources(lock)
    # Steamodded v26.829.0 uses the `file` shader argument, unlike older packs.
    # Reuse the newer adapter without enabling Cryptid-specific modes or assets.
    import browser_adapters
    original_adapt = browser_adapters.adapt_sources
    def fish_adapt(files, flavor='multiplayer'):
        # The browser VM is Lua 5.1 and lacks LuaJIT's goto statement.
        prefix = 'Mods/FishAndChips/content/'
        def edit(relative, transform):
            key = prefix + relative
            before = files[key].decode('utf-8')
            after = transform(before)
            if after == before or 'goto ' in after or '::continue::' in after:
                raise RuntimeError('Fish Lua 5.1 rewrite failed: ' + relative)
            files[key] = after.encode('utf-8')
        edit('aure-allu/Aure-Allu.lua', lambda s: s.replace('goto skip', 'return distance').replace('::skip::', ''))
        edit('hayayaya/ellen/8f.lua', lambda s: s.replace('if not blind then\n\t\t\tgoto continue\n\t\tend', 'if blind then').replace('::continue::', 'end'))
        for relative in ('hayayaya/ellen/mewtwo.lua',):
            edit(relative, lambda s: s.replace('for _, c in ipairs(G.fac_fish_area.cards) do',
                'for _, c in ipairs(G.fac_fish_area.cards) do\n            repeat')
                .replace('goto continue', 'break').replace('::continue::', 'until true'))
        edit('hayayaya/ellen/woke.lua', lambda s: s.replace(
            'for _, c in ipairs(G.fac_fish_area.cards) do\n\t\t\t-- Must not be itself',
            'for _, c in ipairs(G.fac_fish_area.cards) do\n            repeat\n\t\t\t-- Must not be itself'
        ).replace('goto continue', 'break').replace('::continue::', 'until true'))
        edit('minty/tundraeel.lua', lambda s: s.replace('if diff < 1 then goto nvm end', 'if diff >= 1 then')
             .replace('::nvm::', 'end'))
        return original_adapt(files, flavor='cryptid' if flavor == 'fish-and-chips' else flavor)
    browser_adapters.adapt_sources = fish_adapt
    browser.adapt_sources = fish_adapt  # build_upstream imported it by name
    original_apply = browser.apply_lovely
    def fish_apply(files, mods, pinned, flavor=None):
        # Apply the existing browser anchors for Steamodded 26.829.
        # This does not enable Cryptid or include its content.
        return original_apply(files, mods, pinned, "cryptid")
    browser.apply_lovely = fish_apply
    original_patch = browser.adapt_patch
    def fish_patch(mod, name, index, patch, source):
        p, reason = original_patch(mod, name, index, patch, source)
        if mod != 'FishAndChips' or reason:
            return p, reason
        key = (name, index)
        if key == ('lovely/stats.toml', 1):
            # Browser saves use decoded profile objects instead of the
            # desktop's inline `progress` literal; lazily initialize the
            # fishing stats on save after the profile has been loaded.
            p['pattern'] = 'function Game:save_progress()'
            p['position'] = 'after'
            fields = ('career_fish_caught', 'career_perfect_catch',
                      'career_treasure_caught', 'career_lines_snapped',
                      'career_sand_dollars', 'career_fish_sold')
            collections = ('environments_data', 'baits_used',
                           'fish_data', 'rod_data', 'bait_data')
            defaults = ['    ' + name + ' = 0,' for name in fields]
            defaults += ['    ' + name + ' = {},' for name in collections]
            p['payload'] = ('local profile = G.PROFILES and G.PROFILES[G.SETTINGS.profile]\n'
                            'if profile then\n'
                            '    profile.fac_fishing = profile.fac_fishing or {\n' +
                            '\n'.join(defaults) + '\n    }\nend')
        if key == ('lovely/menu.toml', 7):
            p['pattern'] = ('G.VIBRATION = G.VIBRATION + 1\n'
                            'G.MOBILE_VIBRATION_QUEUE = math.max(G.MOBILE_VIBRATION_QUEUE or 0, 2)\n'
                            'return true\nend)}))')
        if key == ('lovely/fish.toml', 4):
            p['pattern'] = "elseif set == 'Blind' then"
            p['position'] = 'before'
        if key == ('lovely/astra-missingno/ascii.toml', 1):
            p['pattern'] = 'state.fish_vel = state.fish_vel + (state.fish_goal_vel - state.fish_vel) * velocity_blend'
        if key in (('lovely/stats.toml', 1), ('lovely/menu.toml', 7)):
            marker = 'progress' if 'stats' in name else 'G.VIBRATION'
            lines = source.splitlines()
            matches = [(i, line) for i, line in enumerate(lines) if marker in line]
            print('FISH SOURCE ANCHORS', key,
                  [(i+1, lines[max(0, i-3):i+7]) for i, _ in matches[:8]], flush=True)
        if key in (
            ('lovely/crimsonseraphim/card_draw.toml', 7),
            ('lovely/crimsonseraphim/larp.toml', 2),
            ('lovely/crimsonseraphim/multiboxes.toml', 1),
        ):
            return p, 'Optional/obsolete upstream contributor UI patch; source anchor is absent'
        return p, None
    browser.adapt_patch = fish_patch
    files, report = browser.build_smods_pack(
        ["Steamodded", "APotatoPatchUtils", "FishAndChips"],
        "fish-and-chips", ("browser/menu.lua",), lock,
    )
    # Optional integration with DebugPlus should not require DebugPlus itself.
    for row in report:
        if row["status"] == "missing-target" and "debugplus" in row["target"].lower():
            row.update(status="not-applicable", reason="DebugPlus is optional")
    for row in report:
        if row["status"] not in ("applied", "not-applicable"):
            print("FISH PATCH UNRESOLVED", row["mod"], row["manifest"], row["index"], row["kind"], row["status"], row["target"], "matches", row["matches"], "expected", row.get("expected"), flush=True)
    browser.summarize_report(report, "fish-and-chips",
                             "patch-report-fish-and-chips.json", candidate)
    return browser.emit_archive(
        files, ROOT / "build" / "fish-and-chips", (ROOT / "game.js").read_text(),
        ROOT / "fish-and-chips" if release else None,
        part_size=10 * 1024 * 1024,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--release", action="store_true")
    cli.add_argument("--candidate", action="store_true",
                     help="Diagnostic only: allow patch mismatches; do not publish.")
    opts = cli.parse_args()
    if opts.candidate and opts.release:
        cli.error("--candidate and --release cannot be combined")
    build(release=opts.release, candidate=opts.candidate)
