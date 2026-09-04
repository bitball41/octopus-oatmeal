#!/usr/bin/env python3
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "game.data"

with zipfile.ZipFile(DATA, "r") as z:
    ui = z.read("functions/UI_definitions.lua").decode("utf-8")
    buttons = z.read("functions/button_callbacks.lua").decode("utf-8")


def show(label, text, pattern, before=12, after=28):
    print(f"\n===== {label} =====")
    m = re.search(pattern, text, re.I | re.M)
    if not m:
        print("NOT FOUND")
        return
    lines = text.splitlines()
    line_no = text[:m.start()].count("\n")
    lo = max(0, line_no - before)
    hi = min(len(lines), line_no + after)
    for i in range(lo, hi):
        print(f"{i+1:05d}: {lines[i]}")

show("main menu function around PLAY", ui, r"PLAY|b_play|main_menu")
show("collection/options row", ui, r"collection|options", 18, 45)
show("create_text_input definition", ui, r"function\s+create_text_input|create_text_input\s*=", 8, 80)
show("overlay menu callback example", buttons, r"G\.FUNCS\.(options|collection|settings|exit_overlay_menu)|overlay_menu", 12, 50)

print("\n===== candidate UIDEF functions =====")
for m in re.finditer(r"function\s+G\.UIDEF\.([A-Za-z0-9_]+)|G\.UIDEF\.([A-Za-z0-9_]+)\s*=\s*function", ui):
    name = m.group(1) or m.group(2)
    if any(k in name.lower() for k in ("main", "menu", "settings", "profile", "options", "tab")):
        print(name)
