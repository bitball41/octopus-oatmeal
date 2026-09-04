#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

STUB = '''    <script>
      window.__octopusTextInputActive = false;
      window.__octopusTextKeyQueue = window.__octopusTextKeyQueue || [];
      window.OctopusMultiplayer = window.OctopusMultiplayer || {
        _pending: [],
        fromLuaEncoded: function () {
          this._pending.push(["fromLuaEncoded", Array.from(arguments)]);
        },
        setSaveDirectoryEncoded: function () {
          this._pending.push(["setSaveDirectoryEncoded", Array.from(arguments)]);
        },
        setTextInputActiveEncoded: function () {
          this._pending.push(["setTextInputActiveEncoded", Array.from(arguments)]);
        },
        createLobby: function () {
          this._pending.push(["createLobby", Array.from(arguments)]);
        },
        joinLobbyEncoded: function () {
          this._pending.push(["joinLobbyEncoded", Array.from(arguments)]);
        },
        leaveLobby: function () {
          this._pending.push(["leaveLobby", Array.from(arguments)]);
        },
        handleBrowserTextKey: function () {
          this._pending.push(["handleBrowserTextKey", Array.from(arguments)]);
        },
      };

      (function () {
        function loveKeyFromBrowserEvent(e) {
          var special = {
            Backspace: "backspace",
            Delete: "delete",
            Enter: "return",
            Escape: "escape",
            CapsLock: "capslock",
            ArrowLeft: "left",
            ArrowRight: "right",
            Space: "space",
          };
          if (special[e.code]) return special[e.code];
          if (typeof e.key === "string" && /^[A-Za-z]$/.test(e.key)) {
            return e.key.toLowerCase();
          }
          if (typeof e.key === "string" && /^[0-9]$/.test(e.key)) {
            return e.key;
          }
          return null;
        }

        window.addEventListener(
          "keydown",
          function (e) {
            if (!window.__octopusTextInputActive) return;
            if (e.ctrlKey || e.metaKey || e.altKey) return;
            var key = loveKeyFromBrowserEvent(e);
            if (!key) return;

            e.preventDefault();
            e.stopPropagation();
            if (e.stopImmediatePropagation) e.stopImmediatePropagation();

            var bridge = window.OctopusMultiplayer;
            if (bridge && typeof bridge.handleBrowserTextKey === "function") {
              bridge.handleBrowserTextKey(key, !!e.shiftKey);
            } else {
              window.__octopusTextKeyQueue.push([key, !!e.shiftKey]);
            }
          },
          true
        );
      })();
    </script>
'''


def replace_bridge_script(text: str) -> str:
    markers = ["window.__octopusTextInputActive", "window.OctopusMultiplayer"]
    marker_pos = -1
    for marker in markers:
        marker_pos = text.find(marker)
        if marker_pos >= 0:
            break

    if marker_pos >= 0:
        start = text.rfind("    <script>", 0, marker_pos)
        end = text.find("    </script>", marker_pos)
        if start >= 0 and end >= 0:
            end += len("    </script>")
            if end < len(text) and text[end] == "\n":
                end += 1
            return text[:start] + STUB + text[end:]

    game_script = re.search(r'    <script(?:\s+[^>]*)?\s+src="[^"]*game\.js[^"]*"[^>]*></script>', text)
    if not game_script:
        raise RuntimeError("game.js script anchor not found")
    return text[:game_script.start()] + STUB + text[game_script.start():]


def install_bridge(text: str, module_src: str) -> str:
    text = text.replace("multiplayer.js", "multiplayer_native.js")
    text = replace_bridge_script(text)

    module_pattern = re.compile(r'    <script type="module" src="[^"]*multiplayer(?:_native)?\.js"></script>\s*')
    desired = f'    <script type="module" src="{module_src}"></script>\n'
    if module_pattern.search(text):
        text = module_pattern.sub(desired, text, count=1)
    else:
        game_script = re.search(r'    <script(?:\s+[^>]*)?\s+src="[^"]*game\.js[^"]*"[^>]*></script>', text)
        if not game_script:
            raise RuntimeError("game.js script anchor not found after bridge install")
        text = text[:game_script.start()] + desired + text[game_script.start():]

    return text


def patch_balatro() -> None:
    path = ROOT / "balatro.html"
    text = path.read_text("utf-8")
    text = install_bridge(text, "multiplayer_native.js")
    path.write_text(text, "utf-8")


def patch_index() -> None:
    path = ROOT / "index.html"
    text = path.read_text("utf-8")

    text = re.sub(
        r'https://cdn\.jsdelivr\.net/gh/bitball41/octopus-oatmeal@[^/]+/',
        'https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@main/',
        text,
    )

    text = install_bridge(
        text,
        "https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@main/multiplayer_native.js",
    )
    path.write_text(text, "utf-8")


def main() -> None:
    patch_balatro()
    patch_index()
    print("Patched native multiplayer HTML and browser text-input bridge")


if __name__ == "__main__":
    main()
