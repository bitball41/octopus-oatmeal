# Third-party multiplayer components

This browser port bundles pinned source snapshots of these GPL-3.0 projects:

- Steamodded `adfa438771b14ea13ca9eb5993ef2632320a2865`
- Balatro Multiplayer `3dff16a99edde91894e0ccf94cc9a9171443070b` (release 0.5.5)
- Balatro Multiplayer API Server `d664c29523b827d53dfa1a181e5b2baf1aefac4f`

Their source archives, upstream URLs, exact checksums, and license files are in
`vendor/`. `scripts/build_upstream.py` applies the pinned Lovely manifests to
the browser Lua archive, and `scripts/build_server.mjs` bundles the upstream
server for the peer host. Browser-specific adapters replace unavailable native
filesystem, LuaJIT, TCP-thread, and platform APIs; gameplay remains upstream.
