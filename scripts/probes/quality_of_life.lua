local qa_update = love.update
local qa_step = 0
local qa_until, qa_deadline
local qa_perkeo, qa_plain, qa_limit

-- Events (copies, merges, dissolves) run slowly under software rendering.
-- Wait for the expected state, or 20 seconds, before the step's checks.
local function qa_await(condition)
    qa_until = condition
    qa_deadline = love.timer.getTime() + 20
end

local function qa_fools()
    local plain, negative = {}, {}
    for _, card in ipairs(G.consumeables.cards) do
        assert(card.config.center.key == 'c_fool', 'QA Perkeo copied an unexpected card '..card.config.center.key)
        if card.edition and card.edition.negative then negative[#negative+1] = card else plain[#plain+1] = card end
    end
    return plain, negative
end

local function qa_stacks()
    local plain, negative = qa_fools()
    return #plain == 1 and #negative == 1 and plain[1]:getQty(), #negative == 1 and #plain == 1 and negative[1]:getQty()
end

local function qa_trigger_perkeo(pick)
    local choose = pseudorandom_element
    if pick then pseudorandom_element = function() return pick end end
    local ok, err = pcall(qa_perkeo.calculate_joker, qa_perkeo, {ending_shop = true})
    pseudorandom_element = choose
    assert(ok, err)
end

function love.update(dt)
    qa_update(dt)
    if qa_until then
        if not qa_until() and love.timer.getTime() < qa_deadline then return end
        qa_until = nil
    end
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
        qa_limit = G.consumeables.config.card_limit
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
        stacked:remove()
        qa_await(function() return #G.consumeables.cards == 0 and G.consumeables.config.card_limit == qa_limit end)
    elseif qa_step == 2 then
        qa_step = 3
        assert(#G.consumeables.cards == 0 and G.consumeables.config.card_limit == qa_limit, 'QA consumables were not cleared')
        qa_perkeo = create_card('Joker', G.jokers, nil, nil, nil, nil, 'j_perkeo')
        qa_perkeo:add_to_deck(); G.jokers:emplace(qa_perkeo)
        qa_plain = create_card('Tarot', G.consumeables, nil, nil, nil, nil, 'c_fool')
        qa_plain:add_to_deck(); G.consumeables:emplace(qa_plain)
        qa_trigger_perkeo()
        qa_await(function() local _, negative = qa_fools(); return #negative == 1 end)
    elseif qa_step == 3 then
        qa_step = 4
        local plain, negative = qa_fools()
        assert(#plain == 1 and #negative == 1, ('QA Perkeo made %d plain and %d negative cards, expected 1 negative'):format(#plain - 1, #negative))
        print('PROBE PERKEO NEGATIVE COPY PASSED')
        qa_trigger_perkeo()
        qa_await(function()
            local plain_qty, negative_qty = qa_stacks()
            return plain_qty == 1 and negative_qty == 2 and G.consumeables.config.card_limit == qa_limit + 1 and G.consumeables.config.card_count == 2
        end)
    elseif qa_step == 4 then
        qa_step = 5
        local plain_qty, negative_qty = qa_stacks()
        assert(plain_qty == 1 and negative_qty == 2, ('QA second Perkeo copy gave plain %s, negative %s stacks; expected 1 and 2'):format(tostring(plain_qty), tostring(negative_qty)))
        assert(G.consumeables.config.card_limit == qa_limit + 1, ('QA consumable limit %d, expected %d'):format(G.consumeables.config.card_limit, qa_limit + 1))
        assert(G.consumeables.config.card_count == 2, ('QA negative stack uses %d slots, expected 2'):format(G.consumeables.config.card_count))
        print('PROBE PERKEO NEGATIVE STACK SLOTS PASSED')
        -- With "Only stack negative consumables" off, a stacked plain pick must still yield a negative copy.
        -- A loaded card has no materialize marker, so Overflow treats it as mergeable.
        Overflow.config.only_stack_negatives = false
        qa_plain.dissolve = nil
        Overflow.set_amount(qa_plain, 2)
        qa_trigger_perkeo(qa_plain)
        qa_await(function() local _, negative_qty = qa_stacks(); return negative_qty == 3 end)
    elseif qa_step == 5 then
        qa_step = 6
        Overflow.config.only_stack_negatives = true
        local plain_qty, negative_qty = qa_stacks()
        assert(plain_qty == 2 and negative_qty == 3, ('QA Perkeo on a plain stack gave plain %s, negative %s; expected 2 and 3'):format(tostring(plain_qty), tostring(negative_qty)))
        print('PROBE PERKEO PLAIN STACK PASSED')
    end
end
