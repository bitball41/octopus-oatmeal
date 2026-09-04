#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import re
import sys
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "game.data"
GAME_JS = ROOT / "game.js"
MP_LUA = ROOT / "octopus_multiplayer.lua"


def fail(message: str) -> None:
    raise RuntimeError(message)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0:
        fail(f"Patch target not found: {label}")
    if count > 1:
        print(f"warning: {label} matched {count} times; patching first occurrence", file=sys.stderr)
    return text.replace(old, new, 1)


def patch_lua(files: dict[str, bytes]) -> dict[str, bytes]:
    required = [
        "main.lua",
        "game.lua",
        "functions/state_events.lua",
        "functions/button_callbacks.lua",
    ]
    for name in required:
        if name not in files:
            fail(f"{name} is missing from game.data")

    mp_source = MP_LUA.read_bytes()
    files["octopus_multiplayer.lua"] = mp_source

    main = files["main.lua"].decode("utf-8")
    marker = 'local OCTOPUS_MP = require("octopus_multiplayer")'
    if marker not in main:
        main = marker + "\nOCTOPUS_MP.init()\n" + main
    files["main.lua"] = main.encode("utf-8")

    game = files["game.lua"].decode("utf-8")
    update_marker = "function Game:update(dt)"
    if "OCTOPUS_MP.update(dt)" not in game:
        game = replace_once(
            game,
            update_marker,
            update_marker + "\n    OCTOPUS_MP.update(dt)",
            "Game:update multiplayer tick",
        )

    original_end = "if G.GAME.chips - G.GAME.blind.chips >= 0 or G.GAME.current_round.hands_left < 1 then"
    if "if OCTOPUS_MP.should_end_round() then" not in game:
        game = replace_once(
            game,
            original_end,
            "if OCTOPUS_MP.should_end_round() then",
            "round-end condition",
        )
    files["game.lua"] = game.encode("utf-8")

    state_events = files["functions/state_events.lua"].decode("utf-8")
    score_anchor = "check_for_unlock({type = 'chip_score', chips = math.floor(hand_chips*mult)})"
    score_hook = score_anchor + "\n    OCTOPUS_MP.on_hand_scored(hand_chips*mult)"
    if "OCTOPUS_MP.on_hand_scored(hand_chips*mult)" not in state_events:
        state_events = replace_once(
            state_events,
            score_anchor,
            score_hook,
            "hand score hook",
        )

    round_anchor = "if game_over then"
    if "OCTOPUS_MP.on_round_end(game_over)" not in state_events:
        state_events = replace_once(
            state_events,
            round_anchor,
            "OCTOPUS_MP.on_round_end(game_over)\n    " + round_anchor,
            "blind-end hook",
        )
    files["functions/state_events.lua"] = state_events.encode("utf-8")

    buttons = files["functions/button_callbacks.lua"].decode("utf-8")
    start_anchor = "G:start_run(args)"
    if "OCTOPUS_MP.on_run_start()" not in buttons:
        buttons = replace_once(
            buttons,
            start_anchor,
            start_anchor + "\n    OCTOPUS_MP.on_run_start()",
            "run-start hook",
        )
    files["functions/button_callbacks.lua"] = buttons.encode("utf-8")

    return files


def rebuild_archive() -> bytes:
    if not zipfile.is_zipfile(DATA):
        fail("game.data is not a ZIP/LÖVE archive; cannot patch safely")

    with zipfile.ZipFile(DATA, "r") as zin:
        infos = zin.infolist()
        files = {info.filename: zin.read(info.filename) for info in infos if not info.is_dir()}
        dirs = [info for info in infos if info.is_dir()]

    files = patch_lua(files)

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        for info in dirs:
            zout.writestr(info, b"")
        written = set()
        for info in infos:
            if info.is_dir():
                continue
            data = files[info.filename]
            new_info = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            new_info.compress_type = zipfile.ZIP_DEFLATED
            new_info.external_attr = info.external_attr
            new_info.internal_attr = info.internal_attr
            new_info.create_system = info.create_system
            new_info.flag_bits = info.flag_bits
            zout.writestr(new_info, data)
            written.add(info.filename)
        for name in sorted(set(files) - written):
            zout.writestr(name, files[name])

    return out.getvalue()


def patch_game_js(blob: bytes) -> str:
    size = len(blob)
    digest = hashlib.sha256(blob).hexdigest()
    package_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"octopus-oatmeal:{digest}"))
    cache_tag = digest[:8]

    text = GAME_JS.read_text("utf-8")
    text, count = re.subn(
        r'var REMOTE_PACKAGE_BASE = "game\.data\?v=[^"]+";',
        f'var REMOTE_PACKAGE_BASE = "game.data?v={cache_tag}";',
        text,
        count=1,
    )
    if count != 1:
        fail("Could not update game.data cache tag in game.js")

    text, count = re.subn(
        r'package_uuid:\s*"[^"]+"',
        f'package_uuid: "{package_uuid}"',
        text,
        count=1,
    )
    if count != 1:
        fail("Could not update package_uuid in game.js")

    text, count = re.subn(
        r'remote_package_size:\s*\d+',
        f'remote_package_size: {size}',
        text,
        count=1,
    )
    if count != 1:
        fail("Could not update remote_package_size in game.js")

    text, count = re.subn(
        r'(filename:\s*"/game\.love",\s*\n\s*crunched:\s*0,\s*\n\s*start:\s*0,\s*\n\s*end:)\s*\d+',
        rf'\1 {size}',
        text,
        count=1,
    )
    if count != 1:
        fail("Could not update /game.love end offset in game.js")

    return text


def main() -> None:
    archive = rebuild_archive()
    DATA.write_bytes(archive)
    GAME_JS.write_text(patch_game_js(archive), "utf-8")
    print(f"Patched game.data: {len(archive)} bytes")


if __name__ == "__main__":
    main()
