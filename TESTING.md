# Vanilla / Paperback / Bunco / Pokermon / Multiplayer launcher — September 11, 2026

`index.html` and `balatro.html` pick a mode before the runtime starts.

- **Vanilla** loads `vanilla/game.data`. Stock Balatro plus the liminal cheat and browser seed paste. IndexedDB database `/home/web_user/love-vanilla`.
- **Vanilla + Handy** loads `vanilla-handy/game.data`. Vanilla with standalone Handy; shares `/home/web_user/love-vanilla`, including the current run, profiles and unlocks.
- **Paperback (a vanilla+ mod)** loads `paperback/game.data` (Steamodded + Paperback). IndexedDB database `/home/web_user/love-paperback`.
- **Bunco (a vanilla+ mod)** loads `bunco/game.data` (Steamodded + Bunco). IndexedDB database `/home/web_user/love-bunco`.
- **Pokermon (a pokemon mod)** loads `pokermon/game.data.part0` and `part1` concatenated into the LÖVE archive (Steamodded + Pokermon). IndexedDB database `/home/web_user/love-pokermon`. jsDelivr 403s any single file over 20 MB, so this pack is split at 18 MiB. 2x / Natdex / Unown-swarm sheets are dropped so love.js can decode the remaining PNGs.
- **multiplayer mod** loads root `game.data` (Steamodded + Multiplayer). IndexedDB database `/home/web_user/love` so existing browser saves keep working. `#modded` still boots this mode.

All modes mount the LÖVE save directory at `/home/web_user/love`. Vanilla and
Vanilla + Handy use the same IndexedDB name. The content-mod modes use their
own databases, so their runs cannot read Vanilla's profiles.

## Fixes

- Lobby creation and joining let Supabase recover an initial transport failure within a bounded 15-second window. Failed or cancelled rooms release their channels, and a failed host can retry with the existing username/version handshake. Authorization failures still fail immediately. `node scripts/validate_signaling.mjs` and `node scripts/validate_sessions.mjs` exercise these paths.
- Red Deck in the multiplayer run setup was showing "Not available in this demo" because a Steamodded back.lua patch was remapped onto `if not back_config.unlocked then` and deleted that check. The unlocked Red Deck description is restored.
- Multiplayer create-lobby skips ruleset / gamemode / weekly walls. Hosting uses vanilla ruleset + attrition and goes straight to a lobby code.
- Signaling uses the Liminal Supabase project (`trsirhyucncmyyfyiuje`) and its browser-safe publishable key, without a persisted Auth session. Both the upstream bridge and the legacy native fallback target this project. Rebuild `multiplayer_upstream.js` with `node scripts/build_server.mjs` after changing the bridge connection, and refresh its cache revision in both launchers.
- Save restore opens compatible IndexedDB databases at their current version. Forcing version 21 could leave multiplayer at Preparing (1/2) while an older save connection stayed open. Blocked or unresponsive opens release startup without enabling save writeback, and late requests close without restoring over the active session. `npm run test:startup` runs the real WASM and archive loader against fresh, older, current, newer, blocked and unresponsive save databases, including restored progress surviving a flush.
- Launcher fallback SHA is a real commit, with GitHub API then `runtime.json` then that SHA. Localhost loads files from this checkout instead of the CDN. Mode archives must stay under jsDelivr's 20 MB cap (Pokermon ships as concatenated parts). The picker preloads shared `love.js` / `love.wasm` immediately and prefetches a mode's archive on hover so Play is not a cold start.

## Verification

```sh
npm ci
python3 -m pip install lupa pillow
npm run build:multiplayer
npm run test:loader
npm run test:sessions
npm run test:features
python3 scripts/validate_nativefs.py
python3 scripts/validate_object_registration.py
python3 scripts/validate_format_atlas.py
python3 scripts/validate_modes.py
```

In the browser: open the launcher, pick Vanilla, confirm PLAY has no MULTIPLAYER button and a seeded run can start. Reload, pick Paperback (a vanilla+ mod), confirm Steamodded/Paperback content loads without a MULTIPLAYER button. Reload, pick Bunco (a vanilla+ mod), confirm Steamodded/Bunco content (exotic suits, custom jokers) loads without a MULTIPLAYER button. Reload, pick Pokermon (a pokemon mod), confirm Steamodded/Pokermon content loads without a MULTIPLAYER button and without a shader abort. Reload, pick multiplayer mod, confirm MULTIPLAYER is present, Red Deck shows +1 discard, and Create Lobby yields a five-letter code without extra menus. Use `OctopusMP.diagnostics()` if a join fails.

## Cryptid

The **Cryptid** button in both launchers (or `index.html#cryptid`) loads Cryptid
0.5.17c, Amulet 3.6.1, and Steamodded 26.829.0. Its IndexedDB name is
`/home/web_user/love-cryptid`; the other modes retain their existing builds and
saves. The archive uses two CDN-safe parts, with 512 MiB initial runtime memory.

Fetch pinned sources with `python scripts/fetch_cryptid_sources.py`, then build
only this mode with `npm ci && npm run build:cryptid`. As with the other
source builds, the two base archives must be available in git history (use a
full clone, or fetch the base commits named in `scripts/build_upstream.py`).
`npm run test:cryptid` compiles every packaged Lua file against Lua 5.1 and
checks OmegaNum arithmetic, mixed comparisons, and save serialization.
`npm run test:loader` also verifies the mode's local/CDN loading and archive
cache behavior. `lupa` and Pillow are required for Python checks/builds.

Browser adaptations replace native FFI storage and mounts, preserve Amulet's
OmegaNum arithmetic, compile mixed numeric comparisons for Lua 5.1, retain
Cryptid's M1/M2/M3 profile data, and repair WebGL 1 shader loops/mipmaps.
Discord member-count lookup uses Cryptid's upstream offline fallback.

The Build Cryptid browser mode workflow reproduces and commits the generated
assets, then updates the launcher fallback to that exact runtime commit.

## Handy in Cryptid

Cryptid also includes pinned Handy 2.0.6. Open **Options → Handy** to configure
its keybinds, quick buy/sell/use, hand selection, speed, and animation skipping.
The existing game settings include speed/animation controls; no launcher
toolbar or extra in-game HUD buttons are added.

- **Shift + right-click a Joker:** sell every copy of that Joker in the area.
- **Ctrl + Shift + right-click:** sell every sellable card in that area.
- **Alt + mouse wheel:** adjust Handy's speed multiplier, up to **512×**.
- **Left bracket + mouse wheel:** adjust animation skipping.
- **Escape during bulk selling:** stop after the current sale finishes.

Bulk targets are a snapshot in area order. Every card is revalidated immediately
before its native `G.FUNCS.sell_card` callback, with eternal/custom restrictions
intact. All callbacks, sell contexts, retriggers, payouts, scaling, removal and
descendant events finish before the next sale. New/generated cards are not
automatically added. Saves occur only after the batch finishes or cancels;
Cryptid's existing IndexedDB database and M1/M2/M3 profiles are unchanged.

`npm run test:cryptid` includes Lua 5.1 regression comparisons of native serial
sales versus bulk sales for 1, 35 and 100 Jokers with packed Crypto Coin and
Loopy calculations and SMODS retrigger/context loops. It also covers a 1,000-card
selection, yielding/cancellation, eternal restrictions, snapshot semantics,
cleanup, saving and individual payout accounting. These are headless Lua
simulations with rendering stubbed, not browser gameplay tests.

For a manual browser check, reload `index.html#cryptid` with an existing save,
open Options → Handy and inspect its controls. Compare a duplicate-Jolly sale
batch with normal sales using Crypto Coin and Loopy, then test 512× speed,
animation skip, eternal Jokers and Escape cancellation. Check that progress
clears and the saved run resumes with the resulting money and Jokers.

## Vanilla + Handy

The new button beside Vanilla (or `#handy` / `#vanilla-handy`) loads Handy
without Steamodded or Cryptid. It is built from the exact Vanilla base and
retains Vanilla's save/load functions, serializer and filesystem identity.
Both buttons continue the same run and share every profile and unlock.
Game archive caches stay separate so switching buttons keeps both downloads.

Build with `npm run build:handy`; verify with `npm run test:handy` and
`npm run test:loader`. These checks compile the standalone archive, bootstrap
Handy, compare Vanilla's save/load functions, round-trip a saved run in both
directions, and exercise both launcher entry points and their shared-save cache.

## Custom mod builds and value randomizer

Run `npm run build:custom` after changing mod pins, compatibility rules or randomizer instrumentation. It compiles all 64 subsets of Bunco, CardSleeves, Cryptid, Handy, Multiplayer and Paperback, validates Lua 5.1 syntax, and emits shared content-addressed asset packs. Randomizer is a separate optional selection in any build; its bounds are injected by the launcher.

Run `npm run test:custom`, `npm run test:loader`, `npm run test:startup` and `npm run test:sessions -- game.data`. The custom suite checks all recipe/payload hashes, selected-only contents and actual archive assembly. `scripts/validate_randomizer_design.py` checks 500 seeded setups and 10,000 roll samples against the rules in [RANDOMIZER.md](RANDOMIZER.md): native starting budgets, ante progression, coherent Joker scoring, neutral scaler states, safe prices/odds/counts, exclusions, save continuation and multiplayer determinism.

Randomizer scoring bounds default to 0.1×–10× with rolls centered around 1× in log space. Prices, counts and progression have separate limits. Build/save identities include `designed-v3`, keeping earlier rules separate and refusing mismatched multiplayer settings. Configuration stays in the launcher; no in-game settings are added. Existing preset databases remain unchanged.

Custom archives are assembled from verified packs before the engine starts and bypass the old full-archive cache. The optional randomizer Lua is injected from `custom/value-randomizer.lua`, allowing its rules to be updated without rebuilding the underlying mod archives. Game progress uses the existing save system. All 64 mod combinations have compilation/assembly coverage; exhaustive gameplay compatibility remains experimental.

## Entropy and the Handy QoL bundle

- `npm run test:new-mods`: Lua 5.1 compilation, CDN package limits, Entropy profile isolation, selector integration, and lossless expansion of Overflow saves in Vanilla.
- `npm run test:new-mods-browser`: instruments temporary copies of the release archives, then boots actual WASM in Chromium. It checks JokerDisplay overlays, negative-consumable stacking and serialization, Constellation contexts, Entropy content loading, a new run, the first dealt hand and a scored hand. Install Chromium with `npx playwright install --with-deps chromium` first. `PLAYWRIGHT_CHROMIUM_EXECUTABLE` can select an existing binary.
- Browser test output and screenshots live under `build/mod-smoke/`; instrumented archives are never published.
