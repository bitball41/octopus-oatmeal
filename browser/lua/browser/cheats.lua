local M = {}
local order = require 'browser.joker_order'
local buffer, last_key = '', 0

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

function M.keypressed(key)
    if not (G and G.STAGES and G.STAGE == G.STAGES.RUN and G.CONTROLLER)
        or G.CONTROLLER.text_input_hook or G.OVERLAY_MENU or G.SETTINGS.paused
        or love.keyboard.isDown('lctrl', 'rctrl', 'lgui', 'rgui', 'lalt', 'ralt') then
        buffer = ''; return
    end
    local now = love.timer.getTime()
    if now - last_key > 3 then buffer = '' end
    last_key = now
    if type(key) ~= 'string' or #key ~= 1 then buffer = ''; return end
    buffer = (buffer .. key:lower()):sub(-7)
    if buffer == 'liminal' then
        buffer = ''
        -- Finish the current input event before changing the card area.
        G.E_MANAGER:add_event(Event({trigger = 'immediate', func = function() M.grant(); return true end}))
    end
end
return M
