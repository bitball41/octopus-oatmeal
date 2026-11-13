"""Make multiplayer item pools independent of each player's profile progress.

Balatro builds every random pool from the local profile: a locked Joker,
Voucher or consumable becomes an UNAVAILABLE slot that is resampled, and a
Tag whose edition or booster has not been discovered is left out. The
Multiplayer mod shares one seed and assumes both players have fully unlocked
profiles (it only shows an "unlock your profile" warning). Browser saves are
rarely fully unlocked, so the same seed drew from different pools: some tags,
shop cards and packs matched while others drifted, and an unlock earned
mid-run shifted that player's pools from then on.

During a multiplayer match, build the pools as if both profiles were fully
unlocked and discovered. Nothing is written to the save; collection and
single-player behaviour are unchanged.
"""

HELPER = (
    '-- Octopus: a multiplayer match uses fully unlocked pools on both peers,\n'
    '-- so one shared seed generates the same tags, shops and packs.\n'
    'local function octopus_shared_pools()\n'
    '    return MP and MP.LOBBY and MP.LOBBY.code and true or false\n'
    'end\n\n'
)
TAG_OLD = 'G.P_CENTERS[v.requires] and G.P_CENTERS[v.requires].discovered'
TAG_NEW = 'G.P_CENTERS[v.requires] and (G.P_CENTERS[v.requires].discovered or octopus_shared_pools())'
UNLOCK_OLD = '(v.unlocked ~= false or '
UNLOCK_NEW = '(v.unlocked ~= false or octopus_shared_pools() or '


def apply(files):
    if 'Mods/Multiplayer/core.lua' not in files:
        return
    path = 'functions/common_events.lua'
    text = files[path].decode()
    if 'octopus_shared_pools' in text:
        return
    start = text.index('function get_current_pool(')
    end = text.index('\nfunction ', start + 1)
    body = text[start:end]
    for old, new, label in ((TAG_OLD, TAG_NEW, 'Tag discovery'), (UNLOCK_OLD, UNLOCK_NEW, 'center unlock')):
        assert body.count(old) == 1, f'get_current_pool {label} check changed'
        body = body.replace(old, new, 1)
    files[path] = (HELPER + text[:start] + body + text[end:]).encode()
