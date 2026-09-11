# Combined browser build — September 11, 2026

The multiplayer implementation is restored alongside main's seed input and LuaJIT-compatible seeded RNG.

## Fixes

- Drain the JavaScript filesystem inbox from love.update before the upstream Game.update dispatcher. Previously JavaScript delivered messages, but Lua never polled them.
- Disable mipmaps in the browser's WebGL 1 atlas path. Non-power-of-two images otherwise fail during startup.
- Register custom mod sounds without the unavailable desktop sound thread, and play them through the browser's existing sound path.
- Typing liminal during an active run grants the 148 keys in 148 jokers.HTML in its exact order. Ceremonial Dagger and Madness are excluded. Existing copies are preserved; extra pre-existing duplicates follow the ordered set. Capacity grows as needed. The grant runs once per run and does not trigger while editing a text field or in a menu.
- Seed Paste reads the browser clipboard asynchronously. If access is unavailable, a native browser input accepts a manual paste. Cancellation, empty input and late responses to closed menus do not erase the existing seed.
- Every multiplayer rebuild applies main's seeded RNG fixes.

## Verification

Run:

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
```

GitHub Actions completed the build and all listed checks. The generated game.data, game.js, multiplayer_upstream.js and launchers matched the locally tested files.

Chromium testing verified startup and the actual Lua connected/version handshake. Two complete browser game instances joined, readied and entered a run with the same seed through a controlled Realtime wire. Typing liminal in the running browser game produced all 148 jokers.

The live Supabase attempt from this execution environment failed with a signaling transport error. This does not establish the cause of that network failure; live two-device gameplay and a complete multiplayer match remain unverified. The controlled test verifies game integration, not public-network availability.

The user mentioned a second cheat code but did not specify its trigger or effect; it has not been invented.

For a live test, host and join from two devices, ready/start, play hands, compare opponent progress, then leave and rejoin. Use OctopusMP.diagnostics() in each browser console for message counts, channel state and errors.
