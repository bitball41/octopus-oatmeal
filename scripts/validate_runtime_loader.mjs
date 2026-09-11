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
assert.match(html, /id="mode-modded"/);
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
assert.doesNotMatch(source, /55afe41755e8fe3ce13976b4883259dd3830139a/);

function overlay() {
  return { classList: { add() {}, remove() {} }, onclick: null };
}

function context({ hostname, hash, fetchImpl }) {
  const loaded = [];
  const statuses = [];
  const state = { started: 0 };
  const buttons = { "mode-vanilla": overlay(), "mode-modded": overlay() };
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
      createElement: () => ({}),
      head: {
        appendChild(script) {
          loaded.push({ src: script.src, type: script.type || "classic" });
          queueMicrotask(() => script.onload());
        },
      },
    },
  };
  vmContext.window = vmContext;
  vm.runInNewContext(source, vmContext, { filename: "index-runtime-loader.js" });
  return { vmContext, loaded, statuses, state };
}

async function flush() {
  for (let i = 0; i < 12; i += 1) await new Promise(setImmediate);
}

const local = context({ hostname: "localhost" });
await flush();
assert.equal(local.state.started, 0, "picker must not boot until a mode is chosen");
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

const localModded = context({ hostname: "127.0.0.1" });
await localModded.vmContext.OctopusLaunch.start("modded");
await flush();
assert.deepEqual(
  localModded.loaded.map(({ src }) => src),
  ["multiplayer_upstream.js", "game.js", "love.js"],
);
assert.equal(localModded.loaded[0].type, "module");
assert.equal(
  localModded.vmContext.Module.persistenceDatabase,
  "/home/web_user/love",
);
assert.equal(
  localModded.vmContext.Module.locateFile("game.data?v=9"),
  "game.data?v=9",
);

const resolvedRef = "a".repeat(40);
const remote = context({
  hostname: "cdn.example",
  fetchImpl: async () => ({ ok: true, json: async () => ({ sha: resolvedRef }) }),
});
await remote.vmContext.OctopusLaunch.start("modded");
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

const hashed = context({ hostname: "localhost", hash: "#vanilla" });
await flush();
assert.equal(hashed.vmContext.__octopusMode, "vanilla");
assert.equal(hashed.state.started, 1);

console.log("immutable launcher runtime validation passed");
