#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const html = await readFile(new URL("../index.html", import.meta.url), "utf8");
const start = "<!-- OCTOPUS_PINNED_RUNTIME_START -->";
const end = "<!-- OCTOPUS_PINNED_RUNTIME_END -->";

assert.equal(html.split(start).length - 1, 1, "missing pinned-runtime start marker");
assert.equal(html.split(end).length - 1, 1, "missing pinned-runtime end marker");
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

async function exercise(fetchImpl, expectedRef) {
  const loaded = [];
  const statuses = [];
  let started = 0;

  const context = {
    console: { log() {}, warn() {}, error() {} },
    Date: { now: () => 1234 },
    fetch: fetchImpl,
    REMOTE_ASSET_BASE: "",
    Module: { setStatus: (status) => statuses.push(status) },
    applicationLoad: () => { started += 1; },
    document: {
      createElement: () => ({}),
      head: {
        appendChild(script) {
          loaded.push({ src: script.src, type: script.type || "classic" });
          queueMicrotask(() => script.onload());
        },
      },
    },
  };
  context.window = context;

  vm.runInNewContext(source, context, { filename: "index-runtime-loader.js" });
  for (let i = 0; i < 8; i += 1) await new Promise(setImmediate);

  const base =
    `https://cdn.jsdelivr.net/gh/bitball41/octopus-oatmeal@${expectedRef}/`;
  assert.deepEqual(
    loaded.map(({ src }) => src),
    [
      `${base}multiplayer_upstream.js`,
      `${base}game.js`,
      `${base}love.js`,
    ],
  );
  assert.equal(loaded[0].type, "module");
  assert.equal(started, 1, "LÖVE runtime did not start exactly once");
  assert.equal(context.__octopusRuntimeRef, expectedRef);
  assert.equal(context.REMOTE_ASSET_BASE, base);
  assert.equal(statuses[0], "Resolving current build...");
}

const resolvedRef = "a".repeat(40);
await exercise(
  async () => ({ ok: true, json: async () => ({ sha: resolvedRef }) }),
  resolvedRef,
);

const fallbackMatch = source.match(/FALLBACK_RUNTIME_REF\s*=\s*\n?\s*"([0-9a-f]{40})"/i);
assert.ok(fallbackMatch, "missing valid known-good fallback SHA");
await exercise(async () => { throw new Error("offline"); }, fallbackMatch[1]);

console.log("immutable launcher runtime validation passed");
