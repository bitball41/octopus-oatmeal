-- Browser probe for Brainstorm. validate_brainstorm_browser.mjs splices this
-- in front of brainstorm.lua's final return and drives the keys from Chromium.
local probe_update = love.update
local step, waited = 0, 0
local found_seed, ready_sent

local function probe(text) print('PROBE ' .. text) end

local function contains(node, wanted, seen)
    if node == wanted then return true end
    if type(node) ~= 'table' then return false end
    seen = seen or {}
    if seen[node] then return false end
    seen[node] = true
    for k, v in pairs(node) do
        if k ~= 'parent' and (contains(v, wanted, seen)) then return true end
    end
    return false
end

local function check_predictions()
    local game = G.GAME
    local saved, ante, first = game.pseudorandom, game.round_resets.ante, game.first_shop_buffoon
    local tags, packs = {}, {}
    for i = 1, 300 do
        local seed = random_string(8, i * 0.1372)
        local predictor = Brainstorm.predictor(seed)
        local predicted_tag = Brainstorm.first_tag(predictor)
        local predicted_pack = Brainstorm.first_shop_pack(predictor)
        game.pseudorandom = {seed = seed, hashed_seed = pseudohash(seed)}
        game.round_resets.ante = 1
        local actual_tag = get_next_tag_key()
        game.first_shop_buffoon = true
        local actual_pack = get_pack('shop_pack').key
        assert(game.pseudorandom.seed == seed and game.round_resets.ante == 1, 'prediction leaked into the run state')
        assert(predicted_tag == actual_tag, 'tag mismatch for ' .. seed .. ': ' .. tostring(predicted_tag) .. ' vs ' .. tostring(actual_tag))
        assert(predicted_pack == actual_pack, 'pack mismatch for ' .. seed .. ': ' .. tostring(predicted_pack) .. ' vs ' .. tostring(actual_pack))
        tags[actual_tag], packs[actual_pack] = true, true
    end
    game.pseudorandom, game.round_resets.ante, game.first_shop_buffoon = saved, ante, first
    -- Predicting must leave the live run's RNG state untouched.
    local before = {}
    for k, v in pairs(game.pseudorandom) do before[k] = v end
    Brainstorm.seed_matches('ZZZZ1234', {searchTag = 'tag_charm', searchForSoul = 2, searchPack = {'p_arcana_mega_1'}})
    for k, v in pairs(before) do assert(game.pseudorandom[k] == v, 'live RNG changed: ' .. tostring(k)) end
    for k in pairs(game.pseudorandom) do assert(before[k] ~= nil, 'live RNG gained ' .. tostring(k)) end
    local nt, np = 0, 0
    for _ in pairs(tags) do nt = nt + 1 end
    for _ in pairs(packs) do np = np + 1 end
    assert(nt > 10 and np > 10, 'too little variety in sampled seeds')
end

local function arcana_has_soul()
    local soul = false
    local made = {}
    for _ = 1, 5 do
        local card = create_card('Tarot', G.consumeables, nil, nil, true, true, nil, 'ar1')
        made[#made + 1] = card
        if card.config.center.key == 'c_soul' then soul = true end
    end
    for _, card in ipairs(made) do card:remove() end
    return soul
end

function love.update(dt)
    -- Cryptid opens with a paused first-launch intro; mark it seen.
    if Cryptid and G and G.PROFILES and G.SETTINGS and G.PROFILES[G.SETTINGS.profile] then
        G.PROFILES[G.SETTINGS.profile].cry_intro_complete = true
    end
    probe_update(dt)
    -- First-launch unlock popups (e.g. Cryptid's Blue Deck) cover the menu.
    if step == 0 and G and G.STAGES and G.STAGE == G.STAGES.MAIN_MENU and G.OVERLAY_MENU and G.FUNCS.exit_overlay_menu then
        pcall(G.FUNCS.exit_overlay_menu)
    end
    local ok, err = pcall(function()
        if step == 0 and G and G.STAGE == G.STAGES.MAIN_MENU and G.MAIN_MENU_UI and G.P_CENTERS and G.P_CENTERS.j_joker then
            assert(Brainstorm and Brainstorm.INITIALIZED, 'Brainstorm did not load')
            assert(contains(create_UIBox_settings(), 'Brainstorm'), 'Settings has no Brainstorm tab')
            assert(Brainstorm.settings_tab(), 'Brainstorm tab did not build')
            assert(contains(G.UIDEF.settings_tab('Game'), 32), 'Game speed 32 was not added')
            probe('MENU PASSED')
            step = 1
            -- A fresh browser profile is mid-tutorial, which forces the first tags.
            G.SETTINGS.tutorial_complete = true
            G.SETTINGS.tutorial_progress = nil
            G.FUNCS.start_run(nil, {seed = 'BRAINST1'})
        elseif step == 1 and G.STAGE == G.STAGES.RUN and G.GAME.round_resets.blind_tags and G.GAME.round_resets.blind_tags.Small then
            assert(G.GAME.pseudorandom.seed == 'BRAINST1')
            local predicted = Brainstorm.first_tag(Brainstorm.predictor('BRAINST1'))
            assert(G.GAME.round_resets.blind_tags.Small == predicted, 'live run tag ' .. tostring(G.GAME.round_resets.blind_tags.Small) .. ' differs from prediction ' .. tostring(predicted))
            check_predictions()
            probe('PREDICTIONS PASSED')
            local opts = Brainstorm.SETTINGS.autoreroll
            local t0, n = love.timer.getTime(), 0
            while love.timer.getTime() - t0 < 1 do
                Brainstorm.seed_matches(Brainstorm.next_candidate(), opts)
                n = n + 1
            end
            probe(string.format('SEARCH RATE %d seeds/s', n / (love.timer.getTime() - t0)))
            save_run()
            assert(Brainstorm.save_state('1'), 'save state failed')
            assert(get_compressed(G.SETTINGS.profile .. '/saveState1.jkr'), 'save state was not written')
            step = 2
        elseif step == 2 and not G.screenwipe and not ready_sent then
            -- The game ignores keys until the run's screen wipe finishes.
            ready_sent = true
            probe('READY FOR AUTOREROLL')
        elseif step == 2 and Brainstorm.AUTOREROLL.autoRerollActive then
            step = 3
            waited = love.timer.getTime()
            probe('AUTOREROLL STARTED')
        elseif step == 3 and not Brainstorm.AUTOREROLL.autoRerollActive and G.STAGE == G.STAGES.RUN
            and G.GAME.round_resets.blind_tags and G.GAME.pseudorandom.seed ~= 'BRAINST1' then
            found_seed = G.GAME.pseudorandom.seed
            assert(G.GAME.round_resets.blind_tags.Small == 'tag_charm', 'found seed has ' .. tostring(G.GAME.round_resets.blind_tags.Small))
            assert(G.GAME.seeded == false, 'found run should play unseeded')
            assert(arcana_has_soul(), 'found seed has no Soul in the Charm Tag pack')
            probe(string.format('AUTOREROLL PASSED %s after %d seeds in %.1fs', found_seed, Brainstorm.AUTOREROLL.seedsChecked or -1, love.timer.getTime() - waited))
            step = 4
        elseif step == 4 and not G.screenwipe and ready_sent ~= 4 then
            ready_sent = 4
            probe('READY FOR FAST REROLL')
        elseif step == 4 and ready_sent == 4 and G.STAGE == G.STAGES.RUN and G.GAME.pseudorandom.seed ~= found_seed and G.GAME.round_resets.blind_tags then
            probe('FAST REROLL PASSED ' .. G.GAME.pseudorandom.seed)
            step = 5
        elseif step == 5 and not G.screenwipe and ready_sent ~= 5 then
            ready_sent = 5
            probe('READY FOR LOAD STATE')
        elseif step == 5 and ready_sent == 5 and G.STAGE == G.STAGES.RUN and G.GAME.pseudorandom.seed == 'BRAINST1' then
            probe('LOAD STATE PASSED')
            probe('BRAINSTORM ALL PASSED')
            step = 6
        end
    end)
    if not ok then
        step = 99
        probe('FAILED ' .. tostring(err))
    end
end
