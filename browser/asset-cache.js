// Embedded in both launchers by patch_multiplayer_html.py (including file://).
var assetDatabase;
function assetDB() {
  if (!assetDatabase) assetDatabase = new Promise(function (resolve) {
    try {
      var request = indexedDB.open('OCTOPUS_RUNTIME_ASSETS', 1);
      request.onupgradeneeded = function () { request.result.createObjectStore('assets'); };
      request.onsuccess = function () { resolve(request.result); };
      request.onerror = request.onblocked = function () { resolve(null); };
    } catch (_) { resolve(null); }
  });
  return assetDatabase;
}
async function cachedAsset(src) {
  var url = new URL(src, document.baseURI).href;
  var immutable = /(?:@|\/)[0-9a-f]{40}\//i.test(url);
  // Local hosted builds carry content hashes; remote builds use immutable URLs.
  var path = src.split('?')[0];
  var revision = immutable ? url : ASSET_REVISIONS[path];
  var key = immutable ? url.replace(/([@/])[0-9a-f]{40}\//i, '$1build/') : url;
  var db = revision ? await assetDB() : null;
  if (db) {
    var cached = await new Promise(function (resolve) {
      try {
        var request = db.transaction('assets').objectStore('assets').get(key);
        request.onsuccess = function () { resolve(request.result); };
        request.onerror = function () { resolve(null); };
      } catch (_) { resolve(null); }
    });
    if (cached && cached.revision === revision) return cached.blob;
  }
  var response = await fetch(url + (!immutable && revision ? (url.includes('?') ? '&' : '?') + 'v=' + revision : ''));
  if (!response.ok) throw new Error('Download failed: ' + response.status + ' ' + src);
  var blob = await response.blob();
  if (db) await new Promise(function (resolve) {
    try {
      // One entry per asset: new versions replace old ones, never touch saves.
      var tx = db.transaction('assets', 'readwrite');
      tx.oncomplete = tx.onerror = tx.onabort = function () { resolve(); };
      tx.objectStore('assets').put({revision: revision, blob: blob}, key);
    } catch (_) { resolve(); }
  });
  return blob;
}
async function cachedScriptURL(src) {
  try {
    var blob = await cachedAsset(src);
    return URL.createObjectURL(new Blob([blob], {type: 'text/javascript'}));
  } catch (_) {
    // file:// restrictions, disabled storage/fetch, or CSP: ordinary loading works.
    return src;
  }
}
