#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
const start = "<!-- OCTOPUS_PINNED_RUNTIME_START -->";
const end = "<!-- OCTOPUS_PINNED_RUNTIME_END -->";

assert.equal(html.split(start).length - 1, 1, "missing pinned-runtime start marker");
assert.equal(html.split(end).length - 1, 1, "missing pinned-runtime end marker");
assert.match(html, /id="mode-vanilla"/);
assert.match(html, /id="mode-paperback"/);
assert.match(html, /id="mode-bunco"/);
assert.match(html, /id="mode-pokermon"/);
assert.match(html, /id="mode-multiplayer"/);
assert.match(html, /Paperback \(a vanilla\+ mod\)/);
assert.match(html, /Bunco \(a vanilla\+ mod\)/);
assert.match(html, /Pokermon \(a vanilla\+ mod\)/);
assert.match(html, /multiplayer mod/);
assert.doesNotMatch(html, /id="mode-modded"/);
assert.doesNotMatch(
  html,
  /<script[^>]+src="https:\/\/cdn\.jsdelivr\.net\/gh\/bitball41\/octopus-oatmeal@main\/(?:multiplayer_native|game|love)\./i,
  "launcher still has a mutable runtime script",
);
assert.match(html, /var REMOTE_ASSET_BASE = "";/);

const marked = html.slice(html.indexOf(start), html.indexOf(end));
const scripts = [...marked.matchAll(/<script>([\s\S]*?)<\/script>/gi)];
assert.equal(scripts.length, 1, "pinned runtime must be one inline script");
const source = scripts[0][1];
assert.match(source, /FALLBACK_RUNTIME_REF\s*=\s*\n?\s*"([0-9a-f]{40})"/i);
assert.match(source, /raw\.githubusercontent\.com\/" \+ REPOSITORY \+ "\/" \+ ref \+ "\/"/);
assert.match(source, /warmupPromise/);
assert.match(source, /Promise\.all\(scripts\)/);
assert.doesNotMatch(source, /55afe41755e8fe3ce13976b4883259dd3830139a/);
assert.doesNotMatch(source, /e79da809feb66621460f605a30e5437052d6938f/);
assert.doesNotMatch(source, /b24a5c077c0c0ad6ecd4fb0c268a4831c4ae0158/);

function overlay() {
  return { classList: { add() {}, remove() {} }, onclick: null, onmouseenter: null, ontouchstart: null };
}

function context({ hostname, hash, fetchImpl }) {
  const loaded = [];
  const hints = [];
  const statuses = [];
  const state = { started: 0 };
  const buttons = {
    "mode-vanilla": overlay(),
    "mode-paperback": overlay(),
    "mode-bunco": overlay(),
    "mode-pokermon": overlay(),
    "mode-multiplayer": overlay(),
  };
  const vmContext = {
    console: { log() {}, warn() {}, error() {} },
    Date: { now: () => 1234 },
    fetch: fetchImpl,
    location: { protocol: "http:", hostname, hash: hash || "" },
    REMOTE_ASSET_BASE: "",
    Module: {
      setStatus: (status) => statuses.push(status),
      locateFile: (path) => path,
    },
    applicationLoad: () => {
      state.started += 1;
    },
    document: {
      readyState: "complete",
      addEventListener() {},
      getElementById(id) {
        return (
          buttons[id] ||
          overlay()
        );
      },
      createElement(tag) {
        return {
          tagName: String(tag || "div").toLowerCase(),
          rel: "",
          href: "",
          src: "",
          as: "",
          type: "",
          crossOrigin: "",
          onload: null,
          onerror: null,
        };
      },
      head: {
        appendChild(el) {
          if (el.tagName === "link" || el.rel) {
            hints.push({ rel: el.rel, href: el.href, as: el.as, cors: el.crossOrigin });
            return;
          }
          if (el.src) {
            loaded.push({ src: el.src, type: el.type || "classic" });
            queueMicrotask(() => {
              if (typeof el.onload === "function") el.onload();
            });
          }
        },
      },
    },
  };
  vmContext.window = vmContext;
  vm.runInNewContext(source, vmContext, { filename: "index-runtime-loader.js" });
  return { vmContext, loaded, hints, statuses, state };
}

async function flush() {
  for (let i = 0; i < 12; i += 1) await new Promise(setImmediate);
}

const local = context({ hostname: "localhost" });
await flush();
assert.equal(local.state.started, 0, "picker must not boot until a mode is chosen");
assert.deepEqual(
  local.hints.map(({ href }) => href).sort(),
  ["bunco/game.js", "game.js", "love.js", "paperback/game.js", "pokermon/game.js", "vanilla/game.js"],
);
await local.vmContext.OctopusLaunch.start("vanilla");
await flush();
assert.deepEqual(
  local.loaded.map(({ src }) => src),
  ["vanilla/game.js", "love.js"],
);
assert.equal(local.vmContext.__octopusMode, "vanilla");
assert.equal(
  local.vmContext.Module.persistenceDatabase,
  "/home/web_user/love-vanilla",
);
assert.equal(local.vmContext.Module.locateFile("game.data?v=1"), "vanilla/game.data?v=1");
assert.equal(local.vmContext.Module.locateFile("love.wasm"), "love.wasm");
assert.equal(local.state.started, 1);
local.vmContext.OctopusLaunch.prefetch("paperback");
await flush();
assert.ok(
  local.hints.some((hint) => hint.href === "paperback/game.data" && hint.as === "fetch"),
  "hover/prefetch must start the mode archive before Play",
);

const localMultiplayer = context({ hostname: "127.0.0.1" });
await localMultiplayer.vmContext.OctopusLaunch.start("multiplayer");
await flush();
assert.deepEqual(
  localMultiplayer.loaded.map(({ src }) => src),
  ["multiplayer_upstream.js", "game.js", "love.js"],
);
assert.equal(localMultiplayer.loaded[0].type, "module");
assert.equal(localMultiplayer.vmContext.__octopusMode, "multiplayer");
assert.equal(
  localMultiplayer.vmContext.Module.persistenceDatabase,
  "/home/web_user/love",
);
assert.equal(
  localMultiplayer.vmContext.Module.locateFile("game.data?v=9"),
  "game.data?v=9",
);

const localAlias = context({ hostname: "localhost" });
await localAlias.vmContext.OctopusLaunch.start("modded");
await flush();
assert.equal(localAlias.vmContext.__octopusMode, "multiplayer");
assert.deepEqual(
  localAlias.loaded.map(({ src }) => src),
  ["multiplayer_upstream.js", "game.js", "love.js"],
);

const localPaperback = context({ hostname: "localhost" });
await localPaperback.vmContext.OctopusLaunch.start("paperback");
await flush();
assert.deepEqual(
  localPaperback.loaded.map(({ src }) => src),
  ["paperback/game.js", "love.js"],
);
assert.equal(localPaperback.vmContext.__octopusMode, "paperback");
assert.equal(
  localPaperback.vmContext.Module.persistenceDatabase,
  "/home/web_user/love-paperback",
);
assert.equal(
  localPaperback.vmContext.Module.locateFile("game.data?v=1"),
  "paperback/game.data?v=1",
);
assert.equal(localPaperback.vmContext.Module.locateFile("love.wasm"), "love.wasm");

const localBunco = context({ hostname: "localhost" });
await localBunco.vmContext.OctopusLaunch.start("bunco");
await flush();
assert.deepEqual(
  localBunco.loaded.map(({ src }) => src),
  ["bunco/game.js", "love.js"],
);
assert.equal(localBunco.vmContext.__octopusMode, "bunco");
assert.equal(
  localBunco.vmContext.Module.persistenceDatabase,
  "/home/web_user/love-bunco",
);
assert.equal(
  localBunco.vmContext.Module.locateFile("game.data?v=1"),
  "bunco/game.data?v=1",
);
assert.equal(localBunco.vmContext.Module.locateFile("love.wasm"), "love.wasm");

const localPokermon = context({ hostname: "localhost" });
await localPokermon.vmContext.OctopusLaunch.start("pokermon");
await flush();
assert.deepEqual(
  localPokermon.loaded.map(({ src }) => src),
  ["pokermon/game.js", "love.js"],
);
assert.equal(localPokermon.vmContext.__octopusMode, "pokermon");
assert.equal(
  localPokermon.vmContext.Module.persistenceDatabase,
  "/home/web_user/love-pokermon",
);
assert.equal(localPokermon.vmContext.Module.INITIAL_MEMORY, 536870912);
assert.equal(
  localPokermon.vmContext.Module.locateFile("game.data?v=1"),
  "pokermon/game.data?v=1",
);
assert.equal(localPokermon.vmContext.Module.locateFile("love.wasm"), "love.wasm");
localPokermon.vmContext.OctopusLaunch.prefetch("pokermon");
await flush();
for (const part of ["pokermon/game.data.part0", "pokermon/game.data.part1"]) {
  assert.ok(
    localPokermon.hints.some((hint) => hint.href === part && hint.as === "fetch"),
    "hover/prefetch must start Pokermon archive part " + part,
  );
}
assert.ok(
  !localPokermon.hints.some((hint) => hint.href === "pokermon/game.data"),
  "Pokermon must not prefetch an unsplit game.data (jsDelivr 20 MB cap)",
);

const resolvedRef = "a".repeat(40);
const remote = context({
  hostname: "cdn.example",
  fetchImpl: async () => ({ ok: true, json: async () => ({ sha: resolvedRef }) }),
});
await remote.vmContext.OctopusLaunch.start("multiplayer");
await flush();
const base = `https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@${resolvedRef}/`;
assert.deepEqual(
  remote.loaded.map(({ src }) => src),
  [
    `${base}multiplayer_upstream.js`,
    `${base}game.js`,
    `${base}love.js`,
  ],
);
assert.equal(remote.vmContext.__octopusRuntimeRef, resolvedRef);
assert.equal(remote.vmContext.REMOTE_ASSET_BASE, base);
assert.equal(
  remote.vmContext.Module.locateFile("game.data?v=1"),
  `${base}game.data?v=1`,
);
assert.equal(
  remote.vmContext.Module.locateFile("love.wasm"),
  `${base}love.wasm`,
);
assert.ok(
  remote.hints.some((hint) => hint.href === `${base}love.js` && hint.as === "script"),
  "remote picker must preload shared love.js",
);

const remotePaperback = context({
  hostname: "cdn.example",
  fetchImpl: async () => ({ ok: true, json: async () => ({ sha: resolvedRef }) }),
});
await remotePaperback.vmContext.OctopusLaunch.start("paperback");
await flush();
assert.equal(
  remotePaperback.vmContext.Module.locateFile("game.data?v=1"),
  `${base}paperback/game.data?v=1`,
);
assert.equal(
  remotePaperback.vmContext.Module.locateFile("love.wasm"),
  `${base}love.wasm`,
);
assert.ok(
  remotePaperback.hints.some((hint) => hint.href === `${base}paperback/game.data`),
  "choosing Paperback must preload its archive",
);

const wasmRemote = context({
  hostname: "cdn.example",
  fetchImpl: async (url) => {
    const href = String(url || "");
    if (href.includes("love.wasm")) {
      return { ok: true, arrayBuffer: async () => new ArrayBuffer(8) };
    }
    return { ok: true, json: async () => ({ sha: resolvedRef }) };
  },
});
await flush();
assert.equal(wasmRemote.vmContext.Module.wasmBinary.byteLength, 8);

const hashed = context({ hostname: "localhost", hash: "#vanilla" });
await flush();
assert.equal(hashed.vmContext.__octopusMode, "vanilla");
assert.equal(hashed.state.started, 1);

const hashedPaperback = context({ hostname: "localhost", hash: "#paperback" });
await flush();
assert.equal(hashedPaperback.vmContext.__octopusMode, "paperback");
assert.equal(hashedPaperback.state.started, 1);

const hashedBunco = context({ hostname: "localhost", hash: "#bunco" });
await flush();
assert.equal(hashedBunco.vmContext.__octopusMode, "bunco");
assert.equal(hashedBunco.state.started, 1);

const hashedPokermon = context({ hostname: "localhost", hash: "#pokermon" });
await flush();
assert.equal(hashedPokermon.vmContext.__octopusMode, "pokermon");
assert.equal(hashedPokermon.state.started, 1);

const hashedAlias = context({ hostname: "localhost", hash: "#modded" });
await flush();
assert.equal(hashedAlias.vmContext.__octopusMode, "multiplayer");
assert.equal(hashedAlias.state.started, 1);

console.log("immutable launcher runtime validation passed");
