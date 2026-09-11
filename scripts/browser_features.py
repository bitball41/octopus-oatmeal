"""Install browser-only input features and the repository's exact joker order."""
import json
import re
from pathlib import Path
from browser_adapters import once
ROOT = Path(__file__).resolve().parents[1]

def apply(files, vanilla=False):
    if not vanilla:
        text = files['game.lua'].decode()
        text = once(text,
                    "G.SETTINGS.tutorial_complete = get_cloud_flag('tutorial_complete')",
                    "G.SETTINGS.tutorial_complete = true\n    G.SETTINGS.tutorial_progress = nil",
                    'modded main menu tutorial skip')
        text = once(text, 'function Game:start_run(args)',
                    'function Game:start_run(args)\n'
                    '    G.SETTINGS.tutorial_complete = true\n'
                    '    G.SETTINGS.tutorial_progress = nil',
                    'modded run tutorial skip')
        files['game.lua'] = text.encode()
    # The bundled runtime is WebGL 1: upstream enables mipmaps on NPOT atlases,
    # which fails during splash/menu creation on conforming browsers.
    for name in ('game.lua', 'Mods/Steamodded/src/game_object.lua'):
        if name not in files:
            continue
        text = files[name].decode()
        text = re.sub(r'mipmaps\s*=\s*true', 'mipmaps = false', text)
        text = re.sub(r"^([^\n]*:setMipmapFilter\([^\n]*)$", r'-- WebGL 1: \1', text, flags=re.M)
        files[name] = text.encode()
    name = 'Mods/Steamodded/src/game_object.lua'
    if name in files:
        text = files[name].decode()
        text = once(text, "            if prev_path then G.SOUND_MANAGER.channel:push({ type = 'stop' }) end",
            "            if not G.F_SOUND_THREAD then\n"
            "                SOURCES[self.sound_code] = {}\n"
            "                return\n"
            "            end\n"
            "            if prev_path then G.SOUND_MANAGER.channel:push({ type = 'stop' }) end", 'browser sound registration')
        files[name] = text.encode()
    name = 'functions/misc_functions.lua'
    text = files[name].decode()
    text = once(text, '''  local s = {sound = love.audio.newSource("resources/sounds/"..args.sound_code..'.ogg', should_stream and "stream" or 'static')}''',
        "  local custom = SMODS and SMODS.Sounds[args.sound_code]\n"
        "  local path = custom and custom.full_path or (\"resources/sounds/\"..args.sound_code..'.ogg')\n"
        "  local s = {sound = love.audio.newSource(path, should_stream and 'stream' or 'static')}", 'browser custom sound playback')
    files[name] = text.encode()
    reference = (ROOT / '148 jokers.HTML').read_text()
    rows = json.loads(re.search(r'const a=(\[.*?\]);', reference).group(1))
    keys = [r[2] for r in rows]
    assert len(keys) == len(set(keys)) == 148
    assert 'j_ceremonial' not in keys and 'j_madness' not in keys
    assert 'j_rough_gem' in keys
    files['browser/joker_order.lua'] = ('return {' + ','.join(json.dumps(k) for k in keys) + '}\n').encode()
    text = files['main.lua'].decode()
    text = once(text, 'function love.keypressed(key)',
                'function love.keypressed(key)\n    require("browser.cheats").keypressed(key)', 'cheat keyboard hook')
    if vanilla:
        text = once(text, 'function love.update( dt )',
                    'function love.update( dt )\n    require("browser.clipboard").poll()',
                    'vanilla clipboard poll')
    files['main.lua'] = text.encode()
    text = files['functions/button_callbacks.lua'].decode()
    start = text.index('G.FUNCS.paste_seed = function(e)')
    end = text.index('\nend', start) + len('\nend')
    text = text[:start] + 'G.FUNCS.paste_seed = function(e)\n  require("browser.clipboard").request(e)\nend' + text[end:]
    files['functions/button_callbacks.lua'] = text.encode()
