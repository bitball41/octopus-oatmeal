#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

STUB = '''    <script>
      window.OctopusMultiplayer = window.OctopusMultiplayer || {
        _pending: [],
        fromLuaEncoded: function () {
          this._pending.push(["fromLuaEncoded", Array.from(arguments)]);
        },
        setSaveDirectoryEncoded: function () {
          this._pending.push(["setSaveDirectoryEncoded", Array.from(arguments)]);
        },
      };
    </script>
'''


def patch_balatro() -> None:
    path = ROOT / "balatro.html"
    text = path.read_text("utf-8")
    if "OctopusMultiplayer" not in text:
        anchor = '    <script type="text/javascript" src="game.js?v=4e38bdee"></script>'
        if anchor not in text:
            raise RuntimeError("balatro.html game.js anchor not found")
        replacement = STUB + '    <script type="module" src="multiplayer.js"></script>\n' + anchor
        text = text.replace(anchor, replacement, 1)
    path.write_text(text, "utf-8")


def patch_index() -> None:
    path = ROOT / "index.html"
    text = path.read_text("utf-8")

    # The downloadable launcher must follow the current remote build; an immutable
    # pre-multiplayer commit would otherwise keep loading the old game.data forever.
    text = re.sub(
        r'https://cdn\.jsdelivr\.net/gh/bitball41/octopus-oatmeal@[^/]+/',
        'https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@main/',
        text,
    )

    if "OctopusMultiplayer" not in text:
        anchor = '    <script\n      type="text/javascript"\n      src="https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@main/game.js"'
        if anchor not in text:
            raise RuntimeError("index.html remote game.js anchor not found")
        module = (
            STUB
            + '    <script type="module" src="https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@main/multiplayer.js"></script>\n'
        )
        text = text.replace(anchor, module + anchor, 1)

    path.write_text(text, "utf-8")


def main() -> None:
    patch_balatro()
    patch_index()
    print("Patched multiplayer HTML entry points")


if __name__ == "__main__":
    main()
