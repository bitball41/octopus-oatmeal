local M = {}
local order = require 'browser.joker_order'
local buffer, last_key = '', 0
local lotion_pending, lotion_applying = false, false

local LOTION_JOKERS = {
    'j_baron',
    'j_brainstorm', 'j_brainstorm', 'j_brainstorm', 'j_brainstorm',
    'j_blueprint', 'j_blueprint', 'j_blueprint', 'j_blueprint',
    'j_mime',
}

local LOTION_VOUCHERS = {
    'v_paint_brush', 'v_palette',
    'v_grabber', 'v_nacho_tong',
    'v_directors_cut', 'v_retcon',
    'v_overstock_norm', 'v_overstock_plus',
    'v_clearance_sale', 'v_liquidation',
}

local function run_ready()
    return G and G.STAGES and G.STAGE == G.STAGES.RUN and G.GAME
        and G.jokers and G.consumeables and G.deck and G.hand
        and G.playing_cards and G.P_CENTERS and G.P_CARDS
end

local function modifier_down()
    return love and love.keyboard and love.keyboard.isDown
        and love.keyboard.isDown('lctrl', 'rctrl', 'lgui', 'rgui', 'lalt', 'ralt')
end

local function clear_area(area)
    if not (area and area.cards) then return end
    while #area.cards > 0 do
        local card = area.cards[#area.cards]
        local before = #area.cards
        if card and card.remove_from_deck then pcall(card.remove_from_deck, card) end
        local owner = card and card.area or area
        if owner and owner.remove_card then owner:remove_card(card) end
        if #area.cards == before then table.remove(area.cards, before) end
        if card and card.remove then pcall(card.remove, card) end
    end
end

local function set_plasma_back()
    local plasma = assert(G.P_CENTERS.b_plasma, 'Missing lotion deck: b_plasma')
    if G.GAME.selected_back and G.GAME.selected_back.change_to then
        G.GAME.selected_back:change_to(plasma)
    elseif Back then
        G.GAME.selected_back = Back(plasma)
    end
    G.GAME.starting_params = G.GAME.starting_params or {}
    G.GAME.starting_params.ante_scaling = 2
end

local function reset_run_baseline()
    local p = G.GAME.starting_params or {}
    G.GAME.starting_params = p
    p.hands = 4
    p.discards = 3
    p.hand_size = 8
    p.joker_slots = 10
    p.consumable_slots = 60
    p.reroll_cost = 5
    p.ante_scaling = 2

    if G.GAME.round_resets then
        G.GAME.round_resets.hands = 4
        G.GAME.round_resets.discards = 3
    end
    if G.hand.config then G.hand.config.card_limit = 8 end
    if G.jokers.config then G.jokers.config.card_limit = 10 end
    if G.consumeables.config then G.consumeables.config.card_limit = 60 end

    G.GAME.spectral_rate = 0
    G.GAME.discount_percent = 0
    G.GAME.used_vouchers = {}
    G.GAME.starting_voucher_count = 0
    G.GAME.modifiers = G.GAME.modifiers or {}
    G.GAME.modifiers.no_interest = false
    G.GAME.modifiers.money_per_hand = 1
    G.GAME.modifiers.money_per_discard = 0
end

local function apply_vouchers()
    for _, key in ipairs(LOTION_VOUCHERS) do
        local center = assert(G.P_CENTERS[key], 'Missing lotion Voucher: ' .. key)
        G.GAME.used_vouchers[key] = true
        G.GAME.starting_voucher_count = G.GAME.starting_voucher_count + 1
        Card.apply_to_run(nil, center)
    end
end

local function spawn_lotion_jokers()
    G.jokers.config.card_limit = 10
    for _, key in ipairs(LOTION_JOKERS) do
        local card = create_card('Joker', G.jokers, nil, nil, nil, nil, key, 'lotion')
        if card.set_edition then card:set_edition({polychrome = true}, true, true) end
        card:add_to_deck()
        G.jokers:emplace(card)
    end
    if G.jokers.align_cards then G.jokers:align_cards() end
end

local function remove_playing_card(card)
    if not card then return end
    local area = card.area
    if area and area.remove_card then area:remove_card(card) end
    if card.remove then card:remove() end
end

local function normalize_playing_deck()
    while #G.playing_cards > 52 do
        local card = G.playing_cards[#G.playing_cards]
        remove_playing_card(card)
        table.remove(G.playing_cards)
    end

    G.playing_card = G.playing_card or #G.playing_cards
    while #G.playing_cards < 52 do
        G.playing_card = G.playing_card + 1
        local card = Card(
            G.deck.T.x + G.deck.T.w/2,
            G.deck.T.y + G.deck.T.h/2,
            G.CARD_W, G.CARD_H,
            G.P_CARDS.H_K,
            G.P_CENTERS.m_steel,
            {playing_card = G.playing_card}
        )
        card:add_to_deck()
        card:set_seal('Red', true, true)
        G.deck:emplace(card)
        table.insert(G.playing_cards, card)
    end
    if G.deck.config then G.deck.config.card_limit = 52 end

    local ace = (G.hand.cards and G.hand.cards[1]) or G.playing_cards[1]
    for _, card in ipairs(G.playing_cards) do
        if card == ace then
            card:set_base(G.P_CARDS.H_A, true)
            card:set_ability(G.P_CENTERS.m_glass, true, true)
            card:set_seal('Red', true, true)
            card:set_edition({polychrome = true}, true, true)
        else
            card:set_base(G.P_CARDS.H_K, true)
            card:set_ability(G.P_CENTERS.m_steel, true, true)
            card:set_seal('Red', true, true)
            card:set_edition(nil, true, true)
        end
    end
end

local function spawn_cryptids()
    G.consumeables.config.card_limit = 60
    G.GAME.consumeable_buffer = 0
    for i = 1, 60 do
        local card = create_card('Spectral', G.consumeables, nil, nil, nil, nil, 'c_cryptid', 'lotion')
        card:add_to_deck()
        G.consumeables:emplace(card)
    end
end

local function set_high_card_101()
    local hand = assert(G.GAME.hands and G.GAME.hands['High Card'], 'Missing High Card hand data')
    hand.level = 101
    hand.chips = 1005
    hand.mult = 101
end

function M.grant()
    if not (G and G.STAGE == G.STAGES.RUN and G.jokers and G.GAME) then return false end
    if G.GAME.liminal_granted then return false end
    -- Validate before touching the run, including on older or mismatched builds.
    for _, key in ipairs(order) do
        assert(G.P_CENTERS[key], 'Missing liminal Joker: ' .. key)
    end
    local existing, sorted, used = {}, {}, {}
    for _, card in ipairs(G.jokers.cards) do
        local key = card.config.center.key
        if not existing[key] then existing[key] = card end
    end
    local missing = 0
    for _, key in ipairs(order) do if not existing[key] then missing = missing + 1 end end
    G.jokers.config.card_limit = math.max(G.jokers.config.card_limit, #G.jokers.cards + missing)
    for _, key in ipairs(order) do
        local card = existing[key]
        if not card then
            card = create_card('Joker', G.jokers, nil, nil, nil, nil, key, 'liminal')
            card:add_to_deck()
            G.jokers:emplace(card)
        end
        sorted[#sorted + 1] = card
        used[card] = true
    end
    -- Keep any pre-existing extra copies after the supplied 148-card order.
    for _, card in ipairs(G.jokers.cards) do
        if not used[card] then sorted[#sorted + 1] = card end
    end
    G.jokers.cards = sorted
    G.GAME.liminal_granted = true
    if G.jokers.align_cards then G.jokers:align_cards() end
    return true
end

function M.grant_lotion()
    if not run_ready() then return false end
    if G.GAME.lotion_granted then return true end

    -- Fail before mutating anything if this build is missing a required vanilla center.
    assert(G.P_CENTERS.b_plasma, 'Missing lotion deck: b_plasma')
    assert(G.P_CENTERS.m_steel and G.P_CENTERS.m_glass, 'Missing lotion card enhancements')
    assert(G.P_CENTERS.c_cryptid, 'Missing lotion consumable: c_cryptid')
    assert(G.P_CARDS.H_K and G.P_CARDS.H_A, 'Missing lotion Hearts card fronts')
    for _, key in ipairs(LOTION_JOKERS) do assert(G.P_CENTERS[key], 'Missing lotion Joker: ' .. key) end
    for _, key in ipairs(LOTION_VOUCHERS) do assert(G.P_CENTERS[key], 'Missing lotion Voucher: ' .. key) end

    -- Remove old run inventory first so its add/remove hooks cannot contaminate the preset.
    clear_area(G.jokers)
    clear_area(G.consumeables)

    reset_run_baseline()
    set_plasma_back()
    apply_vouchers()
    spawn_lotion_jokers()
    normalize_playing_deck()
    spawn_cryptids()
    set_high_card_101()
    G.GAME.dollars = 300
    G.GAME.lotion_granted = true
    return true
end

function M.poll()
    if not lotion_pending or lotion_applying or not run_ready() then return false end
    if G.GAME.lotion_granted then lotion_pending = false; return false end
    lotion_applying = true

    local function apply()
        local ok, applied = pcall(M.grant_lotion)
        lotion_applying = false
        if not ok then
            lotion_pending = false
            print('[lotion] cheat failed: ' .. tostring(applied))
        elseif applied then
            lotion_pending = false
        end
        return true
    end

    if G.E_MANAGER and Event then
        G.E_MANAGER:add_event(Event({trigger = 'immediate', func = apply}))
    else
        apply()
    end
    return true
end

function M.keypressed(key)
    if (G and G.CONTROLLER and G.CONTROLLER.text_input_hook) or modifier_down() then
        buffer = ''; return
    end
    local now = love.timer.getTime()
    if now - last_key > 3 then buffer = '' end
    last_key = now
    if type(key) ~= 'string' or #key ~= 1 then buffer = ''; return end
    buffer = (buffer .. key:lower()):sub(-7)

    if buffer == 'liminal' then
        buffer = ''
        if run_ready() and G.E_MANAGER and Event then
            -- Finish the current input event before changing the card area.
            G.E_MANAGER:add_event(Event({trigger = 'immediate', func = function() M.grant(); return true end}))
        end
    elseif buffer:sub(-6) == 'lotion' then
        buffer = ''
        lotion_pending = true
        M.poll()
    end
end

return M
