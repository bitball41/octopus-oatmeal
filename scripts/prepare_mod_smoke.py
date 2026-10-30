"""Instrument test-only copies of the release archives for browser smoke tests."""
import json
from pathlib import Path
import build_upstream as b

for folder, probe in [('vanilla-handy','quality_of_life'),('entropy','entropy')]:
    directory=b.ROOT/folder
    parts=json.loads((directory/'parts.json').read_text()) if (directory/'parts.json').exists() else ['game.data']
    files=b.unpack(b''.join((directory/part).read_bytes() for part in parts))
    files['main.lua'] += b'\n' + (b.ROOT/'scripts/probes'/f'{probe}.lua').read_bytes()
    b.emit_archive(files,b.ROOT/'build/mod-smoke'/folder,(directory/'game.js').read_text())
