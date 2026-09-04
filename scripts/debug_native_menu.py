#!/usr/bin/env python3
import re, zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
data = root / 'game.data'

with zipfile.ZipFile(data, 'r') as z:
    names = z.namelist()
    texts = {}
    for name in names:
        if name.endswith('.lua'):
            try:
                texts[name] = z.read(name).decode('utf-8')
            except Exception:
                pass

print('=== archive ===')
print('files', len(names))
print('has mp', 'octopus_multiplayer.lua' in names)

print('\n=== main.lua first 120 lines ===')
main = texts.get('main.lua', '')
for i, line in enumerate(main.splitlines()[:120], 1):
    print(f'{i:04d}: {line}')

print('\n=== UI_definitions menu function ===')
ui = texts.get('functions/UI_definitions.lua', '')
needle = 'function create_UIBox_main_menu_buttons()'
pos = ui.find(needle)
print('definition count', ui.count(needle))
print('button marker count', ui.count('octopus_multiplayer_button'))
if pos >= 0:
    lines = ui[:pos].count('\n') + 1
    chunk = ui[pos:pos+5000]
    for j, line in enumerate(chunk.splitlines()[:110], lines):
        print(f'{j:05d}: {line}')

print('\n=== all references to menu function ===')
for name, text in texts.items():
    if 'create_UIBox_main_menu_buttons' in text:
        for m in re.finditer(r'.{0,100}create_UIBox_main_menu_buttons.{0,140}', text):
            print(name, '::', m.group(0).replace('\n', ' '))

print('\n=== UI_definitions loading references ===')
for name, text in texts.items():
    if 'UI_definitions' in text:
        for line in text.splitlines():
            if 'UI_definitions' in line:
                print(name, '::', line)

print('\n=== overwrite candidates ===')
for name, text in texts.items():
    for pat in [
        'create_UIBox_main_menu_buttons =',
        'G.UIDEF.main_menu',
        'main_menu_buttons',
        'MAIN_MENU_UI',
    ]:
        if pat in text:
            print(name, 'contains', repr(pat), 'x', text.count(pat))

print('\n=== MP require/update references ===')
for name, text in texts.items():
    if 'OCTOPUS_MP' in text or 'octopus_multiplayer' in text:
        print(name)
        for line in text.splitlines():
            if 'OCTOPUS_MP' in line or 'octopus_multiplayer' in line:
                print('  ', line)
