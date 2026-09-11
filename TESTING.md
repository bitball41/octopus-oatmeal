# Vanilla / Paperback / Bunco / Multiplayer launcher — September 11, 2026

`index.html` and `balatro.html` pick a mode before the runtime starts.

- **Vanilla** loads `vanilla/game.data`. Stock Balatro plus the liminal cheat and browser seed paste. IndexedDB database `/home/web_user/love-vanilla`.
- **Paperback (a vanilla+ mod)** loads `paperback/game.data` (Steamodded + Paperback). IndexedDB database `/home/web_user/love-paperback`.
- **Bunco (a vanilla+ mod)** loads `bunco/game.data` (Steamodded + Bunco). IndexedDB database `/home/web_user/love-bunco`.
- **multiplayer mod** loads root `game.data` (Steamodded + Multiplayer). IndexedDB database `/home/web_user/love` so existing browser saves keep working. `#modded` still boots this mode.

All four modes mount the LÖVE save directory at `/home/web_user/love`. They only split the IndexedDB name, so a run in one mode cannot read another mode's profile.

## Fixes

- Red Deck in the multiplayer run setup was showing "Not available in this demo" because a Steamodded back.lua patch was remapped onto `if not back_config.unlocked then` and deleted that check. The unlocked Red Deck description is restored.
- Multiplayer create-lobby skips ruleset / gamemode / weekly walls. Hosting uses vanilla ruleset + attrition and goes straight to a lobby code.
- Signaling uses the legacy Supabase anon JWT for Realtime. The live GitHub Pages build was still on the publishable `sb_publishable_` key.
- Launcher fallback SHA is a real commit, with GitHub API then `runtime.json` then that SHA. Localhost loads files from this checkout instead of the CDN. Mode archives must stay under jsDelivr's 20 MB cap. The picker preloads shared `love.js` / `love.wasm` immediately and prefetches a mode's `game.data` on hover so Play is not a cold start.

## Verification

```sh
npm ci
python3 -m pip install lupa
npm run build:multiplayer
npm run test:loader
npm run test:sessions
npm run test:features
python3 scripts/validate_nativefs.py
python3 scripts/validate_object_registration.py
python3 scripts/validate_format_atlas.py
python3 scripts/validate_modes.py
```

In the browser: open the launcher, pick Vanilla, confirm PLAY has no MULTIPLAYER button and a seeded run can start. Reload, pick Paperback (a vanilla+ mod), confirm Steamodded/Paperback content loads without a MULTIPLAYER button. Reload, pick Bunco (a vanilla+ mod), confirm Steamodded/Bunco content (exotic suits, custom jokers) loads without a MULTIPLAYER button. Reload, pick multiplayer mod, confirm MULTIPLAYER is present, Red Deck shows +1 discard, and Create Lobby yields a five-letter code without extra menus. Use `OctopusMP.diagnostics()` if a join fails.
