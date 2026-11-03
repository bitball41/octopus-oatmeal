-- Brainstorm for the browser builds.
--
-- Port of Brainstorm v1.1.0-alpha by OceanRamen
-- (https://github.com/OceanRamen/Brainstorm, commit 9a8fd6a, MPL-2.0).
-- This file is a modified version of that work and remains under the
-- Mozilla Public License 2.0: https://mozilla.org/MPL/2.0/
--
-- Browser changes from upstream:
-- * Lovely patches become function hooks, so the same file runs on the
--   Vanilla archive and on every Steamodded custom build.
-- * nativefs/mod-folder settings become a file in the save directory.
-- * Ctrl+T opens a browser tab and cannot reach the page, so the reroll keys
--   use Shift (Ctrl still works where the browser lets the key through).
-- * Held keys come from the game's controller: love.keyboard.isDown always
--   reports false in the browser runtime.
-- * Auto-reroll asks the game's own tag and pack functions about each
--   candidate (exact on Vanilla and Steamodded builds), draws candidate
--   seeds cheaply, and stops each frame after a time budget so the
--   page stays responsive.
-- * Typing into a text box (seed entry) never triggers a Brainstorm key, and
--   rerolls/save-states are disabled inside a Multiplayer lobby.

Brainstorm = Brainstorm or {}
if Brainstorm.INITIALIZED then return Brainstorm end
Brainstorm.INITIALIZED = true
Brainstorm.VER = 'Brainstorm v1.1.0-alpha (browser)'

local SETTINGS_FILE = 'brainstorm_settings.jkr'

Brainstorm.SearchTagList = {
    ['None'] = '',
    ['Uncommon Tag'] = 'tag_uncommon',
    ['Rare Tag'] = 'tag_rare',
    ['Holographic Tag'] = 'tag_holo',
    ['Foil Tag'] = 'tag_foil',
    ['Polychrome Tag'] = 'tag_polychrome',
    ['Investment Tag'] = 'tag_investment',
    ['Voucher Tag'] = 'tag_voucher',
    ['Boss Tag'] = 'tag_boss',
    ['Charm Tag'] = 'tag_charm',
    ['Juggle Tag'] = 'tag_juggle',
    ['Double Tag'] = 'tag_double',
    ['Coupon Tag'] = 'tag_coupon',
    ['Economy Tag'] = 'tag_economy',
    ['Skip Tag'] = 'tag_skip',
    ['D6 Tag'] = 'tag_d_six',
}

Brainstorm.SearchPackList = {
    ['None'] = {},
    ['Arcana'] = {'p_arcana_normal_1', 'p_arcana_normal_2', 'p_arcana_normal_3', 'p_arcana_normal_4', 'p_arcana_jumbo_1', 'p_arcana_jumbo_2', 'p_arcana_mega_1', 'p_arcana_mega_2'},
    ['Celestial'] = {'p_celestial_normal_1', 'p_celestial_normal_2', 'p_celestial_normal_3', 'p_celestial_normal_4', 'p_celestial_jumbo_1', 'p_celestial_jumbo_2', 'p_celestial_mega_1', 'p_celestial_mega_2'},
    ['Standard'] = {'p_standard_normal_1', 'p_standard_normal_2', 'p_standard_normal_3', 'p_standard_normal_4', 'p_standard_jumbo_1', 'p_standard_jumbo_2', 'p_standard_mega_1', 'p_standard_mega_2'},
    ['Buffoon'] = {'p_buffoon_normal_1', 'p_buffoon_normal_2', 'p_buffoon_jumbo_1', 'p_buffoon_mega_1'},
    ['Spectral'] = {'p_spectral_normal_1', 'p_spectral_normal_2', 'p_spectral_jumbo_1', 'p_spectral_mega_1'},
    ['Normal Arcana'] = {'p_arcana_normal_1', 'p_arcana_normal_2', 'p_arcana_normal_3', 'p_arcana_normal_4'},
    ['Jumbo Arcana'] = {'p_arcana_jumbo_1', 'p_arcana_jumbo_2'},
    ['Mega Arcana'] = {'p_arcana_mega_1', 'p_arcana_mega_2'},
    ['Normal Celestial'] = {'p_celestial_normal_1', 'p_celestial_normal_2', 'p_celestial_normal_3', 'p_celestial_normal_4'},
    ['Jumbo Celestial'] = {'p_celestial_jumbo_1', 'p_celestial_jumbo_2'},
    ['Mega Celestial'] = {'p_celestial_mega_1', 'p_celestial_mega_2'},
    ['Normal Standard'] = {'p_standard_normal_1', 'p_standard_normal_2', 'p_standard_normal_3', 'p_standard_normal_4'},
    ['Jumbo Standard'] = {'p_standard_jumbo_1', 'p_standard_jumbo_2'},
    ['Mega Standard'] = {'p_standard_mega_1', 'p_standard_mega_2'},
    ['Normal Buffoon'] = {'p_buffoon_normal_1', 'p_buffoon_normal_2'},
    ['Jumbo Buffoon'] = {'p_buffoon_jumbo_1'},
    ['Mega Buffoon'] = {'p_buffoon_mega_1'},
    ['Normal Spectral'] = {'p_spectral_normal_1', 'p_spectral_normal_2'},
    ['Jumbo Spectral'] = {'p_spectral_jumbo_1'},
    ['Mega Spectral'] = {'p_spectral_mega_1'},
}

Brainstorm.seedsPerFrame = {['500'] = 500, ['750'] = 750, ['1000'] = 1000}

local searchTagKeys = {'None', 'Charm Tag', 'Double Tag', 'Uncommon Tag', 'Rare Tag', 'Holographic Tag', 'Foil Tag', 'Polychrome Tag', 'Investment Tag', 'Voucher Tag', 'Boss Tag', 'Juggle Tag', 'Coupon Tag', 'Economy Tag', 'Skip Tag', 'D6 Tag'}
local searchPackKeys = {'None', 'Arcana', 'Celestial', 'Standard', 'Buffoon', 'Spectral', 'Normal Arcana', 'Jumbo Arcana', 'Mega Arcana', 'Normal Celestial', 'Jumbo Celestial', 'Mega Celestial', 'Normal Standard', 'Jumbo Standard', 'Mega Standard', 'Normal Buffoon', 'Jumbo Buffoon', 'Mega Buffoon', 'Normal Spectral', 'Jumbo Spectral', 'Mega Spectral'}
local seedsPerFrameKeys = {'500', '750', '1000'}
Brainstorm.searchTagKeys, Brainstorm.searchPackKeys = searchTagKeys, searchPackKeys

-- Upstream defaults, except no pack filter: Charm Tag + Mega Spectral + Soul
-- needs about half a million seeds, far too many for the browser's Lua.
local function default_settings()
    return {
        debug_mode = false,
        keybinds = {saveState = 'z', loadState = 'x', rerollSeed = 't', autoReroll = 'a'},
        autoreroll = {
            searchTagID = 2, searchTag = 'tag_charm',
            searchPackID = 1, searchPack = {},
            searchForSoul = 1,
            seedsPerFrameID = 3, seedsPerFrame = 1000,
        },
    }
end

local function merge(into, from)
    for k, v in pairs(from) do
        if type(v) == 'table' and type(into[k]) == 'table' then merge(into[k], v)
        elseif into[k] == nil then into[k] = v end
    end
    return into
end

function Brainstorm.load_settings()
    local settings
    local ok, info = pcall(love.filesystem.getInfo, SETTINGS_FILE)
    if ok and info then
        local read_ok, text = pcall(love.filesystem.read, SETTINGS_FILE)
        if read_ok and type(text) == 'string' and STR_UNPACK then
            local unpack_ok, value = pcall(STR_UNPACK, text)
            if unpack_ok and type(value) == 'table' then settings = value end
        end
    end
    settings = merge(settings or {}, default_settings())
    local ar = settings.autoreroll
    -- Keep the IDs authoritative so the option cycles always match the search.
    ar.searchTagID = math.max(1, math.min(#searchTagKeys, tonumber(ar.searchTagID) or 1))
    ar.searchTag = Brainstorm.SearchTagList[searchTagKeys[ar.searchTagID]]
    ar.searchPackID = math.max(1, math.min(#searchPackKeys, tonumber(ar.searchPackID) or 1))
    ar.searchPack = Brainstorm.SearchPackList[searchPackKeys[ar.searchPackID]]
    ar.searchForSoul = math.max(0, math.min(2, tonumber(ar.searchForSoul) or 0))
    ar.seedsPerFrameID = math.max(1, math.min(#seedsPerFrameKeys, tonumber(ar.seedsPerFrameID) or 3))
    ar.seedsPerFrame = Brainstorm.seedsPerFrame[seedsPerFrameKeys[ar.seedsPerFrameID]]
    Brainstorm.SETTINGS = settings
    return settings
end

function Brainstorm.save_settings()
    if not (STR_PACK and Brainstorm.SETTINGS) then return end
    pcall(love.filesystem.write, SETTINGS_FILE, STR_PACK(Brainstorm.SETTINGS))
end

Brainstorm.load_settings()

Brainstorm.AUTOREROLL = {
    autoRerollActive = false,
    rerollInterval = 0.01, -- seconds between search batches
    rerollTimer = 0,
    -- Wall-clock limit per batch. The browser runs Lua without a JIT, so a
    -- full 1000-seed batch could otherwise freeze the tab for seconds.
    frameBudget = 0.05,
    seedsChecked = 0,
}

local function in_run()
    return G and G.STAGES and G.STAGE == G.STAGES.RUN and G.GAME
end

local function in_multiplayer_lobby()
    return type(MP) == 'table' and type(MP.LOBBY) == 'table' and MP.LOBBY.code ~= nil
end

-- love.keyboard.isDown always reports false in the browser runtime, so use the
-- keys the game's controller is holding (it tracks every press and release).
-- A key pressed or released during this frame also counts, so a quick
-- Shift+T tap still registers when a slow frame swallows the Shift.
local function key_down(...)
    local controller = G and G.CONTROLLER
    if controller then
        for i = 1, select('#', ...) do
            local key = select(i, ...)
            if (controller.held_keys and controller.held_keys[key])
                or (controller.pressed_keys and controller.pressed_keys[key])
                or (controller.released_keys and controller.released_keys[key]) then
                return true
            end
        end
    end
    return love and love.keyboard and love.keyboard.isDown and love.keyboard.isDown(...) or false
end

local function modifier_down()
    return key_down('lshift', 'rshift', 'lctrl', 'rctrl')
end

-- ---------------------------------------------------------------------------
-- Alerts (upstream saveManagerAlert / attention_text helpers)

function saveManagerAlert(text)
    if not (G and G.E_MANAGER and Event) then return end
    G.E_MANAGER:add_event(Event({
        trigger = 'after',
        delay = 0.4,
        func = function()
            attention_text({
                text = text,
                scale = 0.7,
                hold = 3,
                major = G.STAGE == G.STAGES.RUN and G.play or G.title_top,
                backdrop_colour = G.C.SECONDARY_SET.Tarot,
                align = 'cm',
                offset = {x = 0, y = -3.5},
                silent = true,
            })
            G.E_MANAGER:add_event(Event({
                trigger = 'after',
                delay = 0.06 * G.SETTINGS.GAMESPEED,
                blockable = false,
                blocking = false,
                func = function()
                    play_sound('other1', 0.76, 0.4)
                    return true
                end,
            }))
            return true
        end,
    }))
end
Brainstorm.alert = saveManagerAlert

-- Based on Balatro's attention_text, without the automatic removal.
function Brainstorm.attention_text(args)
    args = args or {}
    args.text = args.text or 'test'
    args.scale = args.scale or 1
    args.colour = copy_table(args.colour or G.C.WHITE)
    args.hold = (args.hold or 0) + 0.1 * (G.SPEEDFACTOR)
    args.pos = args.pos or {x = 0, y = 0}
    args.align = args.align or 'cm'
    args.emboss = args.emboss or nil
    args.fade = 1
    if args.cover then
        args.cover_colour = copy_table(args.cover_colour or G.C.RED)
        args.cover_colour_l = copy_table(lighten(args.cover_colour, 0.2))
        args.cover_colour_d = copy_table(darken(args.cover_colour, 0.2))
    else
        args.cover_colour = copy_table(G.C.CLEAR)
    end
    args.uibox_config = {
        align = args.align or 'cm',
        offset = args.offset or {x = 0, y = 0},
        major = args.cover or args.major or nil,
    }
    G.E_MANAGER:add_event(Event({
        trigger = 'after',
        delay = 0,
        blockable = false,
        blocking = false,
        func = function()
            args.AT = UIBox{
                T = {args.pos.x, args.pos.y, 0, 0},
                definition = {n = G.UIT.ROOT, config = {align = args.cover_align or 'cm', minw = (args.cover and args.cover.T.w or 0.001) + (args.cover_padding or 0), minh = (args.cover and args.cover.T.h or 0.001) + (args.cover_padding or 0), padding = 0.03, r = 0.1, emboss = args.emboss, colour = args.cover_colour}, nodes = {
                    {n = G.UIT.O, config = {draw_layer = 1, object = DynaText({scale = args.scale, string = args.text, maxw = args.maxw, colours = {args.colour}, float = true, shadow = true, silent = not args.noisy, pop_in = 0, pop_in_rate = 6, rotate = args.rotate or nil})}},
                }},
                config = args.uibox_config,
            }
            args.AT.attention_text = true
            args.text = args.AT.UIRoot.children[1].config.object
            args.text:pulse(0.5)
            return true
        end,
    }))
    return args
end

function Brainstorm.remove_attention_text(args)
    G.E_MANAGER:add_event(Event({
        trigger = 'after',
        delay = 0,
        blockable = false,
        blocking = false,
        func = function()
            if not args.AT then return true end
            if not args.start_time then
                args.start_time = G.TIMERS.TOTAL
                args.text:pop_out(3)
            else
                args.fade = math.max(0, 1 - 3 * (G.TIMERS.TOTAL - args.start_time))
                if args.cover_colour then args.cover_colour[4] = math.min(args.cover_colour[4], 2 * args.fade) end
                if args.cover_colour_l then args.cover_colour_l[4] = math.min(args.cover_colour_l[4], args.fade) end
                if args.cover_colour_d then args.cover_colour_d[4] = math.min(args.cover_colour_d[4], args.fade) end
                if args.backdrop_colour then args.backdrop_colour[4] = math.min(args.backdrop_colour[4], args.fade) end
                args.colour[4] = math.min(args.colour[4], args.fade)
                if args.fade <= 0 then
                    args.AT:remove()
                    return true
                end
            end
        end,
    }))
end

-- ---------------------------------------------------------------------------
-- Seed prediction

-- Runs the game's own functions against a candidate seed's fresh RNG state
-- on ante 1, so a seed is judged exactly as a new run would roll it (on
-- Vanilla and on Steamodded builds, whose tag and pack rules differ) without
-- touching the current run.
function Brainstorm.predictor(seed)
    local state = {seed = seed, hashed_seed = pseudohash(seed)}
    local predictor = {}
    function predictor.run(fn, ...)
        local game = G.GAME
        local resets = game.round_resets
        local saved_state, saved_ante, saved_buffoon = game.pseudorandom, resets.ante, game.first_shop_buffoon
        game.pseudorandom, resets.ante = state, 1
        -- The first shop's first pack is always a Buffoon pack; this asks for the other one.
        game.first_shop_buffoon = true
        local ok, value = pcall(fn, ...)
        game.pseudorandom, resets.ante, game.first_shop_buffoon = saved_state, saved_ante, saved_buffoon
        if not ok then error(value, 0) end
        return value
    end
    function predictor.roll(key) return predictor.run(pseudoseed, key) end
    return predictor
end

-- The small blind's skip tag.
function Brainstorm.first_tag(predictor)
    return predictor.run(get_next_tag_key)
end

-- The first shop's second pack.
function Brainstorm.first_shop_pack(predictor)
    local center = predictor.run(get_pack, 'shop_pack')
    return center and center.key
end

-- Upstream's soul search: each requested Soul must appear in a five-card
-- Arcana pack on ante 1 (the Charm Tag's Mega Arcana, then the next one).
-- Once a pack shows The Soul, its remaining cards skip the soul roll (the
-- game checks used_jokers first), so that pack stops consuming the stream.
function Brainstorm.souls_found(predictor, wanted)
    for _ = 1, wanted do
        local found = false
        for _ = 1, 5 do
            if pseudorandom(predictor.roll('soul_Tarot1')) > 0.997 then found = true; break end
        end
        if not found then return false end
    end
    return true
end

function Brainstorm.seed_matches(seed, opts)
    opts = opts or Brainstorm.SETTINGS.autoreroll
    local predictor = Brainstorm.predictor(seed)
    if opts.searchTag and opts.searchTag ~= '' then
        if Brainstorm.first_tag(predictor) ~= opts.searchTag then return false end
    end
    if (opts.searchForSoul or 0) > 0 and not Brainstorm.souls_found(predictor, opts.searchForSoul) then
        return false
    end
    if opts.searchPack and #opts.searchPack > 0 then
        local pack = Brainstorm.first_shop_pack(predictor)
        local ok = false
        for _, key in ipairs(opts.searchPack) do
            if key == pack then ok = true; break end
        end
        if not ok then return false end
    end
    return true
end

local function current_challenge()
    return G.GAME and G.GAME.challenge and G.GAME.challenge_tab or nil
end

local function restart(seed)
    local stake = G.GAME.stake or 1
    local challenge = current_challenge()
    G:delete_run()
    G:start_run({stake = stake, seed = seed, challenge = challenge})
end

function FastReroll()
    if not in_run() then return end
    G.GAME.viewed_back = nil
    G.run_setup_seed = G.GAME.seeded
    G.challenge_tab = current_challenge()
    G.forced_seed, G.setup_seed = nil, nil
    if G.GAME.seeded then
        G.forced_seed = G.GAME.pseudorandom.seed
    end
    local seed = G.run_setup_seed and G.setup_seed or G.forced_seed or nil
    local challenge = G.challenge_tab
    local stake = challenge and 1 or (G.GAME.stake or G.PROFILES[G.SETTINGS.profile].MEMORY.stake or 1)
    G:delete_run()
    G:start_run({stake = stake, seed = seed, challenge = challenge})
end
Brainstorm.fast_reroll = FastReroll

-- Candidate seeds. Upstream reseeds math.random for every candidate (like
-- Balatro's own seed picker), but the browser's math.random is a pure-Lua
-- port of LuaJIT's generator and that alone was most of the search time.
-- A Park-Miller generator draws from the same 34 characters seeds use (no 0
-- or O) for a fraction of the cost, and leaves math.random untouched.
local SEED_CHARS = '123456789ABCDEFGHIJKLMNPQRSTUVWXYZ'
local candidate_state
local function next_candidate()
    if not candidate_state then
        local hover = G.CONTROLLER and G.CONTROLLER.cursor_hover or {}
        local T = hover.T or {}
        local mix = (os.time() % 1000003) * 7919 + love.timer.getTime() * 1000003
            + (T.x or 0) * 334119.83 + (T.y or 0) * 874146 + (hover.time or 0) * 412311
        candidate_state = math.floor(math.abs(mix)) % 2147483646 + 1
    end
    local chars = {}
    for i = 1, 8 do
        candidate_state = (candidate_state * 48271) % 2147483647
        local index = candidate_state % 34 + 1
        chars[i] = SEED_CHARS:sub(index, index)
    end
    return table.concat(chars)
end
Brainstorm.next_candidate = next_candidate

function Brainstorm.auto_reroll()
    local ar = Brainstorm.AUTOREROLL
    local opts = Brainstorm.SETTINGS.autoreroll
    local started = love.timer.getTime()
    local checked, seed_found = 0, nil
    while not seed_found and checked < opts.seedsPerFrame do
        checked = checked + 1
        local candidate = next_candidate()
        if Brainstorm.seed_matches(candidate, opts) then seed_found = candidate end
        if love.timer.getTime() - started > ar.frameBudget then break end
    end
    ar.seedsChecked = (ar.seedsChecked or 0) + checked
    if seed_found then
        restart(seed_found)
        -- Like upstream: the run plays as an unseeded run.
        G.GAME.seeded = false
    end
    return seed_found
end

function Brainstorm.stop_auto_reroll()
    local ar = Brainstorm.AUTOREROLL
    ar.autoRerollActive = false
    ar.autoRerollFrames = 0
    ar.rerollTimer = 0
    if ar.rerollText then
        Brainstorm.remove_attention_text(ar.rerollText)
        ar.rerollText = nil
    end
end

function Brainstorm.toggle_auto_reroll()
    local ar = Brainstorm.AUTOREROLL
    if ar.autoRerollActive then
        Brainstorm.stop_auto_reroll()
        saveManagerAlert('Auto-reroll stopped')
        return
    end
    if not in_run() then return end
    local opts = Brainstorm.SETTINGS.autoreroll
    if (opts.searchTag or '') == '' and (opts.searchForSoul or 0) == 0 and #(opts.searchPack or {}) == 0 then
        saveManagerAlert('Set a search in Options > Settings > Brainstorm')
        return
    end
    -- The tutorial forces the first run's tags, so every seed would miss.
    if G.SETTINGS.tutorial_progress and G.SETTINGS.tutorial_progress.forced_tags then
        saveManagerAlert('Finish the tutorial before auto-rerolling')
        return
    end
    ar.autoRerollActive = true
    ar.autoRerollFrames = 0
    ar.rerollTimer = 0
    ar.seedsChecked = 0
end

function Brainstorm.update(dt)
    local ar = Brainstorm.AUTOREROLL
    if not ar.autoRerollActive then return end
    if not in_run() or in_multiplayer_lobby() then
        Brainstorm.stop_auto_reroll()
        return
    end
    ar.autoRerollFrames = (ar.autoRerollFrames or 0)
    ar.rerollTimer = ar.rerollTimer + dt
    if ar.rerollTimer >= ar.rerollInterval then
        ar.rerollTimer = ar.rerollTimer % ar.rerollInterval
        local ok, seed_found = pcall(Brainstorm.auto_reroll)
        if not ok then
            Brainstorm.stop_auto_reroll()
            print('[Brainstorm] auto-reroll failed: ' .. tostring(seed_found))
            saveManagerAlert('Auto-reroll failed')
            return
        end
        if seed_found then
            local checked = ar.seedsChecked
            Brainstorm.stop_auto_reroll()
            saveManagerAlert('Found ' .. seed_found .. ' after ' .. checked .. ' seeds')
            return
        end
    end
    ar.autoRerollFrames = ar.autoRerollFrames + 1
    if ar.autoRerollFrames == 20 and not ar.rerollText then
        ar.rerollText = Brainstorm.attention_text({
            scale = 1.4, text = 'Rerolling...', align = 'cm', offset = {x = 0, y = -3.5},
            major = G.STAGE == G.STAGES.RUN and G.play or G.title_top,
        })
    end
end

-- ---------------------------------------------------------------------------
-- Keys

local saveKeys = {'1', '2', '3', '4', '5'}

local function state_file(slot)
    return G.SETTINGS.profile .. '/' .. 'saveState' .. slot .. '.jkr'
end

function Brainstorm.save_state(slot)
    if not in_run() or not G.ARGS.save_run then return false end
    compress_and_save(state_file(slot), G.ARGS.save_run)
    saveManagerAlert('Saved state to slot [' .. slot .. ']')
    return true
end

function Brainstorm.load_state(slot)
    local saved = get_compressed(state_file(slot))
    if saved ~= nil then saved = STR_UNPACK(saved) end
    if type(saved) ~= 'table' then
        saveManagerAlert('Slot [' .. slot .. '] is empty')
        return false
    end
    Brainstorm.stop_auto_reroll()
    G:delete_run()
    G.SAVED_GAME = saved
    G:start_run({savetext = G.SAVED_GAME})
    saveManagerAlert('Loaded save from slot [' .. slot .. ']')
    return true
end

function Brainstorm.key_press_update(key)
    if G.CONTROLLER and G.CONTROLLER.text_input_hook then return end
    if in_multiplayer_lobby() then return end
    local binds = Brainstorm.SETTINGS.keybinds
    for _, k in ipairs(saveKeys) do
        if key == k and key_down(binds.saveState) then
            Brainstorm.save_state(k)
        end
        if key == k and key_down(binds.loadState) then
            Brainstorm.load_state(k)
        end
    end
    if key == binds.rerollSeed and modifier_down() then
        Brainstorm.stop_auto_reroll()
        FastReroll()
    end
    if key == binds.autoReroll and modifier_down() then
        Brainstorm.toggle_auto_reroll()
    end
end

-- ---------------------------------------------------------------------------
-- Settings tab

G.FUNCS.change_search_tag = function(x)
    Brainstorm.SETTINGS.autoreroll.searchTagID = x.to_key
    Brainstorm.SETTINGS.autoreroll.searchTag = Brainstorm.SearchTagList[x.to_val]
    Brainstorm.save_settings()
end

G.FUNCS.change_search_pack = function(x)
    Brainstorm.SETTINGS.autoreroll.searchPackID = x.to_key
    Brainstorm.SETTINGS.autoreroll.searchPack = Brainstorm.SearchPackList[x.to_val]
    Brainstorm.save_settings()
end

G.FUNCS.change_search_soul_count = function(x)
    Brainstorm.SETTINGS.autoreroll.searchForSoul = x.to_val
    Brainstorm.save_settings()
end

G.FUNCS.change_seeds_per_frame = function(x)
    Brainstorm.SETTINGS.autoreroll.seedsPerFrameID = x.to_key
    Brainstorm.SETTINGS.autoreroll.seedsPerFrame = Brainstorm.seedsPerFrame[x.to_val]
    Brainstorm.save_settings()
end

local function help_line(text)
    return {n = G.UIT.R, config = {align = 'cm', padding = 0.02}, nodes = {
        {n = G.UIT.T, config = {text = text, scale = 0.3, colour = G.C.UI.TEXT_LIGHT}},
    }}
end

function Brainstorm.settings_tab()
    local ar = Brainstorm.SETTINGS.autoreroll
    return {n = G.UIT.ROOT, config = {align = 'cm', padding = 0.05, colour = G.C.CLEAR}, nodes = {
        create_option_cycle({label = 'AutoReroll Search Tag', scale = 0.8, w = 4, options = searchTagKeys,
            opt_callback = 'change_search_tag', current_option = ar.searchTagID or 1}),
        create_option_cycle({label = 'AutoReroll Search Pack', scale = 0.8, w = 4, options = searchPackKeys,
            opt_callback = 'change_search_pack', current_option = ar.searchPackID or 1}),
        create_option_cycle({label = 'Charm Tag/Arcana Pack: Number of Souls', scale = 0.8, w = 4, options = {0, 1, 2},
            opt_callback = 'change_search_soul_count', current_option = (ar.searchForSoul or 0) + 1}),
        create_option_cycle({label = 'Rerolls per Frame', scale = 0.8, w = 4, options = seedsPerFrameKeys,
            opt_callback = 'change_seeds_per_frame', current_option = ar.seedsPerFrameID or 1}),
        create_toggle({label = 'Debug Mode', ref_table = Brainstorm.SETTINGS, ref_value = 'debug_mode',
            callback = function()
                _RELEASE_MODE = not Brainstorm.SETTINGS.debug_mode
                G.F_NO_ACHIEVEMENTS = Brainstorm.SETTINGS.debug_mode
                Brainstorm.save_settings()
            end}),
        help_line('Shift+T reroll   Shift+A auto-reroll'),
        help_line('Hold Z + 1-5 save state   Hold X + 1-5 load state'),
    }}
end

local function is_settings_tabs(args)
    if not (args and type(args.tabs) == 'table' and G.UIDEF) then return false end
    for _, tab in ipairs(args.tabs) do
        if tab.tab_definition_function_args == 'Game' and tab.tab_definition_function == G.UIDEF.settings_tab then
            return true
        end
    end
    return false
end

local create_tabs_ref = create_tabs
function create_tabs(args)
    if is_settings_tabs(args) then
        local present = false
        for _, tab in ipairs(args.tabs) do
            if tab.tab_definition_function_args == 'Brainstorm' then present = true end
        end
        if not present then
            args.tabs[#args.tabs + 1] = {
                label = 'Brainstorm',
                tab_definition_function = Brainstorm.settings_tab,
                tab_definition_function_args = 'Brainstorm',
            }
        end
    end
    return create_tabs_ref(args)
end

-- Additional game speeds (upstream patches the Game Speed option cycle).
local create_option_cycle_ref = create_option_cycle
function create_option_cycle(args)
    if args and args.opt_callback == 'change_gamespeed' and type(args.options) == 'table' and #args.options == 4 then
        local speeds = {0.5, 1, 2, 4, 8, 16, 32}
        args.options = speeds
        args.current_option = 2
        for i, speed in ipairs(speeds) do
            if G.SETTINGS.GAMESPEED == speed then args.current_option = i end
        end
    end
    return create_option_cycle_ref(args)
end

-- ---------------------------------------------------------------------------
-- Hooks replacing upstream's Lovely patches

local key_press_ref = Controller.key_press_update
function Controller:key_press_update(key, dt)
    if not (self.locks and self.locks.frame) then
        local ok, err = pcall(Brainstorm.key_press_update, key)
        if not ok then print('[Brainstorm] key handler failed: ' .. tostring(err)) end
    end
    return key_press_ref(self, key, dt)
end

local update_ref = Game.update
function Game:update(dt)
    Brainstorm.update(dt)
    return update_ref(self, dt)
end

local draw_ref = Game.draw
function Game:draw()
    draw_ref(self)
    if Brainstorm.SETTINGS.debug_mode == true and G.C and G.C.DARK_EDITION then
        love.graphics.push('all')
        love.graphics.setColor(G.C.DARK_EDITION[1], G.C.DARK_EDITION[2], G.C.DARK_EDITION[3], 1)
        love.graphics.print('BRAINSTORM DEBUG_MODE', 10, 10)
        love.graphics.pop()
    end
end

if Brainstorm.SETTINGS.debug_mode then _RELEASE_MODE = false end

return Brainstorm
