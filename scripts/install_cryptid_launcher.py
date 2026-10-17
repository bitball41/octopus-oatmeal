#!/usr/bin/env python3
"""Add the isolated Cryptid mode to both existing launcher entry points."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def main():
    for filename in ('index.html', 'balatro.html'):
        path = ROOT/filename
        text = path.read_text()
        if '#mode-cryptid {' not in text:
            text = text.replace('      #mode-multiplayer {', '''      #mode-cryptid {
        background: #17827a;
        color: #fff;
        text-transform: none;
        letter-spacing: 0.03em;
        min-width: 240px;
      }

      #mode-multiplayer {''')
        if 'Cryptid adds unbalanced cards' not in text:
            text = text.replace('          Each mode keeps a completely separate save.',
                '          Cryptid adds unbalanced cards and huge scores.\n          Each mode keeps a completely separate save.')
        if 'id="mode-cryptid"' not in text:
            text = text.replace('          <button id="mode-multiplayer"',
                '          <button id="mode-cryptid" type="button">Cryptid</button>\n          <button id="mode-multiplayer"')
        if '          cryptid: {' not in text:
            text = text.replace('          multiplayer: {', '''          cryptid: {
            persist: "/home/web_user/love-cryptid",
            dir: "cryptid/",
            multiplayer: false,
            memory: 536870912,
            parts: ["game.data.part0", "game.data.part1"],
          },
          multiplayer: {''')
        if filename == 'index.html' and 'bindMode("mode-cryptid", "cryptid")' not in text:
            text = text.replace('          bindMode("mode-multiplayer", "multiplayer");',
                '          bindMode("mode-cryptid", "cryptid");\n          bindMode("mode-multiplayer", "multiplayer");')
        if filename == 'balatro.html':
            text = text.replace('["vanilla", "paperback", "bunco", "pokermon", "multiplayer"].forEach',
                '["vanilla", "paperback", "bunco", "pokermon", "cryptid", "multiplayer"].forEach')
        assert 'id="mode-cryptid"' in text and 'dir: "cryptid/"' in text
        path.write_text(text)

if __name__ == '__main__':
    main()
