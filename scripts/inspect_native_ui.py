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

show("main menu b_play", ui, r"b_play", 28, 70)
show("main menu b_collection", ui, r"b_collection", 28, 70)
show("main menu b_options", ui, r"b_options", 28, 70)
show("create_text_input definition", ui, r"function\s+create_text_input|create_text_input\s*=", 8, 80)
show("play callback", buttons, r"G\.FUNCS\.[A-Za-z0-9_]*play[A-Za-z0-9_]*\s*=\s*function", 12, 50)
show("collection callback", buttons, r"G\.FUNCS\.[A-Za-z0-9_]*collection[A-Za-z0-9_]*\s*=\s*function", 12, 50)
show("options callback", buttons, r"G\.FUNCS\.[A-Za-z0-9_]*options[A-Za-z0-9_]*\s*=\s*function", 12, 50)
show("overlay_menu call", buttons, r"G\.FUNCS\.overlay_menu|overlay_menu\s*\(", 12, 70)

print("\n===== candidate menu functions =====")
for m in re.finditer(r"function\s+([A-Za-z0-9_\.]+)\s*\([^)]*\)|([A-Za-z0-9_\.]+)\s*=\s*function\s*\([^)]*\)", ui):
    name = m.group(1) or m.group(2)
    if any(k in name.lower() for k in ("main", "menu", "button", "options", "collection")):
        print(name)
