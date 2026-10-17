#!/usr/bin/env python3
"""Fetch the exact public source snapshots used by the Cryptid browser build."""
import hashlib
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def archive_checkout(checkout, commit, destination):
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', '-z', commit], cwd=checkout).decode().split('\0')
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(filter(None, paths)):
            data = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=checkout)
            info = zipfile.ZipInfo(path, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)


def main():
    lock = json.loads((ROOT/'vendor/upstream.json').read_text())
    for name in ('SteamoddedCryptid', 'Amulet', 'Cryptid'):
        spec = lock[name]
        destination = ROOT/'vendor'/spec['archive']
        if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() == spec['sha256']:
            continue
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run(['git', 'init', '-q', temp], check=True)
            subprocess.run(['git', '-C', temp, 'fetch', '-q', '--depth=1', spec['url'], spec['commit']], check=True)
            candidate = Path(temp)/'source.zip'
            archive_checkout(temp, spec['commit'], candidate)
            assert hashlib.sha256(candidate.read_bytes()).hexdigest() == spec['sha256'], name + ' checksum mismatch'
            destination.write_bytes(candidate.read_bytes())
        print('Fetched', name, spec['commit'])


if __name__ == '__main__':
    main()
