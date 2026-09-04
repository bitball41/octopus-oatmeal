// Legacy launcher compatibility shim.
// Old downloaded launchers still reference multiplayer.js. Keep that URL alive,
// but route it into the native multiplayer client instead of mounting the old
// floating DOM UI.

window.__octopusTextInputActive = !!window.__octopusTextInputActive;
window.__octopusTextKeyQueue = window.__octopusTextKeyQueue || [];
window.OctopusMultiplayer = window.OctopusMultiplayer || { _pending: [] };
window.OctopusMultiplayer._pending = Array.isArray(window.OctopusMultiplayer._pending)
  ? window.OctopusMultiplayer._pending
  : [];

for (const method of [
  "fromLuaEncoded",
  "setSaveDirectoryEncoded",
  "setTextInputActiveEncoded",
  "createLobby",
  "joinLobbyEncoded",
  "leaveLobby",
  "handleBrowserTextKey",
]) {
  if (typeof window.OctopusMultiplayer[method] !== "function") {
    window.OctopusMultiplayer[method] = function () {
      this._pending.push([method, Array.from(arguments)]);
    };
  }
}

if (!window.__octopusTextBridgeInstalled) {
  window.__octopusTextBridgeInstalled = true;

  function loveKeyFromBrowserEvent(e) {
    const special = {
      Backspace: "backspace",
      Delete: "delete",
      Enter: "return",
      Escape: "escape",
      CapsLock: "capslock",
      ArrowLeft: "left",
      ArrowRight: "right",
      Space: "space",
    };

    if (special[e.code]) return special[e.code];
    if (typeof e.key === "string" && /^[A-Za-z]$/.test(e.key)) {
      return e.key.toLowerCase();
    }
    if (typeof e.key === "string" && /^[0-9]$/.test(e.key)) {
      return e.key;
    }
    return null;
  }

  window.addEventListener(
    "keydown",
    (e) => {
      if (!window.__octopusTextInputActive) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      const key = loveKeyFromBrowserEvent(e);
      if (!key) return;

      e.preventDefault();
      e.stopPropagation();
      if (e.stopImmediatePropagation) e.stopImmediatePropagation();

      const bridge = window.OctopusMultiplayer;
      if (bridge && typeof bridge.handleBrowserTextKey === "function") {
        bridge.handleBrowserTextKey(key, !!e.shiftKey);
      } else {
        window.__octopusTextKeyQueue.push([key, !!e.shiftKey]);
      }
    },
    true,
  );
}

const nativeUrl = new URL("./multiplayer_native.js", import.meta.url);
// Cache-bust the legacy upgrade path so an old launcher cannot keep pulling an
// older native client from the browser cache.
nativeUrl.searchParams.set("v", "native-menu-20260904-2");

import(nativeUrl.href).catch((error) => {
  console.error("[Octopus MP] failed to load native multiplayer client", error);
});
