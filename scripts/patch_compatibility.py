"""Explicit compatibility decisions for the pinned browser base (not fuzzy matching)."""
import re

ANCHORS = {
    # Do not remap Steamodded back.toml patch 7 onto `if not back_config.unlocked then`
    # with position=at. That deletes the unlocked check so Red Deck shows
    # "Not available in this demo". See adapt_patch for the insert-after fix.
    ('Steamodded','lovely/playing_card.toml',9): 'return G.ARGS.LOC_COLOURS[_c] or _default or G.C.BLACK',
    ('Steamodded','lovely/pool.toml',3): 'local randInd = math.random(#keys)',
    ('Steamodded','lovely/scoring_calculation.toml',11): "check_and_set_high_score('hand',  SMODS.calculate_round_score() )",
    ('Steamodded','lovely/override_notice.toml',17): 'function create_UIBox_notify_alert(_achievement, _type, _from_left)',
    ('Steamodded','lovely/threads.toml',1): 'while request do',
    ('Steamodded','lovely/fixes.toml',39): 'if v.config.center and (v.config.center.name == "Steel Card") then self.ability.steel_tally = self.ability.steel_tally+1 end',
    ('Steamodded','lovely/fixes.toml',40): 'if v.config.center and (v.config.center.name == "Stone Card") then self.ability.stone_tally = self.ability.stone_tally+1 end',
    ('Steamodded','lovely/fixes.toml',44): 'if v.config.center and (v.config.center.name ~= "Default Base") then self.ability.driver_tally = self.ability.driver_tally+1 end',
    ('Steamodded','lovely/fixes.toml',47): 'if G.pack_cards and G.pack_cards.cards and (G.pack_cards.cards[1]) and',
    ('Paperback','lovely/vacation_juice.toml',3): "if G.GAME.round_resets.blind and G.GAME.round_resets.blind.name == 'Small Blind' then\nG.GAME.round_resets.blind_states.Small = 'Defeated'\n",
    ('Multiplayer','lovely/TheOrder.toml',3): 'self.GAME.pseudorandom.hashed_seed = pseudohash(self.GAME.pseudorandom.seed)',
    ('Multiplayer','lovely/pause.toml',1): 'local credits = nil',
    ('Bunco','lovely.toml',20): 'if G.GAME.current_round.discards_left <= 0 or #G.hand.highlighted <= 0 or #G.hand.highlighted > math.max(G.GAME.starting_params.discard_limit, 0) then',
    ('Bunco','lovely.toml',27): 'if #G.hand.highlighted <= 0 or G.GAME.blind.block_play or #G.hand.highlighted > math.max(G.GAME.starting_params.play_limit, 1) then',
    ('Bunco','lovely.toml',43): 'function level_up_hand(card, hand, instant, amount, statustext)',
    ('Bunco','lovely.toml',45): 'function level_up_hand(card, hand, instant, amount, statustext)',
    ('Bunco','lovely.toml',48): "if self.name == 'The Wheel' and SMODS.pseudorandom_probability(self, pseudoseed('wheel'), 1, 7, 'wheel') then",
    ('Bunco','lovely.toml',60): 'if SMODS.smeared_check(self, suit) then',
    ('Bunco','lovely.toml',99): 'ease_to = G.GAME.chips + math.floor( SMODS.calculate_round_score() ),',
    ('Bunco','lovely.toml',112): 'SMODS.calculate_context({open_booster = true, card = self, booster = booster_obj})',
    ('Bunco','lovely.toml',122): 'G.GAME.pack_choices = math.min((self.ability.choose or self.config.center.config.choose or 1) + (G.GAME.modifiers.booster_choice_mod or 0), self.ability.extra and math.max(1, self.ability.extra + (G.GAME.modifiers.booster_size_mod or 0)) or self.config.center.extra and math.max(1, self.config.center.extra + (G.GAME.modifiers.booster_size_mod or 0)) or 1)',
    ('Bunco','lovely.toml',159): 'if G.GAME.blind and G.GAME.blind.in_blind and not self.from_quantum then G.E_MANAGER:add_event(Event({ func = function() G.GAME.blind:set_blind(nil, true, nil); return true end })) end',
}

SKIPS = {}
def skip(mod, manifest, indices, reason):
    for index in indices: SKIPS[(mod,'lovely/'+manifest+'.toml',index)] = reason
skip('Steamodded','preflight',[7], 'The browser base has no macOS LuaJIT bootstrap.')
skip('Steamodded','fixes',[2,50,51,52,53,54], 'Desktop Steam integration is absent from the browser base.')
skip('Steamodded','fixes',[3], 'Browser saves are already decoded in G.FILES and guarded for nil before can_continue; there is no STR_UNPACK savefile path.')
skip('Steamodded','enhancement',[13,14,17,22], 'Earlier better_calc patches replace these scoring loops with SMODS.calculate_main_scoring and context evaluation.')
skip('Steamodded','better_calc',[61], 'The earlier scoring replacement removes the desktop per-card percent loop.')
skip('Steamodded','event',[1], 'Upstream targets nonexistent event.lua; actual engine/event.lua receives its separate patches.')
skip('Steamodded','mobile_patches',[2,4,5], 'The browser base already includes mobile DPI and text-input routing; retain that platform code.')
skip('Steamodded','menu',[6], 'CRT bloom option is already disabled by the browser port.')
skip('Steamodded','screenshader_rendering',[1,2], 'The browser owns its AA/scaled final canvas pass and disables CRT. The bundled Multiplayer mod registers no ScreenShader; retain the browser renderer instead of drawing an unscaled desktop canvas behind it.')
skip('Multiplayer','compatibility',[1,2], 'Optional AntePreview and Cryptid mods are not bundled.')
skip('Multiplayer','misc',[12], 'Optional All in Jest Patchwork deck is not bundled.')
skip('Paperback','perma_odds',[4], 'This Steamodded build keeps perma_h_dollars tooltips in utils.lua; the duplicate game_object.lua path is absent.')
SKIPS[('Bunco','lovely.toml',10)] = 'Steamodded moved the DESCSCALE tooltip assembler into src/utils.lua; the desktop localize hook is gone.'
SKIPS[('Bunco','lovely.toml',152)] = 'ease_dollars lives in common_events.lua on this Steamodded build; Bunco already patches that copy (index 151).'
SKIPS[('Bunco','lovely.toml',154)] = 'The browser card back sprite is already created behind if not self.children.back then.'


def adapt_patch(mod, name, index, patch, source):
    key=(mod,name,index)
    patch=dict(patch)
    if key in ANCHORS: patch['pattern']=ANCHORS[key]
    if key==('Steamodded','lovely/text_effect.toml',1):
        patch['pattern']='if self.config.bump then letter.offset.y = (G.SETTINGS.reduced_motion and 0 or 1)*self.bump_amount*math.sqrt(self.scale)*((7*self.font.render_scale/(G.TILESIZE*10))*math.max(0, (5+self.bump_rate)*math.sin(self.bump_rate*G.TIMERS.REAL+200*k) - 3 - self.bump_rate)) end'
    if key==('Steamodded','lovely/perma_bonus.toml',13):
        patch['pattern']=patch['pattern'].replace("pseudorandom('lucky_mult') < G.GAME.probabilities.normal/5", "SMODS.pseudorandom_probability(self, 'lucky_mult', 1, 5)")
    if mod=='Steamodded' and name=='lovely/ui_elements.toml' and index in (22,23):
        patch['pattern']=patch['pattern'].replace('self.config.lang.font','(self.config.font or self.config.lang.font)')
        patch['payload']=patch['payload'].replace('self.config.lang.font','(self.config.font or self.config.lang.font)')
    if key==('Steamodded','lovely/back.toml',7):
        # Browser back.lua uses `if not back_config.unlock_condition or back_config.demo`.
        # Upstream SMODS replaces a lone unlock_condition check. Keep the unlocked
        # guard and only inject the SMODS localization locals into that branch.
        patch['pattern'] = 'if not back_config.unlocked then'
        patch['position'] = 'after'
        payload = patch['payload']
        marker = 'if not back_config.unlock_condition then'
        assert payload.rstrip().endswith(marker), 'Steamodded back.lua payload changed'
        patch['payload'] = payload[:payload.rstrip().rfind(marker)].rstrip() + '\n'
    if key==('Steamodded','lovely/stake.toml',23):
        patch['pattern']=patch['pattern'].replace('\n\n','\n')
    if key==('Steamodded','lovely/blind.toml',35):
        begin=source.index('if not v.boss then')
        end=source.index('\n    end\n    for k, v in pairs(G.GAME.banned_keys)',begin)
        old=source[begin:end]
        patch['pattern']=old
        patch['payload']='if not G.FTP_LOCKED then\n'+patch['payload']+'\nelse\n'+old+'\nend'
    if key==('Paperback','lovely/ace_apostle_straights.toml',4):
        patch['payload'] = patch['payload'].replace('goto pb_continue_rank_next', 'break')
        patch['payload'] = 'repeat\n' + patch['payload']
    if key==('Paperback','lovely/ace_apostle_straights.toml',5):
        patch['payload'] = (patch['payload']
                            .replace('goto pb_continue_rank_next', 'break')
                            .replace('::pb_continue_rank_next::', 'until true'))
    if key==('Bunco','lovely.toml',20):
        # Keep Steamodded discard_limit and add The 8's highlighted-limit bypass.
        patch['payload'] = (
            'if G.GAME.current_round.discards_left <= 0 or #G.hand.highlighted <= 0 '
            'or #G.hand.highlighted > math.max(G.GAME.starting_params.discard_limit, 0) '
            'or (G.GAME.THE_8_BYPASS and (#G.hand.highlighted > G.hand.config.highlighted_limit)) then'
        )
    if key==('Bunco','lovely.toml',27):
        patch['payload'] = (
            '\nlocal group_size = 0\n\n'
            'if G.hand and G.hand.highlighted then\n'
            '    for i = 1, #G.hand.highlighted do\n'
            '        if G.hand.highlighted[i].ability.group then\n'
            '            group_size = group_size + 1\n'
            '        end\n'
            '    end\n'
            'end\n\n'
            "if #G.hand.highlighted <= (G.GAME.blind and G.GAME.blind.name == 'cry-Sapphire Stamp' "
            'and not G.GAME.blind.disabled and 1 or 0) or G.GAME.blind.block_play or '
            '(#G.hand.highlighted > math.max(G.GAME.starting_params.play_limit, 1) '
            'and group_size <= math.max(G.GAME.starting_params.play_limit, 1)) then\n'
        )
    if key==('Bunco','lovely.toml',99):
        patch['payload'] = (
            'ease_to = G.GAME.chips + math.floor( SMODS.calculate_round_score() ) '
            '* (antiscore and -1 or 1),'
        )
    return patch, SKIPS.get(key)
