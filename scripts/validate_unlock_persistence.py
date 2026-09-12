"""Exercise real packed unlock callback, metadata save, and SMODS reload."""
import io
import json
import zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
for mode in ('', 'bunco', 'paperback', 'pokermon'):
    path = ROOT / mode
    parts = path / 'parts.json'
    data = (b''.join((path / n).read_bytes() for n in json.loads(parts.read_text()))
            if parts.exists() else (path / 'game.data').read_bytes())
    z = zipfile.ZipFile(io.BytesIO(data))
    utils = z.read('Mods/Steamodded/src/utils.lua').decode()
    restore = utils[utils.index('function SMODS.SAVE_UNLOCKS()'):utils.index('function SMODS.process_loc_text')]
    game = z.read('game.lua').decode()
    save = game[game.index('function Game:save_progress()'):game.index('function Game:load_all_files')]
    buttons = z.read('functions/button_callbacks.lua').decode()
    callback = buttons[buttons.index('G.FUNCS.unlock_all = function(e)'):]
    callback = callback[:callback.index('\nend') + 4]
    lua = LuaRuntime()
    lua.execute('''
      Game = {}; SMODS = {}; G = {FUNCS={}};
      function boot_print_stage() end
      function EMPTY() return {} end
      function set_profile_progress() end
      function set_discover_tallies() end
      love = {filesystem={getInfo=function() return true end}}
      function clone(t)
        if type(t) ~= 'table' then return t end
        local r={}; for k,v in pairs(t) do r[k]=clone(v) end; return r
      end
      function reset(profile, meta)
        G=setmetatable({FUNCS=G.FUNCS, SETTINGS={profile=1}, PROFILES={[1]=profile or {}, [2]={}},
          FILES={['1/meta.jkr']=meta or {}}, ARGS={}, focused_profile=1, F_NO_ACHIEVEMENTS=true,
          OVERLAY_MENU={get_UIE_by_ID=function() return {config={set=true}} end}}, {__index=Game})
        for _,name in ipairs{'P_CENTERS','P_BLINDS','P_TAGS','P_SEALS'} do
          G[name]={}
          G[name][name..'_mod']={unlocked=false,discovered=false,alerted=false,order=1}
          G[name][name..'_new']={unlocked=false,discovered=false,alerted=false,order=2}
          G[name][name..'_demo']={demo=true,unlocked=false,discovered=false,order=3}
        end
        G.FUNCS.change_tab=function() end
      end
      reset()
    ''')
    lua.execute(save + '\n' + restore + '\n' + callback)
    lua.execute('''
      -- Click the actual callback, save, then recreate all default locked objects.
      G.FUNCS.unlock_all({})
      local profile, meta = clone(G.PROFILES[1]), clone(G.FILES['1/meta.jkr'])
      assert(profile.all_unlocked)
      reset(profile, meta)
      SMODS.SAVE_UNLOCKS()
      for _,name in ipairs{'P_CENTERS','P_BLINDS','P_TAGS','P_SEALS'} do
        assert(G[name][name..'_mod'].unlocked)
        assert(G[name][name..'_mod'].discovered)
        assert(G.FILES['1/meta.jkr'].discovered[name..'_mod'])
        assert(not G[name][name..'_demo'].unlocked)
      end
      assert(not G.PROFILES[2].all_unlocked)
      -- Existing broken profiles recover from their saved all_unlocked flag.
      reset({all_unlocked=true}, {})
      SMODS.SAVE_UNLOCKS()
      assert(G.P_CENTERS.P_CENTERS_new.unlocked)
      assert(G.FILES['1/meta.jkr'].unlocked.P_CENTERS_new)
      -- Normal earned progress is restored without unlocking other items.
      reset({}, {unlocked={P_CENTERS_mod=true},discovered={P_CENTERS_mod=true},alerted={P_CENTERS_mod=true}})
      SMODS.SAVE_UNLOCKS()
      assert(G.P_CENTERS.P_CENTERS_mod.unlocked)
      assert(G.P_CENTERS.P_CENTERS_mod.discovered)
      assert(G.FILES['1/meta.jkr'].unlocked.P_CENTERS_mod)
      assert(not G.P_CENTERS.P_CENTERS_new.unlocked)
      reset({}, {})
      SMODS.SAVE_UNLOCKS()
      assert(not G.P_CENTERS.P_CENTERS_mod.unlocked)
    ''')
    print((mode or 'multiplayer') + ': unlock-all, reload, recovery, earned progress, fresh profile passed')
