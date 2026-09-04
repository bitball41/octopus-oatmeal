// Legacy launcher compatibility bootstrap.
// Old downloaded launchers still reference multiplayer.js. Resolve the latest
// main commit at runtime, then replace the document with that immutable build
// while preserving the current tab URL (including about:blank).

const LATEST_LAUNCHER_URL =
  "https://raw.githubusercontent.com/bitball41/octopus-oatmeal/main/index.html";
const MAIN_COMMIT_API =
  "https://api.github.com/repos/bitball41/octopus-oatmeal/commits/main";
const MUTABLE_ASSET_BASE =
  "https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@main/";
const FALLBACK_RUNTIME_REF = "cc0743b6d73d6638411f670f4fb2ca0e2e427524";

function pinnedAssetBase(runtimeRef) {
  return `https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@${runtimeRef}/`;
}

async function resolveRuntimeRef() {
  const response = await fetch(`${MAIN_COMMIT_API}?octopus=${Date.now()}`, {
    cache: "no-store",
    headers: { Accept: "application/vnd.github+json" },
  });
  if (!response.ok) {
    throw new Error(`main commit lookup failed: ${response.status}`);
  }

  const data = await response.json();
  const sha = String(data?.sha || "");
  if (!/^[0-9a-f]{40}$/i.test(sha)) {
    throw new Error("main commit lookup returned an invalid SHA");
  }
  return sha;
}

async function upgradeLegacyLauncher() {
  let runtimeRef = FALLBACK_RUNTIME_REF;

  try {
    runtimeRef = await resolveRuntimeRef();
  } catch (error) {
    console.warn(
      "[Octopus] could not resolve latest main commit; using current known-good runtime",
      error,
    );
  }

  const immutableBase = pinnedAssetBase(runtimeRef);

  try {
    const url = `${LATEST_LAUNCHER_URL}?octopus=${Date.now()}`;
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`launcher fetch failed: ${response.status}`);

    let html = await response.text();
    if (!html.includes("multiplayer_native.js")) {
      throw new Error("latest launcher does not contain native multiplayer");
    }

    // Pin the entire runtime to the same exact commit so game.js, game.data,
    // multiplayer_native.js, WASM, and all other assets cannot drift apart.
    html = html.split(MUTABLE_ASSET_BASE).join(immutableBase);

    document.open();
    document.write(html);
    document.close();
    return;
  } catch (error) {
    console.error("[Octopus] legacy launcher upgrade failed", error);
  }

  // Last-resort fallback still uses the latest resolved immutable build.
  import(`${immutableBase}multiplayer_native.js`).catch((error) => {
    console.error("[Octopus] native multiplayer fallback failed", error);
  });
}

upgradeLegacyLauncher();
