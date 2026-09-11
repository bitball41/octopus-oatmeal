-- Integrate the upstream native lobby after all Multiplayer UI callbacks load.
local M = {}
function M.install()
    assert(MP and MP.ACTIONS and G.FUNCS.play_options, 'Multiplayer did not finish loading')
    local upstream_menu = create_UIBox_main_menu_buttons
    -- Multiplayer has no tutorial. Suspend it for a multiplayer run, without
    -- marking the player's single-player tutorial completed in their save.
    local tutorial
    local function restore_tutorial()
        if not tutorial then return end
        G.SETTINGS.tutorial_complete=tutorial.complete
        G.SETTINGS.tutorial_progress=tutorial.progress
        tutorial=nil
    end
    local function suspend_tutorial()
        if tutorial then return end
        tutorial={complete=G.SETTINGS.tutorial_complete,progress=G.SETTINGS.tutorial_progress}
        G.SETTINGS.tutorial_complete=true;G.SETTINGS.tutorial_progress=nil
    end
    local start_run=G.FUNCS.start_run
    function G.FUNCS.start_run(e,args)
        if args and args.mp_start then
            suspend_tutorial()
        else restore_tutorial() end
        return start_run(e,args)
    end
    local main_menu=Game.main_menu
    function Game:main_menu(context)
        if not MP.LOBBY.code then restore_tutorial() end
        return main_menu(self,context)
    end
    local save_settings=Game.save_settings
    function Game:save_settings(...)
        if not tutorial then return save_settings(self,...) end
        -- The browser queues the settings table itself for asynchronous saving.
        -- Give it a separate snapshot, not the temporarily suspended live table.
        local active=G.SETTINGS
        G.SETTINGS=copy_table(active)
        G.SETTINGS.tutorial_complete=tutorial.complete;G.SETTINGS.tutorial_progress=tutorial.progress
        local ok,result=pcall(save_settings,self,...)
        G.SETTINGS=active
        if not ok then error(result) end
        return result
    end
    G.FUNCS.octopus_multiplayer = function(e)
        print('[Octopus] native MULTIPLAYER callback -> upstream play_options')
        return G.FUNCS.play_options(e)
    end
    local function find(node, id)
        if node.config and node.config.id == id then return node end
        -- Optional browser menu rows leave holes before UIBox normalizes them.
        -- ipairs stops at the first nil and never reaches the real button row.
        for _, child in pairs(node.nodes or {}) do
            local match = find(child, id)
            if match then return match end
        end
    end
    function create_UIBox_main_menu_buttons()
        local menu = upstream_menu()
        -- Lobby rendering remains entirely upstream. The four-button row is for
        -- the main menu only, and is installed during construction, before UIBox.
        if MP.LOBBY.code then return menu end
        local play = assert(find(menu, 'main_menu_play'), 'Native PLAY node missing')
        local collection = assert(find(menu, 'collection_button'), 'Native COLLECTION node missing')
        local function row_with(node)
            local has_play, has_collection = false, false
            for _, child in pairs(node.nodes or {}) do
                if find(child, 'main_menu_play') then has_play = true end
                if find(child, 'collection_button') then has_collection = true end
            end
            for _, child in pairs(node.nodes or {}) do
                local row = row_with(child); if row then return row end
            end
            if has_play and has_collection then return node end
        end
        local row = assert(row_with(menu), 'Native main-menu row missing')
        row.nodes = {
            UIBox_button{id='main_menu_play', button=not G.SETTINGS.tutorial_complete and 'start_run' or 'setup_run', colour=G.C.BLUE, minw=2.8, minh=1.45, label={localize('b_play_cap')}, scale=0.7, col=true},
            UIBox_button{button='options', colour=G.C.ORANGE, minw=2.8, minh=1.45, label={localize('b_options_cap')}, scale=0.5, col=true},
            UIBox_button{id='collection_button', button='your_collection', colour=G.C.PALE_GREEN, minw=2.8, minh=1.45, label={localize('b_collection_cap')}, scale=0.5, col=true},
            UIBox_button{id='octopus_multiplayer_button', button='octopus_multiplayer', colour=G.C.PURPLE, minw=3.3, minh=1.45, label={'MULTIPLAYER'}, scale=0.46, col=true},
        }
        print('[Octopus] native main-menu row constructed: PLAY / OPTIONS / COLLECTION / MULTIPLAYER')
        return menu
    end
    local update = Game.update
    function Game:update(dt)
        require('browser.platform').poll()
        if MP.LOBBY.code then suspend_tutorial() else restore_tutorial() end
        return update(self, dt)
    end
end
return M
