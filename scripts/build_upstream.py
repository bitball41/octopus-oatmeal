#!/usr/bin/env python3
"""Apply pinned upstream Lovely manifests offline to the browser's LÖVE archive.

Lovely v0.9 pattern/regex semantics are implemented here, without a native DLL.
Sources and patch counts are retained so a failed injection cannot look successful.
The shipped archive is only replaced explicitly after runtime validation.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import tomllib
import zipfile
from pathlib import Path
from browser_adapters import adapt_sources
from patch_compatibility import adapt_patch
from patch_multiplayer import patch_game_js

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "83b8a60f09cb833475e825a27c48b1acdc872ba7"
BASE_SHA256 = "aa20c806941b7d3eadd225f7ff8e1f2dd0ba48f98154cbad3ee191a375eecef8"


def unpack(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {n: z.read(n) for n in z.namelist() if not n.endswith('/')}


def browser_base():
    blob = subprocess.check_output(['git', 'show', BASE_COMMIT + ':game.data'], cwd=ROOT)
    assert hashlib.sha256(blob).hexdigest() == BASE_SHA256, 'Browser base checksum mismatch'
    files = unpack(blob)
    # Remove the superseded custom rules, preserving the independent text-input fix.
    files.pop('octopus_multiplayer.lua')
    for name, data in list(files.items()):
        if not name.endswith('.lua'):
            continue
        text = data.decode().replace('\r\n', '\n')
        text = re.sub(r'^.*(?:local OCTOPUS_MP =|OCTOPUS_MP\.(?:init|install_callbacks|update|on_hand_scored|on_round_end|on_run_start)\().*\n', '', text, flags=re.M)
        text = text.replace('if OCTOPUS_MP.should_end_round() then',
                            'if G.GAME.chips - G.GAME.blind.chips >= 0 or G.GAME.current_round.hands_left < 1 then')
        text = re.sub(r'^.*UIBox_button\{id = \'octopus_multiplayer_button\'.*\n', '', text, flags=re.M)
        text = text.replace("id = 'octopus_native_main_menu', ", '')
        # Browser numeric labels pin English explicitly. Upstream replaces
        # these labels and uses the current language's normal font selection.
        text = text.replace("lang = G.LANGUAGES['en-us'], ", '')
        if name == 'game.lua':
            start = text.index('function Game:init_item_prototypes()')
            end = text.index('\nfunction ', start+1)
            block = re.sub(r'(self\.(\w+) = )self\.\2 or (\{)', r'\1\3', text[start:end])
            text = text[:start] + block + text[end:]
        if name == 'card.lua':
            # This browser base accidentally nests Glass Joker's same event
            # twice. Restore the stock single event before SMODS replaces it.
            start = text.index('local glass_cards = 0')
            end = text.index('elseif context.using_consumeable then', start)
            block = text[start:end]
            event = r'G\.E_MANAGER:add_event\(Event\(\{\s+func = function\(\)\s+'
            block, count = re.subn('(' + event + ')(' + event + ')', r'\2', block, count=1)
            assert count == 1, 'Browser Glass Joker wrapper changed'
            block, count = re.subn(r"(card_eval_status_text\(self, 'extra', [^\n]+\n)\s+return true\s+end\s+\}\)\)", r'\1', block, count=1)
            assert count == 1, 'Browser Glass Joker wrapper tail changed'
            text = text[:start] + block + text[end:]
        files[name] = text.encode()
    return files


def interpolate(template, match):
    def sub(m):
        key = m[1] or m[2]
        if key is None:
            return '$'
        try:
            return match[int(key) if key.isdigit() else key] or ''
        except (IndexError, KeyError):
            return ''
    return re.sub(r'\$\{(\w+)\}|\$(\w+)|\$\$', sub, template)


def patch_pattern(text, patch):
    patterns = [re.compile('^' + re.escape(line.strip()).replace(r'\*', '.*').replace(r'\?', '.') + '$')
                for line in patch['pattern'].splitlines()]
    lines = text.splitlines(keepends=True)
    matches, i = [], 0
    while i <= len(lines) - len(patterns):
        if all(p.fullmatch(line.strip()) for p, line in zip(patterns, lines[i:i+len(patterns)])):
            matches.append(i)
            i += len(patterns)
        else:
            i += 1
    count = len(matches)
    for i in reversed(matches[:patch.get('times', count)]):
        indent = re.match(r'[ \t]*', lines[i])[0] if patch.get('match_indent') else ''
        payload = ''.join(indent + line for line in patch['payload'].splitlines(keepends=True))
        if not payload.endswith('\n'):
            payload += '\n'
        start, end = i, i + len(patterns)
        if patch['position'] == 'before': end = start
        if patch['position'] == 'after': start = end
        lines[start:end] = [payload]
    return ''.join(lines), count


def patch_regex(text, patch):
    pattern = re.sub(r'\(\?<([A-Za-z_]\w*)>', r'(?P<\1>', patch['pattern'])
    matches = list(re.finditer(pattern, text, re.M))
    count = len(matches)
    root = patch.get('root_capture', '0').replace('$', '')
    root = int(root) if root.isdigit() else root
    for match in reversed(matches[:patch.get('times', count)]):
        start, end = match.span(root)
        prepend = interpolate(patch.get('line_prepend', ''), match)
        payload = interpolate(''.join(prepend + line for line in patch['payload'].splitlines(keepends=True)), match)
        if patch['position'] == 'before': end = start
        if patch['position'] == 'after': start = end
        if payload and re.match(r'\w', payload[0]) and start and re.match(r'\w', text[start-1]): payload = ' ' + payload
        if payload and re.match(r'\w', payload[-1]) and end < len(text) and re.match(r'\w', text[end]): payload += ' '
        text = text[:start] + payload + text[end:]
    return text, count


def build(candidate=False, release=False):
    files = browser_base()
    lock = json.loads((ROOT/'vendor/upstream.json').read_text())
    manifests, modules, early = [], {}, []
    for mod in ['Steamodded', 'Multiplayer']:
        spec = lock[mod]
        blob = (ROOT/'vendor'/spec['archive']).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == spec['sha256'], f'{mod} checksum mismatch'
        source = unpack(blob)
        prefix = f'Mods/{mod}/'
        for name, data in source.items():
            files[prefix + name] = data.replace(b'\r\n', b'\n') if name.endswith('.lua') else data
            if name.startswith('lovely/') and name.endswith('.toml'):
                manifest = tomllib.loads(data.decode())
                manifests.append((manifest['manifest'].get('priority', 0), mod, name, manifest))
                for patch in manifest.get('patches', []):
                    if 'module' in patch:
                        p = patch['module']
                        modules[p['name']] = prefix + p['source']
                        if p.get('load_now'): early.append(p['name'])

    def target_path(target):
        if target in files: return target
        m = re.fullmatch(r'=\[SMODS (_|\w+) "([^"]+)"\]', target)
        if m: return f'Mods/{"Steamodded" if m[1] == "_" else m[1]}/{m[2]}'
        m = re.fullmatch(r'=\[lovely ([^ ]+) "([^"]+)"\]', target)
        if m: return modules.get(m[1], target)
        if target.endswith('.fs'): return 'resources/shaders/' + target
        return target

    report = []
    for _, mod, name, manifest in sorted(manifests, key=lambda x: x[:3]):
        for index, item in enumerate(manifest.get('patches', []), 1):
            kind, patch = next(iter(item.items()))
            if kind == 'module': continue
            target = target_path(patch['target'])
            row = dict(mod=mod, manifest=name, index=index, target=target, kind=kind)
            patch, skip_reason = adapt_patch(mod, name, index, patch, files.get(target,b'').decode() if target.endswith('.lua') else '')
            if skip_reason:
                row.update(status='not-applicable', matches=0, reason=skip_reason)
            elif target not in files:
                row.update(status='missing-target', matches=0)
            elif kind == 'copy':
                payload = b'\n'.join(files[f'Mods/{mod}/'+p] for p in patch['sources']) + b'\n'
                files[target] = payload + files[target] if patch['position']=='prepend' else files[target] + b'\n' + payload
                row.update(status='applied', matches=1)
            else:
                patch = dict(patch)
                if mod == 'Steamodded' and name == 'lovely/scaling.toml' and index == 29:
                    # better_calc inserts this return before scaling runs. Move
                    # it after the replacement effect instead of emitting code
                    # after return (invalid on both Lua 5.1 and LuaJIT).
                    patch['pattern'] = patch['pattern'].replace('}))\ncard_eval', '}))\nreturn nil, true\ncard_eval')
                    patch['payload'] += '\nreturn nil, true\n'
                patch['payload'] = patch['payload'].replace('{{lovely_hack:patch_dir}}', f'Mods/{mod}')
                operation = patch_pattern if kind == 'pattern' else patch_regex
                source_text = files[target].decode()
                scoped_function = None
                if mod == 'Steamodded' and name == 'lovely/loader.toml':
                    # Browser save_progress repeats this desktop anchor. The
                    # discovery snapshot belongs only to prototype initialization.
                    scoped_function = 'function Game:init_item_prototypes()'
                if mod == 'Multiplayer' and name == 'lovely/decks.toml' and index == 2:
                    scoped_function = 'function ease_dollars('
                if scoped_function:
                    begin = source_text.index(scoped_function)
                    end = source_text.index('\nfunction ', begin + 1)
                    scoped, count = operation(source_text[begin:end], patch)
                    text = source_text[:begin] + scoped + source_text[end:]
                else:
                    text, count = operation(source_text, patch)
                files[target] = text.encode()
                status = 'applied' if count and ('times' not in patch or count == patch['times']) else 'mismatch'
                row.update(status=status, matches=count, expected=patch.get('times'), pattern=patch['pattern'])
            report.append(row)

    adapt_sources(files)
    for module, path in modules.items():
        files[module.replace('.', '/')+'.lua'] = files[path]
    for path in (ROOT/'browser/lua').rglob('*.lua'):
        files[path.relative_to(ROOT/'browser/lua').as_posix()] = path.read_bytes()
    files['main.lua'] = (b'require "browser.platform"\n' +
                         ''.join(f'require "{m}"\n' for m in early).encode() + files['main.lua'])
    out = ROOT/'build'; out.mkdir(exist_ok=True)
    (out/'patch-report.json').write_text(json.dumps(report, indent=2)+'\n')
    failures = [r for r in report if r['status'] not in ('applied','not-applicable')]
    skipped = sum(r['status']=='not-applicable' for r in report)
    print(f'{len(report)-len(failures)-skipped} patch operations applied; {skipped} explicitly not applicable; {len(failures)} unresolved')
    if failures and not candidate:
        raise RuntimeError('Unresolved upstream patch operations; see build/patch-report.json')
    candidate_path = out/'game.data'
    with zipfile.ZipFile(candidate_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026,1,1,0,0,0)); info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    if release:
        blob = candidate_path.read_bytes()
        (ROOT/'game.data').write_bytes(blob)
        (ROOT/'game.js').write_text(patch_game_js(blob), encoding='utf-8')
        print(ROOT/'game.data')
    else:
        print(candidate_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', action='store_true', help='Emit a diagnostic candidate even with unresolved patches; never ship this output')
    parser.add_argument('--release', action='store_true', help='Replace game.data and update game.js after strict validation')
    args = parser.parse_args()
    build(args.candidate, args.release)
