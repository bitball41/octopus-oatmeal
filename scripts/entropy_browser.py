"""Browser adaptations for the pinned Entropy and quality-of-life mods."""
import re


def adapt_patch(mod, name, index, patch, files, target, flavor):
    p = dict(patch)
    source = files.get(target, b'').decode() if target.endswith('.lua') else ''
    key = (name, index)
    if mod == 'Overflow' and key == ('lovely/fixes.toml', 1):
        return p, 'Optional DebugPlus integration is absent from this browser bundle.'
    if mod not in ('Entropy', 'Spectrallib', 'Amulet') or 'Mods/Entropy/Entropy.lua' not in files:
        return p, None
    if mod == 'Entropy' and name == 'lovely/compat.toml':
        if index not in (15, 17, 18):
            return p, 'Optional third-party compatibility target is not bundled in the standalone Entropy preset.'
    if target == 'engine/event.lua' and 'other = {}' in p.get('pattern', ''):
        p.update(position='before', payload=p['payload'].strip().lstrip(',').strip().rstrip(',') + ',')
    if mod == 'Entropy':
        skip = {
            ('lovely/content/blinds.toml', 1): 'Browser ante arithmetic already retains non-integer and large values.',
            ('lovely/content/blinds.toml', 6): 'Desktop UnBlind wrapper is absent; the browser keeps create_UIBox_blind_tag.',
            ('lovely/content/blinds.toml', 18): 'Browser win-ante code already uses blind_on_deck.',
            ('lovely/content/blinds.toml', 21): 'Pinned Steamodded JimboQuip already accepts custom quip types.',
            ('lovely/content/blinds.toml', 22): 'Pinned Steamodded only rejects missing quip types.',
            ('lovely/content/blinds.toml', 27): 'Pinned Steamodded already checks children and animatedSprite.',
            ('lovely/content/jokers.toml', 5): 'Legacy scoring highlight loop is superseded by Steamodded calculate_main_scoring.',
            ('lovely/content/jokers.toml', 27): 'Pinned Steamodded destroy_cards already checks each card before removal.',
            ('lovely/core.toml', 9): 'Pinned Steamodded selects blinds through Blind:in_pool, not this legacy fallback.',
            ('lovely/loading.toml', 2): 'Cryptid profile-prefix override is absent in standalone Entropy.',
            ('lovely/loading.toml', 3): 'Optional Jen/Cryptid profile-prefix override is absent.',
            ('lovely/loading.toml', 4): 'Browser Entropy profiles are initialized before prototype discovery by prepare_sources.',
            ('lovely/loading.toml', 6): 'Browser Entropy configuration uses decoded G.FILES and a guarded config read.',
            ('lovely/pools.toml', 1): 'Pinned Steamodded soul-pool sampling already filters banned keys.',
            ('lovely/pools.toml', 4): 'Pinned Steamodded seal selection uses poll_object with the no_doe filter installed below.',
            ('lovely/tutorial.toml', 5): 'Browser tutorial setup already selects its boss through the current GAME state.',
            ('lovely/ui.toml', 4): 'The preceding Entropy badge patch already guards entr_aleph; Cryptid absolute stickers are absent.',
            ('lovely/ui.toml', 5): 'Upstream payload is an eternal-sticker card patch targeting localization by mistake; the card guard is already installed.',
            ('lovely/ui.toml', 28): 'Pinned Steamodded already supports mod.badge_shader through its badge builder.',
            ('lovely/ui.toml', 29): 'Pinned Steamodded uses the badge_shader metadata supplied by Entropy.',
        }
        if key in skip: return p, skip[key]
        replacements = {
            ('lovely/content/blinds.toml', 16): [('Cryptid.cheapest_boss_reroll()', "'10'")],
            ('lovely/content/blinds.toml', 24): [('if v.boss.showdown then', 'if v.boss and v.boss.showdown then')],
            ('lovely/content/consumables/reverse_codes.toml', 6): [('c = G.shop_jokers:remove_card', 'local c = G.shop_jokers:remove_card')],
            ('lovely/content/jokers.toml', 2): [('ipairs(G.handlist)', 'ipairs(handlist or G.handlist)'), ('create_UIBox_current_hand_row(v, simple)', 'create_UIBox_current_hand_row(v, simple, in_collection)'), ('index >= 10', 'index >= (G.current_hands.settings.in_collection and 10 or G.current_hands.settings.visible_hand_count)')],
            ('lovely/content/jokers.toml', 15): [('hand, parameter)', 'hand, parameter, args.level_up)')],
            ('lovely/content/jokers.toml', 16): [('StatusText = true', 'StatusText = StatusText')],
            ('lovely/content/jokers.toml', 20): [('G.GAME.round_resets.blind == G.P_BLINDS.bl_small', "G.GAME.round_resets.blind and G.GAME.round_resets.blind.name == 'Small Blind'"), ('G.GAME.round_resets.blind == G.P_BLINDS.bl_big', "G.GAME.round_resets.blind and G.GAME.round_resets.blind.name == 'Big Blind'")],
            ('lovely/content/jokers.toml', 21): [("G.GAME.blind:get_type() == 'Boss'", "G.GAME.blind_on_deck == 'Boss'")],
            ('lovely/content/stakes.toml', 7): [("hand['s_'..self.key] + hand['l_'..self.key]*(hand.level - 1)", 'hand[self.key] + amount')],
            ('lovely/fools.toml', 7): [('extras = create_UIBox_blind_tag(type, run_info)', 'if not blind_choice.config.unskippable then extras = create_UIBox_blind_tag(type, run_info) end')],
            ('lovely/pools.toml', 7): [('card:juice_up(0.6, 0.1)', 'if card and card.juice_up then card:juice_up(0.6, 0.1) end')],
            ('lovely/pools.toml', 9): [('ctype_buffer', 'obj_buffer')],
            ('lovely/pools.toml', 10): [("key_append = 'sho'", "key_append = 'sho', front = false")],
            ('lovely/tutorial.toml', 6): [("G.SETTINGS.tutorial_complete = true", "set_cloud_flag('tutorial_complete')")],
            ('lovely/ui.toml', 15): [('vars = {cfg.cry_multiuse}', 'vars = {cfg.cry_multiuse, colours = {get_type_colour(cfg, card)}}')],
            ('lovely/ui.toml', 18): [('get_rarity_badge(card.config.center.rarity)', 'get_rarity_badge(card.config.center.rarity, card.config.center)')],
            ('lovely/ui.toml', 30): [('elseif not run_info then', 'elseif not run_info and type ~= "Small" then')],
        }
        for old, new in replacements.get(key, []): p['pattern'] = p['pattern'].replace(old, new)
        if key == ('lovely/content/blinds.toml', 28):
            p['pattern'] = p['pattern'].replace('if self.debuff then', 'if self.debuff and not self.delay_debuff then', 1)
            p['payload'] = p['payload'].replace('if self.debuff then', 'if self.debuff and not self.delay_debuff then', 1)
        if key == ('lovely/content/jokers.toml', 4):
            # The same line appears in held-card scoring; only the play-area pass uses rubber_cards.
            p['pattern'] = 'local in_scoring = scoring_hand and SMODS.in_scoring(card, context.scoring_hand)'
            p.pop('times', None)
            p['payload'] = p['payload'].replace('if ((area[1])', 'if area and ((area[1])').replace('then\n  in_scoring', 'then\n  in_scoring')
            # Parenthesize the whole optional-area condition.
            p['payload'] = p['payload'].replace('if area and ((area[1]) == card and card.config.center.key == "j_entr_false_vacuum_collapse") or ((area[#area]) == card and card.config.center.key == "j_entr_phoenix_a") then', 'if area and (((area[1]) == card and card.config.center.key == "j_entr_false_vacuum_collapse") or ((area[#area]) == card and card.config.center.key == "j_entr_phoenix_a")) then')
        if key == ('lovely/content/jokers.toml', 26):
            p['pattern'] = p['pattern'].replace('scaling_message = scaling_message or {', 'local message = args.message or {').replace('or scalar_value', 'or change')
            p['payload'] = p['payload'].replace('local send_var = scalar_value', 'local send_var = change').replace('scaling_message = scaling_message or {', 'local message = args.message or {')
        if key == ('lovely/fools.toml', 5):
            p['target'] = '=[SMODS _ "src/utils.lua"]'
            # Steamodded owns rich-text E markup in this version.
        if key == ('lovely/content/consumables/other.toml', 1):
            return p, 'Steamodded moved consumable placement to Card:emplace; Entropy use callback is adapted below.'
        if key == ('lovely/content/consumables/other.toml', 7):
            p['target'] = 'functions/button_callbacks.lua'
            p['pattern'] = 'SMODS.calculate_context({using_consumeable = true, consumeable = card, area = area})'
            p['payload'] = p['payload'].replace('card.from_area', 'area')
    if mod == 'Amulet':
        if key == ('lovely/fixes.toml', 17):
            return p, 'Browser ante arithmetic already retains non-integer and large values.'
        if name == 'lovely/numfmt.toml' and index in (4,5):
            return p, 'Browser hand chip/mult labels already use number_format.'
    if mod == 'Spectrallib':
        skips = {
            ('lovely/ccd.toml', 2): 'SMODS uses card:emplace and supports consumable playing cards.',
            ('lovely/ccd.toml', 4): 'SMODS handles dynamic consumable targeting through its current callback.',
            ('lovely/ccd.toml', 6): 'SMODS edition handling already supports stacking editions.',
            ('lovely/ccd.toml', 7): 'SMODS get_edition handles negative badges through card_limits.',
            ('lovely/core.toml', 13): 'SMODS owns Sixth Sense scoring and its removal contexts.',
            ('lovely/core.toml', 15): 'SMODS handles glass removal via individual enhancement calculations.',
            ('lovely/misc.toml', 8): 'Spectrallib core already installed this pluralization hook.',
        }
        if key in skips:return p, skips[key]
        if key == ('lovely/core.toml', 7):
            p['pattern'] = p['pattern'].replace(" or (self.area and self.area == G.pack_cards)", '')
        if key == ('lovely/core.toml', 5):
            p['pattern'] = p['pattern'].replace('G.GAME.stake > 1', 'G.GAME.stake > 1 or G.GAME.modifiers.entr_entropic')
        if key == ('lovely/Ascended.toml', 5):
            p['pattern'] = "check_and_set_high_score('hand',  SMODS.calculate_round_score() )"
        if key == ('lovely/card_protection.toml', 4):
            p['pattern'] = p['pattern'].replace('ease_dollars(self.sell_cost)', 'ease_dollars(self.sell_cost, true)')
    if mod == 'Entropy':
        if key == ('lovely/content/blinds.toml', 31):
            p['pattern'] = p['pattern'].replace('G.GAME.round_resets.blind == G.P_BLINDS.bl_small', "G.GAME.round_resets.blind and G.GAME.round_resets.blind.name == 'Small Blind'").replace('G.GAME.round_resets.blind == G.P_BLINDS.bl_big', "G.GAME.round_resets.blind and G.GAME.round_resets.blind.name == 'Big Blind'")
            quip = 'if G.GAME.modifiers.entr_gfb then\n    G.GAME.gfb_quip = pseudorandom_element(G.localization.misc.gfb_quips, pseudoseed("gfb"))\nend\n'
            p['pattern'] = p['pattern'].replace("    G.GAME.round_resets.blind_states.Boss", quip + "    G.GAME.round_resets.blind_states.Boss")
            p['payload'] = p['payload'].replace("      G.GAME.round_resets.blind_states.Boss", quip + "      G.GAME.round_resets.blind_states.Boss")
        if key == ('lovely/content/consumables/other.toml', 7):
            p['pattern'] = 'SMODS.calculate_context({using_consumeable = true, consumeable = card, area = card.from_area})'
        if key == ('lovely/content/jokers.toml', 2):
            # Preserve modern pagination and collection arguments around the deleted-hand filter.
            p['pattern'] = p['pattern'].replace('if index >= (G.current_hands.settings.in_collection and 10 or G.current_hands.settings.visible_hand_count) then', "if index >= 10 and #visible_hands > 12 then -- keep pagination off until there's more than the vanilla max of 12 hands")
            p['payload'] = p['payload'].replace('ipairs(G.handlist)', 'ipairs(handlist or G.handlist)').replace('create_UIBox_current_hand_row(v, simple)', 'create_UIBox_current_hand_row(v, simple, in_collection)').replace('if index >= 10 then', "if index >= 10 and #visible_hands > 12 then")
        if key == ('lovely/content/jokers.toml', 26):
            p['pattern'] = p['pattern'].replace('local message = args.message or {', 'local msg = args.message or {')
            p['payload'] = p['payload'].replace('local message = args.message or {', 'local msg = args.message or {')
        if key == ('lovely/content/jokers.toml', 28):
            p['pattern'] = 'center.can_use and center[e.config.condition_func](center, e.config.ref_table) and not e.config.ref_table.debuff'
            p['payload'] = '(not center[e.config.condition_func] or center[e.config.condition_func](center, e.config.ref_table)) and not e.config.ref_table.debuff'
        if key == ('lovely/content/jokers.toml', 29):
            p['pattern'] = 'if center[e.config.use_func] then\n    center[e.config.use_func](center, e.config.ref_table)\nend'
            p['payload'] = p['payload'].replace('center.use', 'center[e.config.use_func]').replace('center:use(e.config.ref_table)', 'center[e.config.use_func](center, e.config.ref_table)').replace('card = card', 'card = e.config.ref_table').replace('message_card = card', 'message_card = e.config.ref_table').replace('card:start_dissolve()', 'e.config.ref_table:start_dissolve()')
        if key == ('lovely/content/jokers.toml', 30):
            return p, 'Generalized Spectrallib use buttons receive the Hypnotism condition in prepare_sources.'
    if mod == 'Spectrallib':
        if key == ('lovely/core.toml', 5):
            p['pattern'] = p['pattern'].replace('G.GAME.stake > 1 or G.GAME.modifiers.entr_entropic', 'G.GAME.stake > 1').replace('tab_definition_function = G.UIDEF.current_stake', 'tab_definition_function = SMODS.config.vanilla_stake and G.UIDEF.current_stake or G.UIDEF.SMODS_current_stake')
        if key == ('lovely/core.toml', 17):
            return p, 'The prior shared-library patch already installed the same interest algorithm; redirect its aliases below.'
        if key == ('lovely/core.toml', 18):
            p['pattern'] = p['pattern'].replace('G.GAME.interest_amount, 5,', 'G.GAME.interest_amount, Cryptid.interest_rate(),')
        if key == ('lovely/core.toml', 26):
            p['pattern'] = p['pattern'].replace("check_for_unlock({type = 'modify_deck'})", "check_for_unlock({type = 'modify_deck'}) end")
        if key == ('lovely/core.toml', 30):
            return p, 'Entropy already installs the same rubber-card scoring logic; message handling is merged below.'
        if key == ('lovely/perma_bonuses.toml', 1):
            p['pattern'] = 'new_ability.perma_h_x_blind_size = self.ability and self.ability.perma_h_x_blind_size or 0'
            p['payload'] = re.sub(r'(?m)^(\w+) = card.ability and card.ability.(\w+) or 0,', r'new_ability.\1 = self.ability and self.ability.\2 or 0', p['payload'])
            p['payload'] = p['payload'].replace('slib_bonus_effects = card.ability and card.ability.slib_bonus_effects or {},', 'new_ability.slib_bonus_effects = self.ability and self.ability.slib_bonus_effects or {}')
        if key == ('lovely/Ascended.toml', 7):
            p['pattern'] = 'update_hand_text({delay = 0}, {[parameter] = G.GAME.hands[hand][parameter], StatusText = true})'
            p['payload'] = p['payload'].replace('StatusText = StatusText', 'StatusText = true')
        if key == ('lovely/card_protection.toml', 1):
            p['pattern'] = """if not G.hand.highlighted[i].ability.scarred then
    G.hand.highlighted[i].ability.discarded = true
end
if not G.hand.highlighted[i].ability.scarred then
    draw_card(G.hand, Spectrallib.return_to_deck() and G.deck or G.discard, i*100/highlighted_count, 'down', false, G.hand.highlighted[i])
end"""
            p['payload'] = p['payload'].replace('if G.hand.highlighted[i]:protected_from_discard()', 'if G.hand.highlighted[i].ability.scarred or G.hand.highlighted[i]:protected_from_discard()')
        if key == ('lovely/card_protection.toml', 4):
            p['pattern'] = "ease_dollars(self.sell_cost)\ndelay(0.3)"
            p['payload'] = """ease_dollars(self.sell_cost)
if not self:protected_from_selling() then self:start_dissolve({G.C.GOLD}) end
delay(0.3)"""
    if mod == 'Entropy' and key == ('lovely/content/blinds.toml', 31):
        begin = source.index("if G.GAME.round_resets.blind and G.GAME.round_resets.blind.name == 'Small Blind' then", source.index('function end_round'))
        end = source.index('if G.GAME.round_resets.temp_handsize', begin)
        p['pattern'] = source[begin:end].rstrip()
    if mod == 'Entropy' and key == ('lovely/content/jokers.toml', 26):
        p["pattern"] = "args.scaling_message = SMODS.merge_defaults(args.scaling_message, {\nmessage = localize(args.message_key and {type='variable',key=args.message_key,vars={args.message_key =='a_xmult' and args.ref_table[args.ref_value] or change}} or 'k_upgrade_ex'),"
        p['payload'] = p['payload'].replace('local msg = args.message or {', 'args.scaling_message = SMODS.merge_defaults(args.scaling_message, {')
    if mod == 'Spectrallib' and key == ('lovely/Ascended.toml', 7):
        return p, 'Pinned Steamodded routes hand-level display through Scoring_Parameter; this legacy common_events text call is absent.'
    if mod == 'Spectrallib' and key == ('lovely/card_protection.toml', 1):
        p['pattern'] = 'if not G.hand.highlighted[i].ability.scarred then'
        p['payload'] = 'if not G.hand.highlighted[i].ability.scarred and not G.hand.highlighted[i]:protected_from_discard() then'
        p['position'] = 'at'
    if mod == 'Spectrallib' and key == ('lovely/card_protection.toml', 4):
        p['pattern'] = 'self:start_dissolve({G.C.GOLD})'
        p['payload'] = 'if not self:protected_from_selling() then self:start_dissolve({G.C.GOLD}) end'
        p['position'] = 'at'
    return p, None

def prepare_sources(files):
    name = 'Mods/Entropy/lib/config.lua'
    if name in files:
        text = files[name].decode()
        text = text.replace('if v.slib_credits then', 'repeat\n            if v.slib_credits then', 1)
        text = text.replace('goto continue', 'break').replace('::continue::', 'until true')
        files[name] = text.encode()
    # Vanilla Constellation receives many contexts without a consumable.
    for name in ('Mods/Overflow/Overflow.lua', 'main.lua'):
        if name in files:
            files[name] = files[name].replace(
                b"self.ability.name == 'Constellation' and not context.blueprint and context.consumeable.ability.set",
                b"self.ability.name == 'Constellation' and context.using_consumeable and not context.blueprint and context.consumeable.ability.set")
    name = 'Mods/JokerDisplay/libs/nativefs/nativefs.lua'
    if name in files:
        files[name] = b'return require("browser.nativefs")\n'
    for name in ('Mods/Overflow/modules/utils.lua', 'overflow/utils.lua'):
        if name in files:
            files[name] = files[name].replace(b'love.filesystem.exists("config/Overflow.lua")', b'love.filesystem.getInfo("config/Overflow.lua")')

    if 'Mods/Entropy/Entropy.lua' not in files:
        return
    # Browser storage returns decoded settings and enumerates profile files explicitly.
    text = files['game.lua'].decode()
    anchor = "    local settings = G.FILES['settings.jkr']"
    assert text.count(anchor) == 1
    text = text.replace(anchor, anchor + '''
    Entropy_config = {profile_prefix = true}
    if love.filesystem.getInfo('config/entr.jkr') then
        local saved = get_compressed('config/entr.jkr')
        if saved then Entropy_config = STR_UNPACK(saved) or Entropy_config end
    end
''')
    for i in range(1, 4):
        text = text.replace(f'"{i}/', f'"E{i}/').replace(f"'{i}/", f"'E{i}/")
    anchor = '    self.SETTINGS.paused = nil'
    assert text.count(anchor) == 1
    text = text.replace(anchor, anchor + '''
    Cryptid = Cryptid or {}
    Cryptid.profile_prefix = 'E'
    G.SETTINGS.profile_counters = G.SETTINGS.profile_counters or {}
    if type(G.SETTINGS.profile) ~= 'string' or not G.SETTINGS.profile:match('^E[123]$') then
        G.SETTINGS.profile = 'E1'
    end
    for i = 1, 3 do
        G.PROFILES['E'..i] = G.PROFILES['E'..i] or {}
        G.SETTINGS.profile_counters['E'..i] = G.SETTINGS.profile_counters['E'..i] or 0
    end
    self:load_profile(G.SETTINGS.profile)
''')
    files['game.lua'] = text.encode()
    # Shared-library interest hooks were carried over under Cryptid's alias.
    for path in ('functions/state_events.lua', 'functions/common_events.lua'):
        files[path] = files[path].replace(b'Cryptid.get_interest(', b'Spectrallib.get_interest(').replace(b'Cryptid.interest_rate()', b'Spectrallib.interest_rate()')
    name = 'Mods/Steamodded/src/utils.lua'
    text = files[name].decode()
    anchor = 'local options = args.options or get_current_pool("Seal")'
    assert text.count(anchor) == 1
    text = text.replace(anchor, anchor + '''
    local allowed = {}
    for _, key in ipairs(options) do
        if not G.GAME.banned_keys[key] and not (SMODS.Seals[key] and SMODS.Seals[key].no_doe) then
            allowed[#allowed+1] = key
        end
    end
    options = #allowed > 0 and allowed or {'Red'}
''')
    files[name] = text.encode()

    for name in ('Mods/Entropy/manifest.json', 'Mods/Spectrallib/manifest.json'):
        files.pop(name, None)
    # WebGL 1 requires a constant loop bound. This retains the full dynamic outline radius.
    name = 'Mods/Entropy/assets/shaders/pulseoutline.fs'
    text = files[name].decode()
    old = 'for (float i = delta2; i <= delta2*outline_width; i+=3.*delta2) {'
    assert text.count(old) == 1
    text = text.replace(old, 'for (int sample_i = 0; sample_i < 22; sample_i++) { float i = (1.0 + 3.0 * float(sample_i)) * delta2; if (i > delta2 * outline_width) break;')
    files[name] = text.encode()
    name = 'Mods/Spectrallib/Entropy/card_buttons.lua'
    text = files[name].decode()
    anchor = 'if card.config.center[v.use_func] then use = true end'
    assert text.count(anchor) == 1
    text = text.replace(anchor, 'if card.config.center[v.use_func] or next(SMODS.find_card("j_entr_hypnotism")) then use = true end')
    files[name] = text.encode()
    name = 'Mods/Steamodded/src/utils.lua'
    text = files[name].decode()
    anchor = 'if G.rubber_cards and scoring_hand [_] == scoring_hand [_-1] then'
    assert anchor in text
    text = text.replace(anchor, '''if G.rescore_messages and G.rescore_messages[_] and G.rescore_messages[_].message then
    card_eval_status_text(G.rescore_messages[_].card, 'extra', nil, nil, nil,
        {message=G.rescore_messages[_].message, colour=G.C.PURPLE})
end
''' + anchor)
    files[name] = text.encode()
    name = 'Mods/Entropy/assets/shaders/freaky.fs'
    files[name] = files[name].replace(b'int hcount = 17;', b'const int hcount = 17;')
    name = 'Mods/Entropy/assets/shaders/invertradius.fs'
    files[name] = files[name].replace(b'float c=3;', b'const float c=3.0;')
    # Desktop GLSL permits implicit int/float conversions that WebGL 1 rejects.
    shader_replacements = {
        'brimstone_badge.fs': [('uv.x * 2)', 'uv.x * 2.0)')],
        'eeshader.fs': [('p.x+2000, 4000', 'p.x+2000.0, 4000.0'), ('p.y+2000, 4000', 'p.y+2000.0, 4000.0'), ('float dummy = 2;', 'float dummy = 2.0;'), ('dummy = 3;', 'dummy = 3.0;'), ('uv.x * 2)', 'uv.x * 2.0)')],
        'entr_astral.fs': [('float outp = 0;', 'float outp = 0.0;'), ('pow(2,-i)', 'pow(2.0,-float(i))'), ('pow(2,i)', 'pow(2.0,float(i))'), (')),2))', ')),2.0))'), ('outp/256', 'outp/256.0'), ('pow(field_part3.x, 2)', 'pow(field_part3.x, 2.0)')],
        'flashlight.fs': [('(1+sin(x))/2', '(1.0+sin(x))/2.0'), ('* (1 - ((', '* (1.0 - ((')],
        'invertradius.fs': [('2*dist', '2.0*dist'), ('inverted.g=0;', 'inverted.g=0.0;'), ('inverted.b = 0;', 'inverted.b = 0.0;'), ('2.0f', '2.0'), ('1.0f', '1.0')],
        'redvignette.fs': [('3*sqrt', '3.0*sqrt'), ('power/10', 'power/10.0'), ('min(dist, 1)', 'min(dist, 1.0)'), ('pow(noise, 3)', 'pow(noise, 3.0)'), ('pow(noise, 4)', 'pow(noise, 4.0)'), ('(1-noise)', '(1.0-noise)'), ('(1-a)', '(1.0-a)')],
        'splash.fs': [('+500, 1000', '+500.0, 1000.0'), ('time + 130', 'time + 130.0')],
        'vignette.fs': [('vec4(1-a, 1-a, 1-a, 1)', 'vec4(1.0-a, 1.0-a, 1.0-a, 1.0)')],
    }
    for shader, replacements in shader_replacements.items():
        name = 'Mods/Entropy/assets/shaders/' + shader
        text = files[name].decode()
        for old, new in replacements:
            assert old in text, (shader, old)
            text = text.replace(old, new)
        files[name] = text.encode()

    name = 'Mods/Entropy/assets/shaders/invertradius.fs'
    files[name] = re.sub(rb'(\d+\.\d+)f\b', rb'\1', files[name])
    name = 'Mods/Entropy/assets/shaders/invertradius.fs'
    files[name] = files[name].replace(b'(1-t)*tex', b'(1.0-t)*tex').replace(b'float max_mult = 2;', b'float max_mult = 2.0;')
    # Match uniform precision across LÖVE's vertex/fragment stages on WebGL 1.
    for name, data in list(files.items()):
        if name.startswith('Mods/Entropy/') and name.endswith('.fs'):
            files[name] = re.sub(rb'\bextern\s+(float|number|vec[234]|int)\b', rb'extern mediump \1', data)
    name = 'Mods/Entropy/assets/shaders/invertradius.fs'
    files[name] = files[name].replace(b'float min_dist=dist;', b'#define min_dist (dist)').replace(b'float max_dist=2.0*dist;', b'#define max_dist (2.0*dist)')
