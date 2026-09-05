"""Explicit compatibility decisions for the pinned browser base (not fuzzy matching)."""
import re

ANCHORS = {
    ('Steamodded','lovely/back.toml',7): 'if not back_config.unlocked then',
    ('Steamodded','lovely/playing_card.toml',9): 'return G.ARGS.LOC_COLOURS[_c] or _default or G.C.BLACK',
    ('Steamodded','lovely/pool.toml',3): 'local randInd = math.random(#keys)',
    ('Steamodded','lovely/scoring_calculation.toml',11): "check_and_set_high_score('hand',  SMODS.calculate_round_score() )",
    ('Steamodded','lovely/override_notice.toml',17): 'function create_UIBox_notify_alert(_achievement, _type, _from_left)',
    ('Steamodded','lovely/threads.toml',1): 'while request do',
    ('Steamodded','lovely/fixes.toml',39): 'if v.config.center and (v.config.center.name == "Steel Card") then self.ability.steel_tally = self.ability.steel_tally+1 end',
    ('Steamodded','lovely/fixes.toml',40): 'if v.config.center and (v.config.center.name == "Stone Card") then self.ability.stone_tally = self.ability.stone_tally+1 end',
    ('Steamodded','lovely/fixes.toml',44): 'if v.config.center and (v.config.center.name ~= "Default Base") then self.ability.driver_tally = self.ability.driver_tally+1 end',
    ('Steamodded','lovely/fixes.toml',47): 'if G.pack_cards and G.pack_cards.cards and (G.pack_cards.cards[1]) and',
    ('Multiplayer','lovely/TheOrder.toml',3): 'self.GAME.pseudorandom.hashed_seed = pseudohash(self.GAME.pseudorandom.seed)',
    ('Multiplayer','lovely/pause.toml',1): 'local credits = nil',
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
    if key==('Steamodded','lovely/stake.toml',23):
        patch['pattern']=patch['pattern'].replace('\n\n','\n')
    if key==('Steamodded','lovely/blind.toml',35):
        begin=source.index('if not v.boss then')
        end=source.index('\n    end\n    for k, v in pairs(G.GAME.banned_keys)',begin)
        old=source[begin:end]
        patch['pattern']=old
        patch['payload']='if not G.FTP_LOCKED then\n'+patch['payload']+'\nelse\n'+old+'\nend'
    return patch, SKIPS.get(key)
