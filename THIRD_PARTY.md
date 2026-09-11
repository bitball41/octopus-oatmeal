# Third-party components

This browser port bundles pinned source snapshots of:

- Steamodded `adfa438771b14ea13ca9eb5993ef2632320a2865` (GPL-3.0)
- Balatro Multiplayer `3dff16a99edde91894e0ccf94cc9a9171443070b` (release 0.5.5, GPL-3.0)
- Balatro Multiplayer API Server `d664c29523b827d53dfa1a181e5b2baf1aefac4f` (GPL-3.0)
- Paperback `f40ee0de1b56ec1bf28a1f6c6c4d34b7e64146bb` (v0.8.1, MIT)
- Bunco `016e4cda5525fcb74ec6b6e70e7fdba1f0609547` (v5.1; upstream ships no LICENSE file)
- Pokermon `2f462f609c271d5b2f2be0e8ba9d0b73b4ed8b71` (v3.8.1-0910b, GPL-3.0)

Their source archives, upstream URLs, exact checksums, and license files are in
`vendor/`. `scripts/build_upstream.py` applies the pinned Lovely manifests to
the browser Lua archives, and `scripts/build_server.mjs` bundles the upstream
server for the peer host. Browser-specific adapters replace unavailable native
filesystem, LuaJIT, TCP-thread, and platform APIs; gameplay remains upstream.
