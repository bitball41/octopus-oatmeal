-- Settings behaviour shared by every Steamodded (mod) build.
--
-- * Pixel art smoothing starts Off for a mod save, but stays a normal setting:
--   once the player turns it On it is saved and respected on later boots.
--   Custom builds played on the Vanilla save keep Vanilla's own choice.
-- * High contrast cards: Steamodded draws card fronts from per-suit colour
--   palettes that are only seeded once from the toggle, so flipping
--   Settings -> High Contrast Cards did nothing. Keep plain lc/hc palettes in
--   step with the toggle (custom deck-skin palettes are left alone).

local octopus_config_cache
local function octopus_config()
    if octopus_config_cache then return octopus_config_cache end
    octopus_config_cache = {}
    local fs = love and love.filesystem
    if fs and fs.getInfo and fs.getInfo('browser/build_config.json') then
        local ok, json = pcall(require, 'json')
        if ok and json and json.decode then
            local decoded_ok, decoded = pcall(json.decode, fs.read('browser/build_config.json'))
            if decoded_ok and type(decoded) == 'table' then octopus_config_cache = decoded end
        end
    end
    return octopus_config_cache
end

-- Mods load textures through several loaders (Steamodded atlases, Cryptid,
-- Handy, deck skins), and not all of them pick up the smoothing setting when
-- it changes. Apply it to every loaded texture directly.
local function apply_smoothing_filters()
    local graphics = G and G.SETTINGS and G.SETTINGS.GRAPHICS
    if not graphics then return end
    local mode = graphics.texture_scaling == 1 and 'nearest' or 'linear'
    for _, atlases in ipairs({G.ASSET_ATLAS or {}, G.ANIMATION_ATLAS or {}}) do
        for _, atlas in pairs(atlases) do
            local image = type(atlas) == 'table' and atlas.image
            if image and image.setFilter and not atlas.force_pixel then
                pcall(image.setFilter, image, mode, mode)
            end
        end
    end
end

local set_render_settings = Game.set_render_settings
function Game:set_render_settings(...)
    local settings = self.SETTINGS
    if settings and settings.GRAPHICS and not settings.octopus_mod_pixel_default then
        settings.octopus_mod_pixel_default = true
        if not octopus_config().vanilla_save then
            settings.GRAPHICS.texture_scaling = 1
        end
    end
    local result = set_render_settings(self, ...)
    apply_smoothing_filters()
    return result
end

local smoothing_wrapped = false
local function install_smoothing_toggle()
    if smoothing_wrapped or not (G and G.FUNCS and G.FUNCS.change_pixel_smoothing) then return end
    smoothing_wrapped = true
    local change_pixel_smoothing = G.FUNCS.change_pixel_smoothing
    G.FUNCS.change_pixel_smoothing = function(...)
        local result = change_pixel_smoothing(...)
        -- Mod atlases are re-injected after set_render_settings; cover them too.
        apply_smoothing_filters()
        return result
    end
end

-- Returns true when Steamodded palettes exist and were brought in line with
-- G.SETTINGS.colourblind_option.
local function sync_contrast_palettes()
    local settings = G and G.SETTINGS
    if not (settings and SMODS and type(SMODS.Suits) == 'table' and type(settings.colour_palettes) == 'table') then
        return false
    end
    local want = settings.colourblind_option and 'hc' or 'lc'
    local proto = G.C and G.C['SO_' .. (want == 'hc' and 2 or 1)] or {}
    local collabs = settings.CUSTOM_DECK and settings.CUSTOM_DECK.Collabs or {}
    for suit in pairs(SMODS.Suits) do
        local current = settings.colour_palettes[suit]
        local skin = SMODS.DeckSkins and collabs[suit] and SMODS.DeckSkins[collabs[suit]]
        local skin_supports = not (skin and skin.palette_map) or skin.palette_map[want]
        if (current == nil or current == 'lc' or current == 'hc') and skin_supports and proto[suit] then
            settings.colour_palettes[suit] = want
        end
        if proto[suit] and G.FUNCS.update_suit_colours then
            pcall(G.FUNCS.update_suit_colours, suit, collabs[suit])
        end
    end
    return true
end

local function refresh_card_fronts()
    for _, card in pairs(G.I and G.I.CARD or {}) do
        if card.config and card.config.card and card.children and card.children.front
            and card.ability and card.ability.effect ~= 'Stone Card' then
            card:set_sprites(nil, card.config.card)
        end
    end
end

local contrast_wrapped = false
local function install_contrast_toggle()
    if contrast_wrapped or not (G and G.FUNCS and G.FUNCS.refresh_contrast_mode) then return end
    contrast_wrapped = true
    local refresh_contrast_mode = G.FUNCS.refresh_contrast_mode
    G.FUNCS.refresh_contrast_mode = function(...)
        local synced = sync_contrast_palettes()
        local result = refresh_contrast_mode(...)
        if synced then
            -- The original resets the four base suits; reapply skin colours.
            sync_contrast_palettes()
            refresh_card_fronts()
            G:save_settings()
        end
        return result
    end
end

local start_up = Game.start_up
function Game:start_up(...)
    local result = start_up(self, ...)
    install_contrast_toggle()
    install_smoothing_toggle()
    apply_smoothing_filters()
    -- Saves where High Contrast was switched on while it had no effect.
    if self.SETTINGS and self.SETTINGS.colourblind_option and sync_contrast_palettes() then
        refresh_card_fronts()
    end
    return result
end
