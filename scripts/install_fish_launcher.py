#!/usr/bin/env python3
"""Install Fish and Chips in the selector only after validated runtime assets exist."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = """
# Keep the Fish and Chips preset when this selector is regenerated.
if (ROOT / 'fish-and-chips' / 'parts.json').exists():
    from install_fish_launcher import install as install_fish
    install_fish()
"""


def require_replace(s, needle, replacement, path):
    if needle not in s:
        raise RuntimeError(f"{path}: missing launcher anchor {needle!r}")
    return s.replace(needle, replacement, 1)


def install():
    parts_path = ROOT / "fish-and-chips" / "parts.json"
    if not parts_path.is_file():
        raise RuntimeError("Fish and Chips archive has not been built")
    parts = json.loads(parts_path.read_text())
    if not parts or not all((parts_path.parent / p).is_file() for p in parts):
        raise RuntimeError("Fish and Chips archive parts are missing")

    for filename in ("index.html", "balatro.html"):
        path = ROOT / filename
        text = path.read_text()
        # Re-running is harmless (used by both existing and dedicated CI).
        if 'id="mode-fish"' not in text:
            text = require_replace(
                text, '<button id="mode-entropy" type="button" data-tip="entropy">Entropy</button>',
                '<button id="mode-entropy" type="button" data-tip="entropy">Entropy</button>\n'
                '          <button id="mode-fish" type="button" data-tip="fish">Fish &amp; Chips</button>',
                path)
        if "#mode-fish {background:" not in text:
            text = require_replace(
                text, '#mode-entropy {background:#9b2946;}',
                '#mode-entropy {background:#9b2946;}\n'
                '      #mode-fish {background:#257f98;}',
                path)
        tooltip = "fish:['Fish & Chips','Go fishing in Balatro: hundreds of fish, collectible rods and a fishing minigame. Separate save.'],"
        if tooltip not in text:
            text = require_replace(text,
                "            cryptid:['Cryptid',",
                "            " + tooltip + "\n            cryptid:['Cryptid',", path)
        if 'fish: {\n            persist:' not in text:
            config = (
                '          fish: {\n'
                '            persist: "/home/web_user/love-fish-and-chips",\n'
                '            dir: "fish-and-chips/",\n'
                '            multiplayer: false,\n'
                '            memory: 536870912,\n'
                '            parts: ' + json.dumps(parts) + ',\n'
                '          },\n'
            )
            text = require_replace(text, '          multiplayer: {\n',
                                   config + '          multiplayer: {\n', path)
        if 'bindMode("mode-fish", "fish")' not in text:
            text = require_replace(
                text, '          bindMode("mode-entropy", "entropy");',
                '          bindMode("mode-entropy", "entropy");\n'
                '          bindMode("mode-fish", "fish");', path)
        path.write_text(text)


def persist_hook():
    path = ROOT / "scripts" / "install_mod_selector.py"
    text = path.read_text()
    if "from install_fish_launcher import install as install_fish" not in text:
        path.write_text(text.rstrip() + "\n" + HOOK)


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--persist-hook", action="store_true")
    opt = cli.parse_args()
    install()
    if opt.persist_hook:
        persist_hook()
