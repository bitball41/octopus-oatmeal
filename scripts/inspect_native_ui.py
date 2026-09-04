#!/usr/bin/env python3
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "game.data"

with zipfile.ZipFile(DATA, "r") as z:
    files = {name: z.read(name).decode("utf-8", "ignore") for name in z.namelist() if name.endswith(".lua")}


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

ui = files["functions/UI_definitions.lua"]
buttons = files["functions/button_callbacks.lua"]
show("create_UIBox_main_menu_buttons", ui, r"function\s+create_UIBox_main_menu_buttons\s*\(", 4, 150)
show("create_text_input definition", ui, r"function\s+create_text_input\s*\(", 4, 55)
show("select_text_input callback", buttons, r"G\.FUNCS\.select_text_input\s*=\s*function", 5, 110)

for needle in (r"function\s+love\.keypressed", r"love\.keypressed\s*=", r"text_input_hook", r"love\.textinput", r"text_input_key"):
    print(f"\n===== occurrences: {needle} =====")
    for name, text in files.items():
        if re.search(needle, text):
            print(name)
            for m in list(re.finditer(needle, text))[:4]:
                lines = text.splitlines()
                line_no = text[:m.start()].count("\n")
                lo = max(0, line_no - 8)
                hi = min(len(lines), line_no + 24)
                for i in range(lo, hi):
                    print(f"{i+1:05d}: {lines[i]}")
                print("---")
