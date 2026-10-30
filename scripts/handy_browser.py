"""Platform adapters for the pinned Handy mod; native gameplay stays upstream."""
from browser_adapters import once


def adapt_handy_patch(name, index, patch, files, resolve, flavor=None):
    target = resolve(patch['target'])
    if flavor == 'handy':
        source = files.get(target, b'').decode()
        if target not in files and patch['target'].startswith('=[SMODS '):
            return patch, 'Standalone Handy has no Steamodded or optional content mods.'
        if name == 'lovely/ui_fixes.toml' and index <= 13:
            return patch, 'The Vanilla browser base retains its existing text input and alignment implementation.'
        if name == 'lovely/controls/scoring_hold.toml' and index == 2:
            return patch, 'Vanilla uses the stock scoring path; the preceding patch supplies its hold event.'
        if name == 'lovely/controls/animation_skip.toml':
            if index in (5, 7, 9):
                return patch, 'Alternative Talisman animation hooks do not apply to Vanilla.'
            if index == 8 and 'card:juice_up(0.1, 0.1, true)' in source:
                patch = dict(patch)
                patch['pattern'] = patch['pattern'].replace('0.1, 0.1)', '0.1, 0.1, true)')
        return patch, None
    if target not in files and (patch['target'].startswith('=[SMODS Multiplayer') or
                                patch['target'].startswith('=[SMODS DebugPlus')):
        return patch, 'Optional desktop mod is not bundled in Cryptid mode.'
    patch = dict(patch)
    if name == 'lovely/ui_fixes.toml' and index <= 13:
        return patch, 'Steamodded/browser already supplies alignment and multi-field text input fixes.'
    if name == 'lovely/controls/scoring_hold.toml' and index == 1:
        return patch, 'Steamodded scoring uses calculate_round_score; the following patch supplies its hold event.'
    if name == 'lovely/controls/animation_skip.toml':
        if index == 5:
            return patch, 'Amulet uses its noanims hook; the preceding patch retains dollar-buffer reset events.'
        if index in (6, 7):
            return patch, 'Steamodded resolves card effects through trigger_effects; Handy juice hooks cover that path.'
        if index == 8:
            patch['pattern'] = patch['pattern'].replace('0.1, 0.1)', '0.1, 0.1, true)')
        if index == 9:
            return patch, 'Browser juice_card_until was adapted by the preceding patch.'
        if index == 17 and flavor == 'cryptid' and 'Mods/Cryptid/Cryptid.lua' in files:
            patch['pattern'] = 'if to_big(amt) ~= to_big(0) then'
    return patch, None


def prepare_handy_sources(files):
    # The read-only web archive has no native FFI or self-updating threads.
    # Handy already supports distributions without the updater (Thunderstore).
    for name in list(files):
        if name.startswith('Mods/Handy/src/core/updater/'):
            del files[name]
    files['Mods/Handy/src/libs/nativefs.lua'] = b'return require("browser.nativefs")\n'
    files.pop('Mods/Handy/manifest.json', None)
    for path, filename in [('Mods/Handy/src/core/config/index.lua', 'Handy.jkr'),
                           ('Mods/Handy/src/core/presets/index.lua', 'Handy_Presets.jkr')]:
        files[path] = once(files[path].decode(), f'get_compressed("config/{filename}")',
            f'(love.filesystem.getInfo("config/{filename}") and get_compressed("config/{filename}"))',
            'optional Handy settings').encode()
    path = 'Mods/Handy/src/controls/speed_multiplier/hooks.lua'
    files[path] = once(files[path].decode(),
        'time_budget = math.max(0.0333, time_budget or 3e-4)',
        'time_budget = math.min(0.002, time_budget or 3e-4)',
        'browser GC frame budget').encode()
    path = 'Mods/Handy/src/controls/animation_skip/hooks.lua'
    text = once(files[path].decode(),
        'function ease_dollars(amount, ...)', 'function ease_dollars(amount, instant, ...)',
        'Handy explicit instant argument')
    text = text.replace('ease_dollars_ref(amount, ...)', 'ease_dollars_ref(amount, instant, ...)')
    files[path] = once(text,
        '\t\tHandy.animation_skip.ease_dollars_buffer = Handy.animation_skip.ease_dollars_buffer + amount\n\t\treturn',
        '\t\t-- Commit every payout separately: money_altered effects may scale per payment.\n'
        '\t\treturn ease_dollars_ref(amount, true, ...)',
        'Handy per-payment accounting').encode()
    path = 'Mods/Handy/src/ui/assets.lua'
    files[path] = files[path].replace(b'mipmaps = true', b'mipmaps = false')
    # Preserve config/save identity and make useful, non-destructive controls
    # available immediately. User settings override these first-boot defaults.
    path = 'Mods/Handy/src/core/config/default_config.lua'
    text, old_config = files[path].decode().split('local old_default_v1', 1)
    for key in ('dangerous_actions', 'dangerous_actions_sell_all_same', 'dangerous_actions_sell_all'):
        text = once(text, f'\t{key} = {{\n\t\tenabled = false,',
                    f'\t{key} = {{\n\t\tenabled = true,', 'Handy default ' + key)
    for key, keys in [('dangerous_actions_sell_all_same', '"Shift", "Right Mouse"'),
                      ('dangerous_actions_sell_all', '"Ctrl", "Shift", "Right Mouse"')]:
        text = once(text, f'\t{key} = {{\n\t\tenabled = true,\n\t\tkeys_1 = {{}},',
                    f'\t{key} = {{\n\t\tenabled = true,\n\t\tkeys_1 = {{ {keys} }},', 'Handy binding ' + key)
    # The web distribution caps speed at 512 and never uses unsafe event reorder.
    files[path] = (text + 'local old_default_v1' + old_config).encode()
    path = 'Mods/Handy/src/index.lua'
    files[path] += b'\nrequire("browser.handy").install()\n'
