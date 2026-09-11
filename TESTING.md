# Vanilla / Modded launcher — September 11, 2026

`index.html` and `balatro.html` pick a mode before the runtime starts.

- **Vanilla** loads `vanilla/game.data`. Stock Balatro plus the liminal cheat and browser seed paste. Save directory is IndexedDB mount `/home/web_user/love-vanilla`.
- **Modded** loads `modded/game.data` (also copied to root `game.data` for old launchers). Steamodded + Multiplayer. Save directory stays `/home/web_user/love` so existing browser saves keep working.

The two modes never share a save.

## Fixes

- Red Deck in the modded run setup was showing "Not available in this demo" because a Steamodded back.lua patch was remapped onto `if not back_config.unlocked then` and deleted that check. The unlocked Red Deck description is restored.
- Multiplayer create-lobby skips ruleset / gamemode / weekly walls. Hosting uses vanilla ruleset + attrition and goes straight to a lobby code.
- Signaling uses the legacy Supabase anon JWT. The publishable `sb_publishable_` key was failing Realtime subscribe.
- Launcher fallback SHA is a real commit, with GitHub API then `runtime.json` then that SHA. Localhost loads files from this checkout instead of jsDelivr.

## Verification

```sh
npm ci
python -m pip install lupa
npm run build:multiplayer
npm run test:loader
npm run test:sessions
npm run test:features
python scripts/validate_nativefs.py
python scripts/validate_object_registration.py
python scripts/validate_format_atlas.py
python scripts/validate_modes.py
```

In the browser: open the launcher, pick Vanilla, confirm PLAY has no MULTIPLAYER button and a seeded run can start. Reload, pick Modded, confirm MULTIPLAYER is present, Red Deck shows +1 discard, and Create Lobby yields a five-letter code without extra menus. Use `OctopusMP.diagnostics()` if a join fails.
