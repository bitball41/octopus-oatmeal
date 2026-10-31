#!/usr/bin/env python3
"""Build Fish and Chips + Potato Patch Utils as an isolated browser mode.

Upstream sources are pinned to commits. The existing preset archives and
rendering / smoothing settings are not changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import build_upstream as browser

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "APotatoPatchUtils": (
        "https://github.com/Balatro-Potato-Patch/Potato-Patch-Utils",
        "c1df6cda90703d3408002d95a57de8b36abf152d",
        "PotatoPatchUtils",
    ),
    "FishAndChips": (
        "https://github.com/Balatro-Potato-Patch/Fish-and-Chips",
        "0ca961ed80240dc0d58b86ff4c7fa62f995b6520",
        "FishAndChips",
    ),
}


def download_sources(lock):
    cache = ROOT / "build" / "fish-sources"
    cache.mkdir(parents=True, exist_ok=True)
    for name, (url, commit, folder) in SOURCES.items():
        archive = cache / (name + ".zip")
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            subprocess.run(["git", "-C", tmp, "fetch", "--depth=1", url, commit],
                           check=True, stdout=subprocess.DEVNULL)
            fetched = subprocess.check_output(
                ["git", "-C", tmp, "rev-parse", "FETCH_HEAD"], text=True).strip()
            if fetched != commit:
                raise RuntimeError(f"{name}: fetched {fetched}, expected {commit}")
            subprocess.run(["git", "-C", tmp, "archive", "--format=zip",
                            "--output=" + str(archive), commit], check=True)
        lock[name] = {
            "archive": "../build/fish-sources/" + archive.name,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        }
        browser.MOD_FOLDERS[name] = folder
        print(f"Pin {name}: {commit}")


def build(release=False, candidate=False):
    lock = json.loads((ROOT / "vendor" / "upstream.json").read_text())
    lock["Steamodded"] = lock["SteamoddedCryptid"]  # v26.829.0
    download_sources(lock)
    files, report = browser.build_smods_pack(
        ["Steamodded", "APotatoPatchUtils", "FishAndChips"],
        "fish-and-chips", ("browser/menu.lua",), lock,
    )
    # Optional integration with DebugPlus should not require DebugPlus itself.
    for row in report:
        if row["status"] == "missing-target" and "debugplus" in row["target"].lower():
            row.update(status="not-applicable", reason="DebugPlus is optional")
    browser.summarize_report(report, "fish-and-chips",
                             "patch-report-fish-and-chips.json", candidate)
    return browser.emit_archive(
        files, ROOT / "build" / "fish-and-chips", (ROOT / "game.js").read_text(),
        ROOT / "fish-and-chips" if release else None,
        part_size=10 * 1024 * 1024,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--release", action="store_true")
    cli.add_argument("--candidate", action="store_true",
                     help="Diagnostic only: allow patch mismatches; do not publish.")
    opts = cli.parse_args()
    if opts.candidate and opts.release:
        cli.error("--candidate and --release cannot be combined")
    build(release=opts.release, candidate=opts.candidate)
