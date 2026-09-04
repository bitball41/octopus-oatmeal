#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

BOOTSTRAP_START = "<!-- OCTOPUS_MULTIPLAYER_BOOTSTRAP_START -->"
BOOTSTRAP_END = "<!-- OCTOPUS_MULTIPLAYER_BOOTSTRAP_END -->"

STUB = '''    <script>
      window.__octopusTextInputActive = !!window.__octopusTextInputActive;
      window.__octopusTextKeyQueue = window.__octopusTextKeyQueue || [];
      window.OctopusMultiplayer = window.OctopusMultiplayer || { _pending: [] };
      window.OctopusMultiplayer._pending = Array.isArray(window.OctopusMultiplayer._pending)
        ? window.OctopusMultiplayer._pending
        : [];
      [
        "fromLuaEncoded",
        "setSaveDirectoryEncoded",
        "setTextInputActiveEncoded",
        "createLobby",
        "joinLobbyEncoded",
        "leaveLobby",
        "handleBrowserTextKey",
      ].forEach(function (method) {
        if (typeof window.OctopusMultiplayer[method] !== "function") {
          window.OctopusMultiplayer[method] = function () {
            this._pending.push([method, Array.from(arguments)]);
          };
        }
      });
    </script>
'''


def find_game_script(text: str):
    match = re.search(
        r'<script(?:\s+[^>]*)?\s+src="[^"]*game\.js[^"]*"[^>]*></script>',
        text,
        re.I,
    )
    if not match:
        raise RuntimeError("game.js script anchor not found")
    return match


def remove_generated_block(text: str) -> str:
    marker_pattern = re.compile(
        rf'[ \t]*{re.escape(BOOTSTRAP_START)}\n.*?{re.escape(BOOTSTRAP_END)}\n?',
        re.S,
    )
    text = marker_pattern.sub('', text)

    # Remove pre-marker bootstrap versions from older generated HTML.
    text = re.sub(
        r'[ \t]*<script>\s*(?:window\.__octopusTextInputActive|window\.OctopusMultiplayer).*?</script>\n?',
        '',
        text,
        count=1,
        flags=re.S,
    )

    # Remove any old multiplayer module tags outside the generated block.
    text = re.sub(
        r'[ \t]*<script\s+type="module"\s+src="[^"]*multiplayer(?:_native)?\.js(?:\?[^\"]*)?"\s*></script>\n?',
        '',
        text,
        flags=re.I,
    )
    return text


def install_bridge(text: str, module_src: str) -> str:
    text = remove_generated_block(text)
    game_script = find_game_script(text)
    block = (
        f'    {BOOTSTRAP_START}\n'
        + STUB
        + f'    <script type="module" src="{module_src}"></script>\n'
        + f'    {BOOTSTRAP_END}\n'
    )
    return text[:game_script.start()] + block + text[game_script.start():]


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
        "https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@main/multiplayer_native.js?v=native-menu-20260904-2",
    )
    path.write_text(text, "utf-8")


def main() -> None:
    patch_balatro()
    patch_index()
    print("Patched native multiplayer HTML entry points")


if __name__ == "__main__":
    main()
