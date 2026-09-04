#!/usr/bin/env python3
import zipfile
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

def show_context(name, needle, before=25, after=70):
    text = texts.get(name, '')
    lines = text.splitlines()
    hits = [i for i, line in enumerate(lines) if needle in line]
    print(f'\n=== {name} :: {needle} ({len(hits)} hits) ===')
    for hit in hits:
        lo = max(0, hit-before)
        hi = min(len(lines), hit+after+1)
        for i in range(lo, hi):
            print(f'{i+1:05d}: {lines[i]}')
        print('---')

print('=== archive ===')
print('files', len(names), 'has mp', 'octopus_multiplayer.lua' in names)
show_context('functions/UI_definitions.lua', 'function create_UIBox_main_menu_buttons()', 5, 65)
show_context('functions/UI_definitions.lua', 'function UIBox_button', 10, 110)
show_context('functions/common_events.lua', 'definition = create_UIBox_main_menu_buttons()', 45, 85)
show_context('functions/common_events.lua', 'G.MAIN_MENU_UI', 25, 55)
show_context('game.lua', 'G.MAIN_MENU_UI', 20, 55)

print('\n=== all create_UIBox_main_menu_buttons refs ===')
for name, text in texts.items():
    if 'create_UIBox_main_menu_buttons' in text:
        print(name, text.count('create_UIBox_main_menu_buttons'))

ui = texts.get('functions/UI_definitions.lua', '')
print('\n=== button marker ===')
print('marker count', ui.count('octopus_multiplayer_button'))
print('definition count', ui.count('function create_UIBox_main_menu_buttons()'))
