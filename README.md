# octopus-oatmeal

A fullscreen web launcher for the fixed Balatro LOVE/Emscripten build.

## Launch

Open `index.html` through a web server. The GitHub Pages deployment uses `index.html` automatically.

## Save persistence

The runtime restores IDBFS before the game starts and flushes saves to browser storage during play. Browser saves are tied to the site's origin, so keep using the same launcher URL.

The legacy `balatro.html` entry point is retained for compatibility.
