"""Handle Cryptid's character-free overlay during multiplayer scene cleanup."""

def apply(files):
    if 'Mods/Multiplayer/ui/lobby/lobby.lua' not in files:
        return
    old='G.OVERLAY_TUTORIAL.Jimbo:remove()'
    fixed='if G.OVERLAY_TUTORIAL.Jimbo then G.OVERLAY_TUTORIAL.Jimbo:remove() end'
    for path in ('game.lua','functions/button_callbacks.lua','functions/state_events.lua','Mods/Cryptid/lib/gameset.lua'):
        if path not in files:
            continue
        text=files[path].decode()
        if old in text and fixed not in text:
            text=text.replace(old,fixed)
        files[path]=text.encode()
    # Cryptid's own introduction is separate from Balatro's tutorial. Pause
    # it in peer rooms without marking the single-player introduction finished.
    path='Mods/Cryptid/lib/gameset.lua'
    if path in files:
        text=files[path].decode()
        anchor='G.FUNCS.cry_intro_controller = function()'
        guard='\n\tif MP and MP.LOBBY and MP.LOBBY.code then return end'
        if anchor+guard not in text:
            assert text.count(anchor)==1, 'Cryptid introduction controller changed'
            text=text.replace(anchor,anchor+guard,1)
        files[path]=text.encode()
    # Notification callbacks may outlive the UI they were created for.
    path='functions/common_events.lua';text=files[path].decode()
    anchor='            G.achievement_notification.alignment.offset.x = left_not and'
    guard='            if not G.achievement_notification or not G.ROOM then return true end\n'
    if guard+anchor not in text:
        assert text.count(anchor)==1, 'Achievement notification callback changed'
        text=text.replace(anchor,guard+anchor,1)
    files[path]=text.encode()
