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
// Preserve the exact build commit when failing over to GitHub.
function assetDownloadURLs(src) {
  var url = new URL(src, document.baseURI);
  var urls = [url.href];
  var match = url.href.match(/^https:\/\/cdn\.jsdelivr\.net\/gh\/([^/]+\/[^@/]+)@([0-9a-f]{40})\/(.+)$/i);
  if (match) urls.push('https://raw.githubusercontent.com/' + match[1] + '/' + match[2] + '/' + match[3]);
  return urls;
}
function archiveAssetURL(src) {
  var urls=assetDownloadURLs(src);
  return urls[1] || src;
}
async function downloadAsset(src) {
  var urls=assetDownloadURLs(src),lastError;
  for(var i=0;i<urls.length;i++) {
    try {
      var response=await fetch(urls[i]);
      if(!response.ok) throw new Error('HTTP '+response.status);
      return await response.blob();
    } catch(error) {lastError=error;}
  }
  throw new Error('Download failed: '+src+' ('+(lastError && lastError.message)+')');
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
  var blob = await downloadAsset(url + (!immutable && revision ? (url.includes('?') ? '&' : '?') + 'v=' + revision : ''));
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
