#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

BOOTSTRAP_START = "<!-- OCTOPUS_MULTIPLAYER_BOOTSTRAP_START -->"
BOOTSTRAP_END = "<!-- OCTOPUS_MULTIPLAYER_BOOTSTRAP_END -->"
PINNED_RUNTIME_START = "<!-- OCTOPUS_PINNED_RUNTIME_START -->"
PINNED_RUNTIME_END = "<!-- OCTOPUS_PINNED_RUNTIME_END -->"

STUB = '''    <script>
      window.OctopusMP = window.OctopusMP || { _pending: [] };
      ["attach", "send"].forEach(function (method) {
        if (typeof window.OctopusMP[method] !== "function") {
          window.OctopusMP[method] = function () {
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
        r'[ \t]*<script\s+type="module"\s+src="[^"]*multiplayer(?:_native|_upstream)?\.js(?:\?[^\"]*)?"\s*></script>\n?',
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
    text = install_bridge(text, "multiplayer_upstream.js")
    path.write_text(text, "utf-8")


def patch_index() -> None:
    path = ROOT / "index.html"
    text = path.read_text("utf-8")

    # The downloadable launcher resolves main through GitHub's API, then
    # loads multiplayer_upstream.js, game.js, love.js, WASM, and game.data from
    # that one immutable commit. Never rewrite it back to mutable @main URLs:
    # jsDelivr can resolve separate mutable requests to different revisions.
    if text.count(PINNED_RUNTIME_START) != 1 or text.count(PINNED_RUNTIME_END) != 1:
        raise RuntimeError("index.html is missing its immutable runtime loader")
    if re.search(
        r'<script[^>]+src="https://cdn\.jsdelivr\.net/gh/'
        r'bitball41/octopus-oatmeal@main/(?:multiplayer_native|game|love)\.',
        text,
        re.I,
    ):
        raise RuntimeError("index.html still loads a mutable @main runtime asset")
    text = re.sub(re.escape(BOOTSTRAP_START)+r'.*?'+re.escape(BOOTSTRAP_END),
                  BOOTSTRAP_START+'\n'+STUB+'    '+BOOTSTRAP_END,text,flags=re.S)
    text = text.replace('"multiplayer_native.js", true', '"multiplayer_upstream.js", true')
    path.write_text(text, "utf-8")


def main() -> None:
    patch_balatro()
    patch_index()
    print("Patched native multiplayer HTML entry points")


if __name__ == "__main__":
    main()
