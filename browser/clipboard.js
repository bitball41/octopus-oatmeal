// Clipboard reads are asynchronous and can require a fresh browser gesture.
export function installClipboard(getSaveDirectory) {
  let active;
  function finish(id, text, cancelled = false) {
    if (active && active.id !== id) return;
    active?.dialog?.remove(); active = null;
    const payload = new TextEncoder().encode(JSON.stringify({id, text, cancelled}));
    const path = getSaveDirectory();
    if (path) window.Module.FS_createDataFile(path, 'octopus_clipboard.json', payload, true, true, true);
    document.querySelector('canvas')?.focus();
  }
  function fallback(id) {
    const dialog = document.createElement('dialog');
    active = {id, dialog};
    dialog.style.cssText = 'color:#eee;background:#20262a;border:2px solid #697d85;border-radius:12px;padding:24px;font:16px system-ui;max-width:360px';
    const label = document.createElement('label'); label.textContent = 'Paste your seed here';
    const input = document.createElement('input'); input.type = 'text'; input.maxLength = 64;
    input.style.cssText = 'display:block;margin:16px 0;padding:12px;font:20px monospace;width:90%';
    label.append(input); dialog.append(label);
    const submit = document.createElement('button'); submit.textContent = 'Use seed';
    const cancel = document.createElement('button'); cancel.textContent = 'Cancel';
    for (const button of [submit, cancel]) button.style.cssText = 'padding:10px 16px;margin-right:8px';
    submit.onclick = () => finish(id, input.value);
    cancel.onclick = () => finish(id, '', true);
    dialog.addEventListener('cancel', e => {e.preventDefault(); finish(id, '', true);});
    // Keep SDL from inserting the same DOM keystrokes into the game.
    for (const event of ['keydown', 'keyup', 'keypress']) dialog.addEventListener(event, e => {
      e.stopPropagation();
      if (event === 'keydown' && e.key === 'Enter') finish(id, input.value);
    });
    dialog.append(submit, cancel); document.body.append(dialog); dialog.showModal(); input.focus();
  }
  window.OctopusClipboard = {async read(id) {
    active?.dialog?.remove(); active = {id};
    try {
      if (!navigator.clipboard?.readText) throw new Error('Clipboard unavailable');
      const text = await navigator.clipboard.readText();
      if (active?.id === id) text.trim() ? finish(id, text) : fallback(id);
    } catch {
      if (active?.id === id) fallback(id);
    }
  }};
}
