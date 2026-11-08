-- Browser probe for Brainstorm Rerolled. validate_brainstorm_browser.mjs
-- splices this in front of browser/brainstorm.lua's final return and drives
-- the keys from Chromium.
local probe_update = love.update
local step, waited = 0, 0
local found_seed, ready_sent, rare_job, rare_started

local function probe(text) print('PROBE ' .. text) end

local function contains(node, wanted, seen)
    if node == wanted then return true end
    if type(node) ~= 'table' then return false end
    seen = seen or {}
    if seen[node] then return false end
    seen[node] = true
    for k, v in pairs(node) do
        if k ~= 'parent' and contains(v, wanted, seen) then return true end
    end
    return false
end

-- Immolate (WebAssembly, in the page) must agree with this game's own rolls.
local function check_predictions()
    local game = G.GAME
    local saved, ante = game.pseudorandom, game.round_resets.ante
    local native = Brainstorm.native
    local tags, vouchers = {}, {}
    for i = 1, 40 do
        local seed = random_string(8, i * 0.1372)
        game.pseudorandom = {seed = seed, hashed_seed = pseudohash(seed)}
        game.round_resets.ante = 1
        local tag = get_next_tag_key()
        local voucher = get_next_voucher_key()
        game.pseudorandom, game.round_resets.ante = saved, ante
        assert(native.check_seed({filter_spec = 'tag ' .. tag .. ' ante=1 blind=small'}, seed) == true,
            'engine disagrees: ' .. seed .. ' small blind tag ' .. tag)
        assert(native.check_seed({filter_spec = 'voucher ' .. voucher .. ' ante=1'}, seed) == true,
            'engine disagrees: ' .. seed .. ' voucher ' .. voucher)
        local other = tag == 'tag_charm' and 'tag_double' or 'tag_charm'
        assert(native.check_seed({filter_spec = 'tag ' .. other .. ' ante=1 blind=small'}, seed) == false,
            'engine accepts the wrong tag for ' .. seed)
        tags[tag], vouchers[voucher] = true, true
    end
    local nt, nv = 0, 0
    for _ in pairs(tags) do nt = nt + 1 end
    for _ in pairs(vouchers) do nv = nv + 1 end
    assert(nt > 8 and nv > 8, 'too little variety in sampled seeds')
end

-- The start seed the page's search job reports.
local function job_start_seed(job)
    local path = 'brainstorm_reply.lua'
    print('callJavascriptFunction window.OctopusBrainstorm.call(' .. Brainstorm.native.encode(love.filesystem.getSaveDirectory()) .. ',{"op":"poll","job":' .. job.id .. '})')
    local reply = assert(love.filesystem.load(path))()
    love.filesystem.remove(path)
    return reply.start_seed
end

local function arcana_has_soul()
    local soul, made = false, {}
    for _ = 1, 5 do
        local card = create_card('Tarot', G.consumeables, nil, nil, true, true, nil, 'ar1')
        made[#made + 1] = card
        if card.config.center.key == 'c_soul' then soul = true end
    end
    for _, card in ipairs(made) do card:remove() end
    return soul
end

function love.update(dt)
    -- First-launch screens (Cryptid's intro, unlock popups) cover the menu.
    if Cryptid and G and G.PROFILES and G.SETTINGS and G.PROFILES[G.SETTINGS.profile] then
        G.PROFILES[G.SETTINGS.profile].cry_intro_complete = true
    end
    probe_update(dt)
    if step == 0 and G and G.STAGES and G.STAGE == G.STAGES.MAIN_MENU and G.OVERLAY_MENU and G.FUNCS.exit_overlay_menu then
        pcall(G.FUNCS.exit_overlay_menu)
    end
    local ok, err = pcall(function()
        if step == 0 and G and G.STAGE == G.STAGES.MAIN_MENU and G.MAIN_MENU_UI and G.P_CENTERS and G.P_CENTERS.j_joker then
            assert(Brainstorm and Brainstorm.initialized, 'Brainstorm Rerolled did not start')
            probe('HANDY ' .. tostring(Handy ~= nil))
            assert(Brainstorm.native and Brainstorm.native.lib, 'search engine unavailable: ' .. tostring(Brainstorm.native_error))
            probe('ENGINE ' .. Brainstorm.native.build_info())
            assert(contains(create_UIBox_settings(), 'Brainstorm-Rerolled'), 'Settings has no Brainstorm-Rerolled tab')
            assert(Brainstorm.FB.settings_tab(), 'settings tab did not build')
            local problem = Brainstorm.FB.problem({conditions = {{kind = 'tag', key = 'tag_bogus', ante = 1, ante_to = 1, blind = 'small'}}})
            assert(problem, 'a bad filter was accepted')
            -- Immolate predicts for a played profile; the test profile is new.
            for _, key in ipairs({'j_blueprint', 'e_foil', 'e_holo', 'e_polychrome', 'e_negative'}) do
                G.P_CENTERS[key].discovered = true
            end
            for _, v in ipairs(G.P_CENTER_POOLS.Joker) do v.unlocked = true end
            Brainstorm.warned_new_profile = true
            -- Use the Charm + Soul starter filter.
            local filters = Brainstorm.config.filters
            for i, f in ipairs(filters.list) do
                if f.name == 'Charm + Soul' then filters.active = i end
            end
            assert(filters.list[filters.active] and filters.list[filters.active].name == 'Charm + Soul', 'no Charm + Soul starter filter')
            probe('MENU PASSED')
            -- A rare filter: progress must climb, then cancel must stop it.
            rare_job = assert(Brainstorm.native.start({start_seed = 'AAAAAAAA', filter_spec =
                'tag tag_charm ante=1 blind=small\nsoul ante=1 packs=1 size=5 legendary=j_perkeo\njoker j_blueprint ante=1 within=2 edition=e_negative'}))
            rare_started = love.timer.getTime()
            step = 0.5
        elseif step == 0.5 then
            local status, seed, checked = Brainstorm.native.poll(rare_job)
            assert(status == 'running' or status == 'found', 'rare search ' .. tostring(status))
            if checked >= 3000000 or status == 'found' then
                Brainstorm.native.cancel(rare_job)
                local after = Brainstorm.native.poll(rare_job)
                assert(status == 'running' and after == 'cancelled', 'search ' .. tostring(status) .. ', then ' .. tostring(after) .. ' after cancel')
                Brainstorm.native.free(rare_job)
                probe(string.format('PROGRESS PASSED %d seeds in %.1fs (%.1fM/s)', checked, love.timer.getTime() - rare_started,
                    checked / math.max(0.001, love.timer.getTime() - rare_started) / 1e6))
                step = 0.75
            end
            assert(love.timer.getTime() - rare_started < 120, 'rare search made no progress')
        elseif step == 0.75 then
            step = 1
            G.SETTINGS.tutorial_complete = true
            G.SETTINGS.tutorial_progress = nil
            G.FUNCS.start_run(nil, {seed = 'BRAINST1'})
        elseif step == 1 and G.STAGE == G.STAGES.RUN and G.GAME.round_resets.blind_tags and G.GAME.round_resets.blind_tags.Small then
            assert(G.GAME.pseudorandom.seed == 'BRAINST1')
            local tag = G.GAME.round_resets.blind_tags.Small
            assert(Brainstorm.native.check_seed({filter_spec = 'tag ' .. tag .. ' ante=1 blind=small'}, 'BRAINST1'), 'engine disagrees with the live run tag')
            check_predictions()
            probe('PREDICTIONS PASSED')
            save_run()
            step = 2
        elseif step == 2 and not G.screenwipe and not ready_sent then
            -- The game ignores keys until the run's screen wipe finishes.
            ready_sent = 'save'
            probe('READY FOR SAVE STATE')
        elseif step == 2 and ready_sent == 'save' and get_compressed(G.SETTINGS.profile .. '/saveState1.jkr') then
            ready_sent = 'auto'
            probe('READY FOR AUTOREROLL')
        elseif step == 2 and Brainstorm.ar_job then
            -- The search must begin at the mod's random start seed.
            local sent = Brainstorm.ar_opts.start_seed
            local job = job_start_seed(Brainstorm.ar_job)
            assert(job == sent, 'search started at ' .. tostring(job) .. ', not the start seed ' .. tostring(sent))
            step = 3
            waited = love.timer.getTime()
            probe('AUTOREROLL STARTED')
        elseif step == 3 and not Brainstorm.ar_job and G.STAGE == G.STAGES.RUN
            and G.GAME.round_resets.blind_tags and G.GAME.pseudorandom.seed ~= 'BRAINST1' then
            found_seed = G.GAME.pseudorandom.seed
            assert(G.GAME.used_filter, 'run was not started by the filter')
            assert(G.GAME.round_resets.blind_tags.Small == 'tag_charm', 'found seed has ' .. tostring(G.GAME.round_resets.blind_tags.Small))
            assert(G.GAME.seeded == false, 'found run should play unseeded')
            assert(arcana_has_soul(), 'found seed has no Soul in the Charm Tag pack')
            probe(string.format('AUTOREROLL PASSED %s in %.1fs (%s)', found_seed, love.timer.getTime() - waited, Brainstorm.ar_status))
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
