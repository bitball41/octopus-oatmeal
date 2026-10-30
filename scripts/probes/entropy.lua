local qa_update = love.update
local qa_step = 0
local qa_ready = false
local qa_main_menu = Game.main_menu
function Game:main_menu(...)
    local result = qa_main_menu(self, ...)
    qa_ready = true
    return result
end
function love.update(dt)
    qa_update(dt)
    if G and G.OVERLAY_MENU and G.FUNCS.exit_overlay_menu then G.FUNCS.exit_overlay_menu() end
    if qa_step == 0 and G and qa_ready and Entropy and Spectrallib and SMODS then
        qa_step = 1
        local count = 0
        for key in pairs(G.P_CENTERS) do if key:match('^j_entr_') then count=count+1 end end
        assert(count > 200, 'Entropy content did not load')
        assert(G.SETTINGS.profile == 'E1', 'Entropy did not select an isolated profile')
        print('PROBE ENTROPY CONTENT LOADED '..count)
        if G.OVERLAY_MENU then G.FUNCS.exit_overlay_menu() end
        G.SETTINGS.tutorial_complete = true
        G.FUNCS.start_run(nil, {seed='ENTRTEST'})
    elseif qa_step == 1 and G.STAGE == G.STAGES.RUN and G.consumeables and G.jokers and G.blind_select then
        qa_step = 2
        print('PROBE ENTROPY RUN STARTED')
        G.FUNCS.select_blind({UIBox=G.blind_select, config={ref_table=G.P_BLINDS.bl_small}})
    elseif qa_step == 2 and G.hand and #G.hand.cards > 0 and G.STATE == G.STATES.SELECTING_HAND then
        qa_step = 3
        print('PROBE ENTROPY HAND DEALT')
        if G.OVERLAY_TUTORIAL then G.FUNCS.skip_tutorial_section() end
        G.hand:add_to_highlighted(G.hand.cards[1], true)
        G.FUNCS.play_cards_from_highlighted()
    elseif qa_step == 3 and G.GAME and to_number(G.GAME.chips) > 0 and G.GAME.current_round.hands_played > 0 then
        qa_step = 4
        print('PROBE ENTROPY HAND SCORED '..to_number(G.GAME.chips))
    end
end
