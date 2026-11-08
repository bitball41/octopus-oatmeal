-- Brainstorm Rerolled 2.0.0-alpha UI/ui.lua (ABGamma, commit e0a7298).
-- Browser: the Settings menu is also recognised by its Game tab (below).
-- ui.lua — adds the "Brainstorm-Rerolled" tab to the game's Settings menu.
--
-- The tab shows which saved filter auto-reroll uses ("ACTIVE FILTER") and a
-- button to manage filters. Its contents are built by
-- Brainstorm.FB.settings_tab() in UI/filter_builder.lua. (The old built-in
-- filter options were replaced by saved filters; see filter_builder.lua.)

-- When true, the next Settings menu opens on the Brainstorm-Rerolled tab (used when
-- coming back from the filter screens).
Brainstorm.open_settings_tab = false

-- The Settings menu is the create_tabs call with tab_h = 7.05.
-- Browser: this build's Settings menu has a different height, so it is
-- recognised by its Game tab instead.
local function isSettingsMenu(args)
  if not (args and type(args.tabs) == "table") then
    return false
  end
  if args.tab_h == 7.05 then
    return true
  end
  for _, tab in ipairs(args.tabs) do
    if tab.tab_definition_function_args == "Game" and tab.tab_definition_function == G.UIDEF.settings_tab then
      return true
    end
  end
  return false
end

local create_tabs_ref = create_tabs
function create_tabs(args)
  if isSettingsMenu(args) then
    local chosen = Brainstorm.open_settings_tab
    Brainstorm.open_settings_tab = false
    if chosen then
      -- create_tabs shows the tab marked `chosen`.
      for _, tab in ipairs(args.tabs) do
        tab.chosen = false
      end
    end
    args.tabs[#args.tabs + 1] = {
      label = "Brainstorm-Rerolled",
      chosen = chosen,
      tab_definition_function = function()
        return Brainstorm.FB.settings_tab()
      end,
      tab_definition_function_args = "Brainstorm",
    }
  end
  return create_tabs_ref(args)
end
