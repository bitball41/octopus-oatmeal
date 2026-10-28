"""Explicit intersections between pinned mods; missing patches remain build errors."""
import re

def adapt(mod, name, index, p, files, target):
    p = dict(p)
    source = files.get(target, b'').decode() if target.endswith('.lua') else ''
    if mod == 'Handy' and name == 'lovely/controls/mp_extension.toml' and index == 1:
        if p['pattern'] not in source:
            return p, 'Pinned Multiplayer dispatches actions through a handler table, not this legacy extension protocol.'
    if mod == 'Multiplayer' and name == 'lovely/TheOrder.toml' and index == 14 and p['pattern'] not in source:
        if 'guaranteed' in source:
            return p, 'New Steamodded seal selector already handles guaranteed seals independently of the weighted poll.'
    if mod == 'Multiplayer' and name == 'lovely/misc.toml' and index == 13 and p['pattern'] not in source:
        p['pattern'] = next(line.strip() for line in source.splitlines() if 'local flags = SMODS.calculate_context(' in line and 'create_shop_card' in line)
    if mod == 'Multiplayer' and name == 'lovely/shared_area.toml' and index == 1:
        p['times'] = len(re.findall(p['pattern'], source))
    if mod == 'Paperback' and name == 'lovely/more_showdowns.toml' and p['pattern'] not in source:
        p['pattern'] = next(line.strip() for line in source.splitlines() if 'G.GAME.bosses_used[boss]' in line)
        p['position']='before'
    if mod == 'Paperback' and name == 'lovely/sell_use_flags.toml' and index == 7:
        p['pattern'] = r'function Card:start_dissolve\([^\n]*\n[\s\S]*?(?<root>self:remove\(\))'
    if mod == 'Bunco' and name == 'lovely.toml' and 'Mods/Cryptid/Cryptid.lua' in files:
        if index == 1:
            p['pattern']='hand.played = hand.played + 1'
        if index == 22:
            p['pattern']='if to_big(#self.highlighted) >= to_big(self.config.highlighted_limit) then'
            p['payload']="if to_big(#self.highlighted) >= to_big(self.config.highlighted_limit) and not card.ability.group and not (G.GAME and G.GAME.THE_8_BYPASS) then"
        if index == 41:
            p['pattern']=next(line.strip() for line in source.splitlines() if 'handname=disp_text, level=G.GAME.hands[text].level' in line)
            p['payload']=p['pattern'].replace('level=G.GAME.hands[text].level', "level=text=='bunc_Deal' and '0' or G.GAME.hands[text].level")
        if index in (91,104):
            p['pattern']=r'(?<indent>[\t ]*)-- TARGET: effects before deck final_scoring_step'
        if index == 128:
            p['pattern']='add_tag(tag_key and Tag(tag_key) or _tag.config.ref_table, true)'
        if index in (157,158):
            p['position']='at'
            p['payload']=p['pattern'].replace("if self.ability.name == 'Credit Card' then", "if not from_debuff and self.ability.name == 'Credit Card' then")
        if index == 159:
            return p, 'Credit Card guard is applied directly; avoid enclosing and then losing Cryptid/Amulet downstream hooks.'
    if mod == 'CardSleeves':
        if name == 'lovely/expected_to_fail.toml' and p['pattern'] not in source and (index == 2 or not re.search(p['pattern'],source)):
            return p, 'Optional legacy Galdur/draw or five-card-limit anchor absent; Steamodded already owns selection limits.'
        if name == 'lovely/expected_to_match.toml' and index == 1:
            # The browser has commented debug lines inside this seed block.
            i = source.index('self.GAME.pseudorandom.seed = args.seed')
            start = source.rfind('if not saveTable then', 0, i)
            end = source.index('\n', source.index('self.GAME.pseudorandom.hashed_seed =', i))
            p['pattern'] = source[start:end]
            p['payload'] = '-- Seed initialization moved earlier by CardSleeves.'
        if name == 'lovely/expected_to_match.toml' and index == 2 and 'Mods/Multiplayer/core.lua' in files:
            p['payload'] = p['payload'].replace('for k, v in pairs(self.GAME.pseudorandom)', 
                'if self.GAME.pseudorandom.seed:sub(1,1) ~= "*" and MP.should_use_the_order() then self.GAME.pseudorandom.seed = "*" .. self.GAME.pseudorandom.seed end\nfor k, v in pairs(self.GAME.pseudorandom)')
        if name == 'lovely/expected_to_match.toml' and index == 3 and p['pattern'] not in source:
            return p, 'Steamodded DrawStep owns stake sticker rendering with rotation and offsets.'
    return p, None
