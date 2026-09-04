// Legacy launcher compatibility bootstrap.
// Old downloaded launchers still reference multiplayer.js. Instead of trying
// to bolt the new multiplayer client onto an already-cached old game archive,
// replace the document with the current launcher while preserving about:blank.

const LATEST_LAUNCHER_URL =
  "https://raw.githubusercontent.com/bitball41/octopus-oatmeal/main/index.html";

async function upgradeLegacyLauncher() {
  try {
    const url = `${LATEST_LAUNCHER_URL}?octopus=${Date.now()}`;
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`launcher fetch failed: ${response.status}`);

    const html = await response.text();
    if (!html.includes("OCTOPUS_NATIVE_RUNTIME_V3")) {
      throw new Error("latest launcher is missing native runtime marker");
    }

    // document.write here is intentional: this script only exists for legacy
    // downloaded launchers. Replacing the document keeps the current tab URL
    // (including about:blank) while aborting the stale game.js/game.data load.
    document.open();
    document.write(html);
    document.close();
    return;
  } catch (error) {
    console.error("[Octopus] legacy launcher upgrade failed", error);
  }

  // Fallback: at least load the current browser client if GitHub Raw is
  // unavailable. Native in-game UI still requires the upgraded game archive.
  const nativeUrl =
    "https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@a27845d382ac5bbbfda86d3c7c02a82ac6a738f8/multiplayer_native.js";
  import(nativeUrl).catch((error) => {
    console.error("[Octopus] native multiplayer fallback failed", error);
  });
}

upgradeLegacyLauncher();
