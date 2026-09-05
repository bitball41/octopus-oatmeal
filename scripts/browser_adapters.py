"""Narrow source adaptations for the pinned browser/Lua 5.1 platform."""
import re


def once(text, old, new, label):
    assert text.count(old) == 1, f'{label}: expected exactly one source anchor'
    return text.replace(old, new, 1)


def adapt_sources(files):
    def edit(name, operation): files[name] = operation(files[name].decode()).encode()

    def core(text):
        start = text.index('local SOCKET = MP.load_mp_file("networking/socket.lua")')
        text = text[:start] + '''-- Browser port: keep MP's action dispatcher; replace the TCP thread only.
require('browser.menu').install()
require('browser.platform').connect()
MP.ACTIONS.connect()
'''
        return text
    edit('Mods/Multiplayer/core.lua', core)

    def smods_menu(text):
        begin = text.index('local create_UIBox_main_menu_buttonsRef = create_UIBox_main_menu_buttons')
        end = text.index('local create_UIBox_profile_buttonRef', begin)
        # Desktop's hard-coded table path does not exist in the browser menu.
        # The browser integration owns the four-button row. Mod configuration
        # remains available through the upstream Options menu.
        return text[:begin] + '-- Main-menu row is installed by browser.menu.\n\n' + text[end:]
    edit('Mods/Steamodded/src/ui.lua', smods_menu)

    def mp_menu(text):
        begin = text.index('-- Modify play button to take you to mode select first')
        end = text.index('G.FUNCS.wipe_off', begin)
        return text[:begin] + '-- Dedicated MULTIPLAYER entry is installed by browser.menu.\n\n' + text[end:]
    edit('Mods/Multiplayer/ui/main_menu/main_menu.lua', mp_menu)

    def title_card(text):
        return once(text, 'function Add_custom_multiplayer_cards(change_context)',
                    'function Add_custom_multiplayer_cards(change_context)\n    if MP.title_card and MP.title_card.area == G.title_top then return end',
                    'browser recursive menu decoration guard')
    edit('Mods/Multiplayer/ui/main_menu/title_card.lua', title_card)

    def multiplayer_selector(text):
        # PLAY stays the browser's single-player entry, so its tutorial gate and
        # single-player choices do not belong in the separate MULTIPLAYER menu.
        begin = text.index('\n\treturn (', text.index('\n\tend\n'))
        text = 'function G.UIDEF.override_main_menu_play_button()' + text[begin:]
        begin = text.index('\n\t\t\t\tUIBox_button(')
        end = text.index('\n\t\t\t\tMP.LOBBY.connected', begin)
        return text[:begin] + text[end:]
    edit('Mods/Multiplayer/ui/main_menu/play_button/play_button.lua', multiplayer_selector)

    def events(text):
        # The browser's debug-only prints concatenate an optional argument.
        # SMODS legitimately creates forced-key cards with no set argument.
        text, count = re.subn(r'print\("(create_card(?:\d*| end))"\.\._type\)', r'print("\1"..tostring(_type))', text)
        assert count == 7, 'Browser create_card debug anchors missing'
        return text
    edit('functions/common_events.lua', events)

    def logging(text):
        return once(text, '\ninitializeSocketConnection()\n', '\n-- Browser logs use the existing console; no desktop debug socket.\n', 'debug socket startup')
    edit('Mods/Steamodded/src/preflight/logging.lua', logging)

    def utils(text):
        # The browser base already keeps decoded profile metadata in G.FILES.
        # It has no desktop convert_save_to_meta function or disk STR_UNPACK path.
        text = once(text, '    convert_save_to_meta()\n\n    local meta = STR_UNPACK(get_compressed(G.SETTINGS.profile .. \'/\' .. \'meta.jkr\') or \'return {}\')',
                    "    local meta = G.FILES[G.SETTINGS.profile .. '/meta.jkr'] or {}", 'browser profile metadata')
        # LuaJIT supports goto, while the bundled Web runtime is Lua 5.1.
        # These forward skips are exactly conditional scopes, not loop exits.
        text, n = re.subn(r'if SMODS.check_looping_context\(([^\n]+)\) then\s+goto skip\s+end',
                          r'if not SMODS.check_looping_context(\1) then', text)
        assert n == text.count('::skip::'), 'Unrecognized Steamodded skip structure'
        text = text.replace('::skip::', 'end')
        text = once(text, 'goto continue\n            end', 'else', 'playing area continue')
        text = once(text, 'if not area.cards then goto continue end', 'if area.cards then', 'MP empty card area guard')
        return once(text, '::continue::', 'end\n            end', 'playing area scope')
    edit('Mods/Steamodded/src/utils.lua', utils)

    def handlers(text):
        begin = text.index('local function action_lobby_options(options)')
        finish = text.index('::continue::', begin)
        segment = text[begin:finish]
        segment = once(segment, 'goto continue\n\t\tend\n\t\tif k == "gamemode" then',
                       'elseif k == "gamemode" then', 'lobby gamemode branch')
        segment = once(segment, 'goto continue\n\t\tend\n\t\tif k == "modifier_layers" then',
                       'elseif k == "modifier_layers" then', 'lobby modifier branch')
        segment = once(segment, 'goto continue\n\t\tend', 'else', 'lobby option branch')
        text = text[:begin] + segment + 'end' + text[finish+len('::continue::'):]
        text = once(text, 'for _, card_str in pairs(card_strings) do', 'for _, card_str in pairs(card_strings) do\n        repeat', 'nemesis deck loop')
        text = text.replace('goto continue', 'break')
        return once(text, '::continue::', 'until true', 'nemesis deck continue')
    edit('Mods/Multiplayer/networking/action_handlers.lua', handlers)

    def logs(text):
        text = once(text, 'if line:find("MULTIPLAYER", 1, true) then',
                    'if line:find("MULTIPLAYER", 1, true) then\n        repeat', 'log loop')
        text = text.replace('goto continue', 'break')
        return once(text, '::continue::', 'until true', 'log continue')
    edit('Mods/Multiplayer/lib/log_parser.lua', logs)

    def game(text):
        text, n = re.subn(r'if (not SMODS.add_to_pool\(SMODS.Ranks\[v.value\][\s\S]*?) then\s+goto continue\s+end',
                          r'local browser_skip_card = \1', text, count=1)
        assert n == 1, 'Initial-deck skip anchor missing'
        text = text.replace('goto continue', 'browser_skip_card = true')
        text = once(text, 'local _ = nil', 'if not browser_skip_card then\n            local _ = nil', 'initial-deck card guard')
        text = once(text, '::continue::', 'end', 'initial-deck end guard')
        # The browser base moved SPEEDFACTOR to the beginning of start_up.
        # SMODS needs the base prototypes/atlases/localization before injection.
        loader = 'require "SMODS.preflight.loader".initSteamodded()'
        text = once(text, loader, '', 'remove premature mod injection')
        return once(text, "boot_timer('prep stage', 'splash prep',1)",
                    "self:load_profile(G.SETTINGS.profile or 1)\n    " + loader + "\n    boot_timer('prep stage', 'splash prep',1)", 'post-prototype mod injection')
    edit('game.lua', game)

    def card(text):
        text = once(text, 'if G.in_delete_run then goto skip_game_actions_during_remove end',
                    'if not G.in_delete_run then', 'card removal guard')
        return once(text, '::skip_game_actions_during_remove::', 'end', 'card removal scope')
    edit('card.lua', card)
