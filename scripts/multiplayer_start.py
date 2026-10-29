"""Handle Cryptid's character-free overlay during multiplayer scene cleanup."""

def apply(files):
    if 'Mods/Multiplayer/ui/lobby/lobby.lua' not in files:
        return
    path='game.lua';text=files[path].decode()
    old='G.OVERLAY_TUTORIAL.Jimbo:remove()'
    fixed='if G.OVERLAY_TUTORIAL.Jimbo then G.OVERLAY_TUTORIAL.Jimbo:remove() end'
    if fixed not in text:
        assert text.count(old)==1, 'Tutorial character cleanup changed'
        text=text.replace(old,fixed,1)
    files[path]=text.encode()
    # Notification callbacks may outlive the UI they were created for.
    path='functions/common_events.lua';text=files[path].decode()
    anchor='            G.achievement_notification.alignment.offset.x = left_not and'
    guard='            if not G.achievement_notification or not G.ROOM then return true end\n'
    if guard+anchor not in text:
        assert text.count(anchor)==1, 'Achievement notification callback changed'
        text=text.replace(anchor,guard+anchor,1)
    files[path]=text.encode()
