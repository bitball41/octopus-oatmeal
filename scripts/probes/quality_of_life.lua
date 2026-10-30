local qa_update = love.update
local qa_step = 0
function love.update(dt)
    qa_update(dt)
    if qa_step == 0 and G and G.STAGE == G.STAGES.MAIN_MENU and G.P_CENTERS and G.P_CENTERS.j_joker and JokerDisplay and JokerDisplay.Definitions and Overflow and G.MAIN_MENU_UI then
        assert(Handy, 'QA Handy was not loaded')
        assert(JokerDisplay and JokerDisplay.Definitions, 'QA JokerDisplay was not loaded')
        assert(Overflow and Overflow.can_merge, 'QA Overflow was not loaded')
        print('PROBE QOL MODS LOADED')
        qa_step = 1
        G.SETTINGS.tutorial_complete = true
        G.FUNCS.start_run(nil, {seed='QOLTEST1'})
    elseif qa_step == 1 and G.STAGE == G.STAGES.RUN and G.consumeables and G.jokers then
        qa_step = 2
        local joker = create_card('Joker', G.jokers, nil, nil, nil, nil, 'j_constellation')
        joker:add_to_deck(); G.jokers:emplace(joker)
        joker:calculate_joker({before=true})
        joker:update_joker_display(true, true, 'browser smoke test')
        assert(joker.children.joker_display, 'JokerDisplay did not create its overlay')
        for i = 1, 2 do
            local card = create_card('Planet', G.consumeables, nil, nil, nil, nil, 'c_pluto')
            card:set_edition({negative=true}, true)
            card:add_to_deck(); G.consumeables:emplace(card)
        end
        assert(#G.consumeables.cards == 1, 'QA duplicate negative planets did not stack')
        local stacked = G.consumeables.cards[1]
        assert(stacked:getQty() == 2, 'QA wrong stack quantity')
        local saved = stacked:save()
        assert(saved.overflow_amount == 2, 'QA stack amount did not serialize')
        print('PROBE NEGATIVE STACK AND SAVE PASSED')
        print('PROBE CONSTELLATION NIL CONTEXT PASSED')
    end
end
