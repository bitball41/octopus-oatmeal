// Legacy launcher compatibility bootstrap.
// Old downloaded launchers still reference multiplayer.js. Instead of trying
// to attach native multiplayer to an already-cached old game archive, replace
// the document with the current launcher while preserving about:blank.

const LATEST_LAUNCHER_URL =
  "https://raw.githubusercontent.com/bitball41/octopus-oatmeal/main/index.html";
const NATIVE_RUNTIME_REF = "a27845d382ac5bbbfda86d3c7c02a82ac6a738f8";
const MUTABLE_ASSET_BASE =
  "https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@main/";
const PINNED_ASSET_BASE =
  `https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@${NATIVE_RUNTIME_REF}/`;

async function upgradeLegacyLauncher() {
  try {
    const url = `${LATEST_LAUNCHER_URL}?octopus=${Date.now()}`;
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`launcher fetch failed: ${response.status}`);

    let html = await response.text();
    if (!html.includes("multiplayer_native.js")) {
      throw new Error("latest launcher does not contain native multiplayer");
    }

    // Force all runtime files to come from one immutable commit. This avoids a
    // stale @main game.js loading an older game.data package from jsDelivr.
    html = html.split(MUTABLE_ASSET_BASE).join(PINNED_ASSET_BASE);

    // This script only runs in legacy downloaded launchers. Replacing the
    // document keeps the existing tab URL (including about:blank) while
    // aborting the stale runtime load and starting the pinned native build.
    document.open();
    document.write(html);
    document.close();
    return;
  } catch (error) {
    console.error("[Octopus] legacy launcher upgrade failed", error);
  }

  // Fallback if GitHub Raw is unavailable.
  import(`${PINNED_ASSET_BASE}multiplayer_native.js`).catch((error) => {
    console.error("[Octopus] native multiplayer fallback failed", error);
  });
}

upgradeLegacyLauncher();
