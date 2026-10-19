#!/usr/bin/env python3
"""Add standalone Handy beside Vanilla, explicitly sharing Vanilla's saves."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    for filename in ('index.html', 'balatro.html'):
        path = ROOT / filename
        text = path.read_text()
        if 'id="mode-handy"' not in text:
            text = text.replace('<button id="mode-vanilla" type="button">Vanilla</button>',
                '<button id="mode-vanilla" type="button">Vanilla</button>\n'
                '          <button id="mode-handy" type="button">Vanilla + Handy</button>')
        if '#mode-handy {' not in text:
            text = text.replace('      #mode-multiplayer {',
                '      #mode-handy {\n        background: #287fa3;\n        color: #fff;\n      }\n\n'
                '      #mode-multiplayer {')
        text = text.replace('Each mode keeps a completely separate save.',
            'Vanilla and Vanilla + Handy share a save. Other modes keep separate saves.')
        if '          handy: {' not in text:
            text = text.replace('          paperback: {', '''          handy: {
            persist: "/home/web_user/love-vanilla",
            dir: "vanilla-handy/",
            cache: "/home/web_user/love-vanilla-handy",
            multiplayer: false,
          },
          paperback: {''')
        if 'cache: "/home/web_user/love-vanilla-handy"' not in text:
            text = text.replace('            dir: "vanilla-handy/",',
                '            dir: "vanilla-handy/",\n'
                '            cache: "/home/web_user/love-vanilla-handy",')
        if 'if (mode === "vanilla-handy")' not in text:
            text = text.replace('          if (mode === "modded")',
                '          if (mode === "vanilla-handy") return "handy";\n'
                '          if (mode === "modded")')
        if 'Module.archiveCacheNamespace =' not in text:
            text = text.replace('          Module.persistenceDatabase = spec.persist;',
                '          Module.persistenceDatabase = spec.persist;\n'
                '          Module.archiveCacheNamespace = spec.cache || spec.persist;')
        if filename == 'index.html' and 'bindMode("mode-handy", "handy")' not in text:
            text = text.replace('          bindMode("mode-vanilla", "vanilla");',
                '          bindMode("mode-vanilla", "vanilla");\n'
                '          bindMode("mode-handy", "handy");')
        if filename == 'balatro.html':
            text = text.replace('["vanilla", "paperback",', '["vanilla", "handy", "paperback",')
        assert 'id="mode-handy"' in text and 'dir: "vanilla-handy/"' in text
        path.write_text(text)


if __name__ == '__main__':
    main()
