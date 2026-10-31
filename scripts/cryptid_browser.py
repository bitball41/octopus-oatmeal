"""Compatibility for Cryptid 0.5.17c / Amulet 3.6.1 / Steamodded 26.829.0.

Native manifests remain pinned and unmodified in vendor/. Every superseded
operation is recorded, and changed browser anchors are explicit.
"""
import re
import json
import subprocess
from pathlib import Path
from browser_adapters import once


def adapt_cryptid_patch(mod, name, index, patch, files, resolve):
    p = dict(patch)
    source = files.get(resolve(p['target']), b'').decode()
    key = (mod, name, index)
    skips = {
        ('Steamodded', 'lovely/blind.toml', 50): 'Browser base already uses blind_on_deck for Small.',
        ('Steamodded', 'lovely/blind.toml', 51): 'Browser base already uses blind_on_deck for Big.',
        ('Cryptid', 'lovely/code.toml', 5): 'Browser renderer disables the desktop CRT pass; no CRT uniform to send.',
        ('Cryptid', 'lovely/ccd.toml', 3): 'Steamodded moved consumable placement to Card:emplace, which supports playing cards.',
        ('Cryptid', 'lovely/ccd.toml', 6): 'Steamodded now assembles edition badges via get_edition; no legacy negative badge branch.',
        ('Cryptid', 'lovely/ccd.toml', 7): 'Steamodded removed the legacy negative-slot override; playing cards use cardarea slot accounting.',
        ('Cryptid', 'lovely/misc.toml', 21): 'Steamodded moved repetition processing into SMODS.calculate_repetitions.',
        ('Cryptid', 'lovely/misc.toml', 43): 'Steamodded 26.829 uses Scoring_Parameter objects and Calculation_Controls, not hand_chips globals.',
        ('Cryptid', 'lovely/misc.toml', 44): 'Steamodded 26.829 uses Scoring_Parameter objects and Calculation_Controls, not mult globals.',
        ('Cryptid', 'lovely/misc.toml', 45): 'Steamodded 26.829 uses Scoring_Parameter objects and Calculation_Controls.',
        ('Cryptid', 'lovely/misc.toml', 46): 'Steamodded 26.829 uses Scoring_Parameter objects and Calculation_Controls.',
        ('Cryptid', 'lovely/misc.toml', 50): 'Steamodded replaced legacy edition hand limits with card_limits accounting.',
        ('Cryptid', 'lovely/misc.toml', 51): 'Steamodded replaced legacy edition draw limits with ability.card_limit accounting.',
        ('Cryptid', 'lovely/stake.toml', 11): 'Browser base already checks ante >= win_ante and blind_on_deck Boss.',
        ('Cryptid', 'lovely/stake.toml', 12): 'Browser base already uses blind_on_deck Small.',
        ('Cryptid', 'lovely/stake.toml', 13): 'Browser base already uses blind_on_deck Big.',
        ('Amulet', 'lovely/noanims.toml', 1): 'Steamodded owns effect animations via trigger_effects; old scoring loop was replaced.',
        ('Amulet', 'lovely/typefix.toml', 4): 'Steamodded scoring parameter delta already uses is_number(vals[name]).',
        ('Amulet', 'lovely/typefix.toml', 5): 'Steamodded scoring parameter delta already uses is_number(vals[name]).',
        ('Amulet', 'lovely/talisman-detection-after.toml', 1): 'Only Amulet is bundled; the optional conflicting-Talisman marker is absent.',
        ('Amulet', 'lovely/talisman-detection-after.toml', 2): 'Only Amulet is bundled; do not install the Talisman conflict error.',
        ('Cryptid', 'lovely/cat.toml', 10): 'Browser metadata uses decoded G.FILES; Cryptid save loading is adapted below.',
        ('Cryptid', 'lovely/cat.toml', 11): 'Browser metadata uses decoded G.FILES; shiny tag loading is adapted below.',
    }
    if mod == 'Steamodded' and name.startswith('lovely/glsl_es_patches/'):
        return p, 'Native LÖVE shader-wrapper patch target is absent in love.js; browser shader adaptation runs at build time.'
    if key in skips:
        return p, skips[key]

    anchors = {
        ('Steamodded', 'lovely/run_select.toml', 4): 'if self.hovering.target and self.hovering.target == self.dragging.target then',
        ('Cryptid', 'lovely/lib_gameset.toml', 3): '--self:load_profile(G.SETTINGS.profile or 1)',
        ('Cryptid', 'lovely/stake.toml', 1): "if not G.GAME.won and G.GAME.round_resets.ante >= G.GAME.win_ante and G.GAME.blind_on_deck == 'Boss' then",
        ('Cryptid', 'lovely/Ascended.toml', 8): "check_and_set_high_score('hand',  SMODS.calculate_round_score() )",
        ('Cryptid', 'lovely/abstracted.toml', 12): 'elseif no_rank then',
    }
    if key in anchors:
        p['pattern'] = anchors[key]
    if key == ('Cryptid', 'lovely/lib_gameset.toml', 3):
        p['payload'] += '''
G.SETTINGS.profile_counters = G.SETTINGS.profile_counters or {}
for i = 1, 3 do
    local profile = Cryptid.profile_prefix .. i
    G.SETTINGS.profile_counters[profile] = G.SETTINGS.profile_counters[profile] or 0
end
'''
    if key == ('Steamodded', 'lovely/ui.toml', 43):
        p['pattern'] = p['pattern'].replace('colours = {G.C.MONEY}', "font = G.LANGUAGES['en-us'].font, colours = {G.C.MONEY}")
    if key == ('Cryptid', 'lovely/lib_gameset.toml', 1):
        p['pattern'] = p['pattern'].replace('args.center or', 'args.center and G.P_CENTERS[args.center] or')
        p['payload'] = p['payload'].replace('args.center or', 'args.center and G.P_CENTERS[args.center] or')
    if key == ('Cryptid', 'lovely/lib_gameset.toml', 2):
        p['pattern'] = 'colours = {args.particle_colours and args.particle_colours[1] or G.C.RED, args.particle_colours and args.particle_colours[2] or G.C.BLUE, args.particle_colours and args.particle_colours[3] or G.C.ORANGE},'
        p['payload'] = p['pattern'].replace('or G.C.RED', 'or G.C.CRY_EXOTIC').replace('or G.C.ORANGE', 'or G.C.CRY_JOLLY')
    if key == ('Cryptid', 'lovely/lib_misc.toml', 15):
        p['pattern'] = 'self.full_path = NFS.getNormalizedPath((self.path_mod or self.mod or SMODS).path ..'
        p['payload'] = 'self.full_path = NFS.getNormalizedPath((self.mod_path or (self.path_mod or self.mod or SMODS).path) ..'
    if key == ('Cryptid', 'lovely/lib_ui.toml', 2):
        p['pattern'] = 'if self.debuff and not self.delay_debuff then'
        p['payload'] = p['payload'].replace('if self.debuff or', 'if (self.debuff and not self.delay_debuff) or')
    if key == ('Cryptid', 'lovely/lib_ui.toml', 3):
        p['pattern'] = "if (self.edition and self.edition.negative and (not self.delay_edition or self.delay_edition.negative)) or (self.ability.name == 'Antimatter' and (self.config.center.discovered or self.bypass_discovery_center)) then"
        p['payload'] = p['pattern'].replace('self.edition.negative and', '(self.edition.negative or self.edition.cry_oversat) and')
    if key == ('Cryptid', 'lovely/lib_ui.toml', 5):
        p['target'] = '=[SMODS _ "src/utils.lua"]'
        p['pattern'] = 'detailed_tooltip = T and (G.P_CENTERS[T.key] or G.P_TAGS[T.key] or T) or nil'
        p['payload'] = 'detailed_tooltip = T and (Cryptid.get_center(T.key) or G.P_CENTERS[T.key] or G.P_TAGS[T.key] or T) or nil'
    if key == ('Cryptid', 'lovely/misc.toml', 30):
        p['pattern'] = 'while eff.retrigger_flag do'
        p['payload'] = 'while eff.retrigger_flag and reps[j+1] ~= nil do'
    if key == ('Cryptid', 'lovely/misc.toml', 41):
        p['pattern'] = "return val and (val >= 0 and '+'..val or ''..val) or '+0'"
        p['payload'] = "return val and (to_big(val) >= to_big(0) and '+'..number_format(val) or number_format(val)) or '+0'"
    if key == ('Cryptid', 'lovely/misc.toml', 42):
        p['pattern'] = "return val and sign..'$'..math.abs(val) or '$0'"
        p['payload'] = "return val and sign..'$'..number_format(math.abs(val)) or '$0'"
    if mod == 'Cryptid' and name == 'lovely/misprint.toml' and index in (34,35,36,37,40,41):
        voucher = re.search(r'v_\w+\s*=', p['pattern'])[0].split('=')[0].strip()
        p['pattern'] = next(line.strip() for line in source.splitlines() if line.strip().startswith(voucher+'=') or line.strip().startswith(voucher+' ='))
    if key == ('Cryptid', 'lovely/stake.toml', 7):
        p['pattern'] = p['pattern'].replace('and G.GAME.current_round', 'and not context.full_hand[1].sixth_sense and G.GAME.current_round')
        p['payload'] = p['payload'].replace('and G.GAME.current_round', 'and not context.full_hand[1].sixth_sense and G.GAME.current_round')
    if key == ('Amulet', 'lovely/noanims.toml', 4):
        p['pattern'] = 'if G.GAME.blind and G.GAME.blind.in_blind and not self.from_quantum then G.E_MANAGER:add_event(Event({ func = function() G.GAME.blind:set_blind(nil, true, nil); return true end })) end'
        p['payload'] = p['payload'].replace('and not Talisman', 'and not self.from_quantum and not Talisman')
    if key == ('Amulet', 'lovely/noanims.toml', 9):
        # The browser already guards juice_up on an optional card.
        if p['pattern'] not in source:
            return p, 'Browser juice_card_until already checks card/juice_up before animation.'
    if key == ('Cryptid', 'lovely/none.toml', 1):
        p['target'] = 'functions/UI_definitions.lua'
        p['pattern'] = p['pattern'].splitlines()[0]
        p['payload'] = p['pattern'].replace('one_press = true, ', '')
    if key == ('Cryptid', 'lovely/none.toml', 2):
        return p, 'Steamodded replaces planet use with bulk level-up and update_hand_text; browser selection refresh is installed below.'
    if mod == 'Amulet' and name == 'lovely/numfmt.toml' and index in (4,5) and p['payload'].strip() in source:
        return p, 'Browser hand labels already use number_format with the same 1000000 threshold.'
    if key == ('Cryptid', 'lovely/cat.toml', 5):
        p['pattern'] = next(line.strip() for line in source.splitlines() if 'local tag_sprite = SMODS.create_sprite(' in line)
        prefix = p['payload'].split('local tag_sprite =')[0]
        p['payload'] = prefix + p['pattern'].replace('SMODS.get_atlas((not self.hide_ability) and G.P_TAGS[self.key].atlas or "tags")', 'tagatlas')
    if key == ('Amulet', 'lovely/fixes.toml', 3):
        # The browser's coin animation cap already uses a bounded Lua number.
        return p, 'Browser dollar display is capped through dollars_to_loop; no 60-dollar desktop loop.'
    if key == ('Amulet', 'lovely/fixes.toml', 9):
        return p, 'Steamodded replaced orbital choice setup with its own tag UI.'
    if key == ('Amulet', 'lovely/fixes.toml', 16):
        p['pattern'] = next(line.strip() for line in source.splitlines() if "id = 'ante_UI_count'" in line)
        p['payload'] = p['pattern'].replace('scale = 2*scale', 'scale = 2*scale, maxw = 0.8')
    return p, None


def atlas_scaling(s):
    s = once(s, 'vec2 neigbours[8] = vec2[8](vec2(-1, -1),vec2(0, -1),vec2(1, -1),vec2(-1, 0),vec2(1, 0),vec2(-1, 1),vec2(0, 1),vec2(1, 1));',
             '// WebGL 1: derive the eight neighbour offsets inside the loop.', 'atlas shader array constructor')
    s = once(s, 'for (int i = 0; i < 8; i++) {',
             'for (int i = 0; i < 9; i++) {\n                if (i == 4) continue;', 'atlas shader neighbour loop')
    s = once(s, 'vec2 c = uv + (neigbours[i] * dim);',
             'vec2 c = uv + vec2(mod(float(i), 3.0)-1.0, floor(float(i)/3.0)-1.0) * dim;', 'atlas shader offsets')
    s = s.replace('c.x < 0 || c.x > 1', 'c.x < 0.0 || c.x > 1.0')
    return s.replace('c.y < 0 || c.y > 1', 'c.y < 0.0 || c.y > 1.0')


def repair_atlas_scaling_shader(files):
    """Steamodded 26.829's atlas scaling shader uses a GLSL 3 array constructor."""
    name = 'Mods/Steamodded/src/game_object.lua'
    files[name] = atlas_scaling(files[name].decode()).encode()


def prepare_cryptid_sources(files):
    def edit(name, fn):
        files[name] = fn(files[name].decode()).encode()

    # Thunderstore's manifest is installer metadata, not a Steamodded mod.
    files.pop('Mods/Amulet/manifest.json', None)
    if 'Mods/Cryptid/Cryptid.lua' in files:
        edit('Mods/Cryptid/lib/content.lua', lambda s: s.replace('mipmaps = true', 'mipmaps = false'))
    repair_atlas_scaling_shader(files)

    # Amulet mounts these directories with LuaJIT FFI on desktop. The same
    # modules live directly in the browser's read-only LÖVE archive instead.
    original_talisman = files['Mods/Amulet/talisman.lua'].decode()
    talisman = original_talisman
    end = talisman.index('require("talisman.configinit")')
    talisman = '-- Amulet modules are pre-mounted in the browser archive.\n' + talisman[end:]
    files['Mods/Amulet/talisman.lua'] = talisman.encode()
    # lovely.copy appended talisman.lua into main.lua before adaptations.
    edit('main.lua', lambda s: once(s, original_talisman, talisman, 'Amulet bootstrap copy'))
    edit('Mods/Amulet/talisman/configinit.lua', lambda s: once(s,
        '    local conf = love.filesystem.read(Talisman.config.file_name)',
        '    if not love.filesystem.getInfo(Talisman.config.file_name) then return end\n'
        '    local conf = love.filesystem.read(Talisman.config.file_name)', 'optional Amulet config read'))
    edit('Mods/Amulet/talisman/break_inf/sanitizer.lua', lambda s: once(s,
        '\tif not Talisman.config_file.enable_compat or not Big then return copy_table_hook(v) end',
        '\tif not Big then return copy_table_hook(v) end', 'table-backed OmegaNum copying'))
    # Lua 5.1 creates an implicit varargs local named `arg`; it shadows
    # Amulet's named shader argument. LuaJIT does not have this collision.
    def shader_argument(s):
        start = s.index('function Shader:send(name, arg, ...)')
        end = s.index('\nlocal lg_translate', start)
        return s[:start] + re.sub(r'\barg\b', 'value', s[start:end]) + s[end:]
    edit('Mods/Amulet/talisman/break_inf/sanitizer.lua', shader_argument)

    # Retain upstream OmegaNum arithmetic; replace only its FFI storage with
    # Lua tables. The defaults mirror zero-initialized C struct fields.
    def omega(s):
        s = s[s.index('local R = require("big-num.constants")'):]
        start = s.index('ffi.cdef[[')
        end = s.index('--OmegaNum port')
        s = s[:start] + '''local function TalismanOmega()
    return setmetatable({asize=0, number=0, sign=0, _nan=false, _inf=false}, OmegaMeta)
end

''' + s[end:]
        s = once(s, '    ffi.copy(n, self, TalismanOmega_sizeof)',
                 '    n.asize, n.number, n.sign = self.asize, self.number, self.sign\n'
                 '    n._nan, n._inf = self._nan, self._inf', 'OmegaNum value copy')
        return once(s, 'ffi.metatype(TalismanOmega, OmegaMeta)', '-- OmegaMeta is assigned by the table constructor.', 'OmegaNum metatype')
    edit('Mods/Amulet/big-num/omeganum.lua', omega)
    for name, data in list(files.items()):
        for directory in ('talisman/', 'big-num/'):
            if name.startswith('Mods/Amulet/'+directory):
                files[name[len('Mods/Amulet/'):]] = data

    # WebGL 1 needs constant loop bounds; retain all 96 Gaussian samples.
    if 'Mods/Cryptid/Cryptid.lua' in files:
        def blur(s):
            s = once(s, 'for (float d = 0.0; d < two_pi; d += d_step) {',
                     'for (int cry_d = 0; cry_d < 16; cry_d++) { float d = float(cry_d) * 0.39269908169875;', 'blur direction loop')
            return once(s, 'for (float i = i_step; i < 1.001; i+=i_step) {',
                        'for (int cry_i = 1; cry_i <= 6; cry_i++) { float i = float(cry_i) / 6.0;', 'blur sample loop')
        edit('Mods/Cryptid/assets/shaders/blur.fs', blur)
    edit('Mods/Steamodded/src/ui.lua', lambda s: once(s,
        'return r.depthstencil and r[1] or r', 'return r and r.depthstencil and r[1] or r', 'window canvas nil guard'))
    files['Mods/Steamodded/src/overrides.lua'] += b'''
-- Refresh None-hand selection after planet use through the current API.
local browser_planet_use = Card.use_consumeable
function Card:use_consumeable(...)
    local result = browser_planet_use(self, ...)
    if self.ability.consumeable and self.ability.consumeable.hand_type and G.hand then
        G.E_MANAGER:add_event(Event({trigger='after', func=function()
            if G.hand and G.GAME.current_round.current_hand.handname ~= '' then
                G.hand:parse_highlighted()
            end
            return true
        end}))
    end
    return result
end
'''

    # The newer API asks NativeFS to normalize paths and return nil for absent
    # atlas alternatives. Limit the extension to this mode's packed adapter.
    files['browser/cryptid_platform.lua'] = b'''local nfs = require 'browser.nativefs'
nfs.getNormalizedPath = function(path) return (path:gsub("\\\\", "/"):gsub("/%./", "/")) end
local newFileData = nfs.newFileData
nfs.newFileData = function(path)
    if not nfs.getInfo(path) then return nil, 'File not found: ' .. path end
    return newFileData(path)
end
package.loaded['SMODS.https'] = {asyncRequest=function(_, callback) callback(0, nil, {}) end}
'''

    # Cryptid separates profiles as M1/M2/M3. Browser base enumerates files
    # explicitly; update that enumeration along with the profile initialization.
    if 'Mods/Cryptid/Cryptid.lua' in files:
        def game(s):
            for i in range(1, 4):
                s = s.replace(f'"{i}/', f'"M{i}/').replace(f"'{i}/", f"'M{i}/")
            s = once(s, "    local meta = G.FILES[G.SETTINGS.profile..'/'..'meta.jkr'] or {}",
                "    local cryptidsave = get_compressed(G.SETTINGS.profile..'/cryptidsave.jkr')\n"
                "    cryptidsave = cryptidsave and STR_UNPACK(cryptidsave) or {}\n"
                "    Cryptid.shinytagdata = cryptidsave.shinytags or {}\n"
                "    local meta = G.FILES[G.SETTINGS.profile..'/'..'meta.jkr'] or {}", 'Cryptid shiny save load')
            # Saved settings already select M1/M2/M3 on the next boot. Prototype
            # initialization calls save_progress, so load that profile first.
            # The desktop injection was after init_item_prototypes in this web base.
            start = s.index('    Cryptid.profile_prefix = "M"')
            end = s.index("    --self:load_profile(G.SETTINGS.profile or 1)", start)
            profiles = s[start:end] + '    self:load_profile(G.SETTINGS.profile)\n'
            profiles = once(profiles,
                'type(G.SETTINGS.profile) ~= "string" or G.SETTINGS.profile:sub(1, #Cryptid.profile_prefix) ~= Cryptid.profile_prefix',
                'type(G.SETTINGS.profile) ~= "string" or not G.SETTINGS.profile:match("^M[123]$")',
                'valid Cryptid profile selection')
            s = s[:start] + s[end:]
            return once(s, '    self.SETTINGS.paused = nil',
                        '    self.SETTINGS.paused = nil\n\n' + profiles,
                        'load Cryptid profile before prototype discovery')
        edit('game.lua', game)

    # Stable, portable PNG encoding for the old wasm image decoder.
    from PIL import Image
    import io
    for name, data in list(files.items()):
        if name.startswith(('Mods/Cryptid/', 'Mods/Amulet/', 'Mods/Entropy/', 'Mods/Spectrallib/')) and name.endswith('.png'):
            image = Image.open(io.BytesIO(data)).convert('RGBA')
            buf = io.BytesIO(); image.save(buf, format='PNG')
            files[name] = buf.getvalue()


def compile_comparisons(files):
    if 'Mods/Cryptid/Cryptid.lua' in files or 'Mods/Entropy/Entropy.lua' in files:
        files['game.lua'] = once(files['game.lua'].decode(),
            '    self:load_profile(G.SETTINGS.profile or 1)\n    require "SMODS.preflight.loader".initSteamodded()',
            '    require "SMODS.preflight.loader".initSteamodded()',
            'retain the profile loaded before prototype discovery').encode()
    compiler = Path(__file__).with_name('compile_cryptid_lua.mjs')
    sources = {name: data.decode() for name, data in files.items()
               if name.endswith('.lua') and name != 'browser/bignum_compare.lua'}
    result = subprocess.run(['node', str(compiler)], input=json.dumps(sources),
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('Cryptid Lua compilation failed:\n' + result.stderr)
    for name, source in json.loads(result.stdout).items():
        files[name] = source.encode()
    files['main.lua'] = b'require "browser.bignum_compare"\n' + files['main.lua']
