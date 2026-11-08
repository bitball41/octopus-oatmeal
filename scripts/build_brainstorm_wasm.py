#!/usr/bin/env python3
"""Build brainstorm/immolate.wasm: Brainstorm Rerolled's Immolate seed searcher
for the browser, from the pinned vendor/BrainstormRerolled.zip.

Needs clang/wasm-ld 18 and a wasm32-wasi sysroot with libc++ (Ubuntu:
apt-get install wasi-libc libc++-18-dev-wasm32 libc++abi-18-dev-wasm32
libclang-rt-18-dev-wasm32). Floating point is compiled exactly as the native
library is (no fast-math, no FMA contraction), so predictions match the game.
"""
import hashlib, io, json, os, subprocess, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT/'scripts/brainstorm_wasm'
OUT = ROOT/'brainstorm/immolate.wasm'
SOURCES = ['functions', 'items', 'rng', 'seed', 'util', 'filters', 'prefilter',
           'scan', 'fastscan', 'filterprog']
CXX = os.environ.get('CXX_WASM', 'clang++-18' if subprocess.run(['which', 'clang++-18'], capture_output=True).returncode == 0 else 'clang++')
LIBCXX = os.environ.get('WASM_LIBCXX_INCLUDE', '/usr/lib/llvm-18/include/wasm32-wasi/c++/v1')
FLAGS = ['--target=wasm32-wasi', '--sysroot=/usr', '-nostdinc++', '-isystem', LIBCXX,
         '-std=c++17', '-O3', '-ffp-contract=off', '-fno-fast-math', '-fno-exceptions',
         '-DIMMOLATE_VERSION="2.0.0"']


def main():
    spec = json.loads((ROOT/'vendor/upstream.json').read_text())['BrainstormRerolled']
    blob = (ROOT/'vendor'/spec['archive']).read_bytes()
    assert hashlib.sha256(blob).hexdigest() == spec['sha256'], 'BrainstormRerolled checksum mismatch'
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            for name in z.namelist():
                if name.startswith('Immolate/src/'):
                    (temp/name).parent.mkdir(parents=True, exist_ok=True)
                    (temp/name).write_bytes(z.read(name))
        src = temp/'Immolate/src'
        objects = []
        for name in SOURCES:
            obj = temp/f'{name}.o'
            subprocess.run([CXX, *FLAGS, '-c', str(src/f'{name}.cpp'), '-o', str(obj)], check=True)
            objects.append(str(obj))
        obj = temp/'wasm_api.o'
        # The shim directory comes first so brainstorm_api.cpp gets the
        # single-threaded <thread>/<mutex> stand-ins.
        flags = FLAGS[:3] + ['-isystem', str(HERE/'shim')] + FLAGS[3:]
        subprocess.run([CXX, *flags, '-I', str(src),
                        '-c', str(HERE/'wasm_api.cpp'), '-o', str(obj)], check=True)
        objects.append(str(obj))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([CXX, '--target=wasm32-wasi', '--sysroot=/usr', '-mexec-model=reactor',
                        '-O3', '-Wl,--strip-all', '-Wl,--gc-sections', *objects,
                        '-lc++', '-lc++abi', '-o', str(OUT)], check=True)
    print(OUT, OUT.stat().st_size, 'bytes')


if __name__ == '__main__':
    main()
