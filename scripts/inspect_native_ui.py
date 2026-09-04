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
    m = re.search(pattern, text, re.M)
    if not m:
        print("NOT FOUND")
        return
    lines = text.splitlines()
    line_no = text[:m.start()].count("\n")
    lo = max(0, line_no - before)
    hi = min(len(lines), line_no + after)
    for i in range(lo, hi):
        print(f"{i+1:05d}: {lines[i]}")

show("create_UIBox_main_menu_buttons", ui, r"function\s+create_UIBox_main_menu_buttons\s*\(", 4, 150)
show("UIBox_button helper", ui, r"function\s+UIBox_button\s*\(", 4, 90)
show("create_UIBox_generic_options", ui, r"function\s+create_UIBox_generic_options\s*\(", 4, 100)
show("create_text_input definition", ui, r"function\s+create_text_input\s*\(", 4, 55)
show("select_text_input callback", buttons, r"G\.FUNCS\.select_text_input\s*=\s*function", 5, 80)
