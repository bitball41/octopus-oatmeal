#!/usr/bin/env python3
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

try:
    from lupa import LuaRuntime, lua_type
except ImportError as exc:  # pragma: no cover - CI installs Lua instead of lupa
    raise SystemExit(
        "validate_native_menu.py requires lupa for the runtime harness"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with zipfile.ZipFile(ROOT / "game.data") as archive:
        main_lua = archive.read("main.lua").decode("utf-8")
        ui_lua = archive.read("functions/UI_definitions.lua").decode("utf-8")
        multiplayer_lua = archive.read("octopus_multiplayer.lua").decode("utf-8")

    callback_module = main_lua.index('require "functions/button_callbacks"')
    multiplayer_loader = main_lua.index('local OCTOPUS_MP = require("octopus_multiplayer")')
    callback_install = main_lua.index("OCTOPUS_MP.install_callbacks()")
    love_run = main_lua.index("function love.run()")
    if not callback_module < multiplayer_loader < callback_install < love_run:
        raise AssertionError("multiplayer callbacks are not installed before love.run")

    lua = LuaRuntime(unpack_returned_tuples=True)
    compile_lua = lua.eval(
        "function(source, name) local fn, err = load(source, name); "
        "if not fn then error(err) end; return true end"
    )
    compile_lua(main_lua, "@main.lua")
    lua.execute(
        """
        local colour = {1, 1, 1, 1}
        G = {
          UIDEF = {}, FUNCS = {},
          UIT = {ROOT=1, C=2, R=3, T=4, O=5, B=6},
          C = {
            CLEAR=colour, L_BLACK=colour, BLUE=colour, ORANGE=colour,
            RED=colour, PALE_GREEN=colour, PURPLE=colour, WHITE=colour,
            GREY=colour, DARK_EDITION=colour, UI={TEXT_LIGHT=colour},
          },
          SETTINGS={tutorial_complete=true, paused=false}, CONTROLLER={},
          F_ENGLISH_ONLY=true, F_LINKTREE=false, FTP_LOCKED=false,
          F_JAN_CTA=false, F_QUIT_BUTTON=false, F_DISP_USERNAME=false,
        }
        love = {
          filesystem = {
            getSaveDirectory=function() return '/tmp/octopus' end,
            getDirectoryItems=function() return {} end,
          },
          system = {setClipboardText=function() end},
        }
        function localize(key) return key end
        function Sprite(...) error('unexpected Sprite construction') end
        """
    )
    lua.execute(ui_lua)

    def walk_buttons(node: object) -> list[tuple[str | None, str]]:
        found: list[tuple[str | None, str]] = []
        if lua_type(node) != "table":
            return found
        config = node["config"]
        if lua_type(config) == "table" and config["button"]:
            found.append((config["id"], config["button"]))
        for child_key in ("nodes", "contents"):
            children = node[child_key]
            if lua_type(children) == "table":
                for _, child in children.items():
                    found.extend(walk_buttons(child))
        return found

    menu = lua.globals().create_UIBox_main_menu_buttons()
    menu_buttons = walk_buttons(menu)
    expected_menu = ["setup_run", "options", "your_collection", "octopus_multiplayer"]
    actual_menu = [button for _, button in menu_buttons]
    if actual_menu != expected_menu:
        raise AssertionError(f"unexpected main-menu buttons: {actual_menu}")

    menu_ids = {identifier for identifier, _ in menu_buttons}
    required_ids = {
        "main_menu_play",
        "collection_button",
        "octopus_multiplayer_button",
    }
    if not required_ids <= menu_ids:
        raise AssertionError(f"missing native menu ids: {sorted(required_ids - menu_ids)}")

    multiplayer = lua.execute(multiplayer_lua)
    multiplayer.install_callbacks()
    funcs = lua.globals().G["FUNCS"]
    callback_names = [
        "octopus_multiplayer",
        "octopus_create_lobby",
        "octopus_copy_lobby",
        "octopus_join_lobby",
        "octopus_leave_lobby",
    ]
    missing_callbacks = [name for name in callback_names if lua_type(funcs[name]) != "function"]
    if missing_callbacks:
        raise AssertionError(f"missing runtime callbacks: {missing_callbacks}")

    lua.execute(
        """
        function create_text_input(args)
          return {n=G.UIT.R, config={id='octopus_join_code'}, nodes={}}
        end
        function create_UIBox_generic_options(args) return args end
        opened_overlay = nil
        G.FUNCS.overlay_menu = function(args) opened_overlay = args.definition end
        """
    )
    funcs["octopus_multiplayer"]()
    overlay = lua.globals().opened_overlay
    if lua_type(overlay) != "table":
        raise AssertionError("MULTIPLAYER callback did not open the native overlay")
    overlay_buttons = [button for _, button in walk_buttons(overlay)]
    expected_overlay = [
        "octopus_create_lobby",
        "octopus_copy_lobby",
        "octopus_join_lobby",
        "octopus_leave_lobby",
    ]
    if overlay_buttons != expected_overlay:
        raise AssertionError(f"unexpected lobby callbacks: {overlay_buttons}")

    print("packed Lua runtime validation passed")
    print("main menu: PLAY / OPTIONS / COLLECTION / MULTIPLAYER")
    print("lobby callbacks:", ", ".join(overlay_buttons))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"native menu runtime validation failed: {exc}", file=sys.stderr)
        raise
