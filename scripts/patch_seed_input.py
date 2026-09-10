#!/usr/bin/env python3
"""Restore browser text input in the single-player archive and refresh its cache key."""
import hashlib
import io
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(source, old, new):
    if new in source:
        return source
    assert source.count(old) == 1, f"Expected one patch anchor: {old!r}"
    return source.replace(old, new, 1)


def patch(name, source):
    if name == 'main.lua':
        handler = '''function love.textinput(text)
    if type(text) ~= 'string' or not (G and G.CONTROLLER and
        G.CONTROLLER.text_input_hook and G.FUNCS and G.FUNCS.text_input_key) then return end
    -- SDL supplies printable text; keypressed keeps editing/navigation keys.
    for i = 1, #text do
        if not G.CONTROLLER.text_input_hook then break end
        local c = text:sub(i, i)
        if c:byte() >= 32 and c:byte() < 127 then
            G.FUNCS.text_input_key({e = G.CONTROLLER.text_input_hook,
                key = c, caps = false, browser_text = true})
        end
    end
end

'''
        return replace_once(source, 'function love.keyreleased(key)',
                            handler + 'function love.keyreleased(key)')
    if name == 'engine/controller.lua':
        return replace_once(source, '    if self.text_input_hook then\n        if key == "escape" then',
                            '    if self.text_input_hook then\n'
                            "        if #key == 1 or key == 'space' then return end\n"
                            '        if key == "escape" then')
    if name == 'functions/button_callbacks.lua':
        return replace_once(source,
                            '  args.caps = args.caps or G.CONTROLLER.capslock or hook_config.all_caps',
                            '  args.caps = (not args.browser_text and (args.caps or G.CONTROLLER.capslock)) or hook_config.all_caps')
    return source


def main():
    output = io.BytesIO()
    with zipfile.ZipFile(ROOT / 'game.data') as original, zipfile.ZipFile(output, 'w') as rebuilt:
        for entry in original.infolist():
            data = original.read(entry)
            if entry.filename in ('main.lua', 'engine/controller.lua', 'functions/button_callbacks.lua'):
                data = patch(entry.filename, data.decode('utf-8').replace('\r\n', '\n')).encode('utf-8')
            rebuilt.writestr(entry, data)
    data = output.getvalue()
    (ROOT / 'game.data').write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    loader = (ROOT / 'game.js').read_text()
    loader = re.sub(r'game\.data\?v=[\w-]+', 'game.data?v=' + digest[:12], loader)
    loader = re.sub(r'package_uuid: "[^"]+"', 'package_uuid: "' + digest + '"', loader)
    loader = re.sub(r'remote_package_size: \d+', f'remote_package_size: {len(data)}', loader)
    loader = re.sub(r'end: \d+', f'end: {len(data)}', loader)
    (ROOT / 'game.js').write_text(loader)
    page = ROOT / 'balatro.html'
    page.write_text(re.sub(r'game\.js\?v=[\w-]+', 'game.js?v=' + digest[:12], page.read_text()))
    print(f'Patched archive: {len(data)} bytes, cache key {digest[:12]}')


if __name__ == '__main__':
    main()
