"""Embed the selector in both standalone launchers; no external CSS/JS dependency."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
def _font_face():
    # Balatro's own pixel font (m6x11plus), taken from the released Vanilla
    # archive and embedded so the downloadable launcher has it too.
    import base64, zipfile
    with zipfile.ZipFile(ROOT/'vanilla/game.data') as z:
        data = z.read('resources/fonts/m6x11plus.ttf')
    return '@font-face {font-family:m6x11;src:url(data:font/ttf;base64,' + base64.b64encode(data).decode() + ') format("truetype");font-display:block;}'

# Styled after the game's own menus: its pixel font, the dark panel with a
# light outline, and solid buttons in the game's colours with a hard bottom
# edge. No gradients.
CSS='''
      ''' + _font_face() + '''
      #mode-overlay,#loading-overlay {background:#1e2527;}
      #mode-overlay {overflow-y:auto;justify-content:safe center;gap:22px;padding:36px 16px;font-family:m6x11,monospace;font-weight:normal;color:#fff;}
      #mode-overlay * {font-weight:normal;}
      #mode-overlay h1 {margin:0;font:64px/1 m6x11,monospace;letter-spacing:.03em;text-transform:none;color:#fff;text-shadow:0 5px 0 #c2483f;}
      .menu-panel {width:min(820px,100%);display:grid;gap:18px;padding:16px 20px 20px;background:#374244;border:3px solid #b8d8d8;border-radius:16px;box-shadow:0 6px 0 #0f1314;}
      .mode-group {text-align:left;}
      .mode-group h2 {margin:0 0 9px;font:22px/1 m6x11,monospace;color:#b8d8d8;letter-spacing:0;text-transform:none;}
      #mode-overlay .mode-row {display:grid;grid-template-columns:repeat(3,1fr);gap:10px 12px;width:100%;}
      #mode-overlay .mode-row button {display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;min-width:0;min-height:66px;margin:0 0 6px;padding:10px 12px;background:var(--c);color:#fff;border:0;border-radius:10px;box-shadow:0 6px 0 var(--d);font:26px/1 m6x11,monospace;letter-spacing:0;text-transform:none;text-align:center;text-shadow:0 2px 0 rgba(0,0,0,.28);cursor:pointer;transition:transform .05s,box-shadow .05s,filter .1s;}
      #mode-overlay .mode-row button span {font-size:18px;line-height:1.05;opacity:.9;text-shadow:none;}
      #mode-overlay .mode-row.featured button {min-height:96px;font-size:28px;}
      #mode-overlay .mode-row button:hover {filter:brightness(1.1);}
      #mode-overlay .mode-row button:active,#mode-overlay .mode-row button[aria-expanded="true"] {transform:translateY(5px);box-shadow:0 1px 0 var(--d);}
      #mode-overlay button:focus-visible,#mode-overlay input:focus-visible {outline:3px solid #fff;outline-offset:2px;}
      #build-panel,#saved-builds {width:min(820px,100%);}
      #build-panel {padding:16px 20px 20px;background:#374244;border:3px solid #b8d8d8;border-radius:16px;box-shadow:0 6px 0 #0f1314;text-align:left;}
      #build-panel[hidden],#randomizer-range[hidden],#saved-builds[hidden],#vanilla-save-row[hidden],#vanilla-save-run[hidden] {display:none;}
      #build-panel h2 {font-size:30px;margin:0 0 14px;color:#fff;}
      #saved-builds h2 {font-size:22px;color:#b8d8d8;margin:0 0 9px;text-align:left;}
      .saved-builds-list {display:flex;flex-wrap:wrap;gap:10px 12px;}
      .saved-build {display:flex;align-items:stretch;border-radius:10px;background:#4f6367;box-shadow:0 5px 0 #2c3739;overflow:hidden;margin-bottom:5px;}
      .saved-build button {background:transparent;border:0;color:white;cursor:pointer;font:inherit;}
      .saved-build-play {display:grid;gap:3px;text-align:left;padding:10px 14px;min-width:0;}
      .saved-build-play strong {font-size:22px;overflow-wrap:anywhere;}
      .saved-build-play span {font-size:17px;color:#cfe3e3;}
      .saved-build-remove {padding:0 14px;color:#fff!important;font-size:24px!important;background:#fe5f55!important;}
      .saved-build button:hover {filter:brightness(1.12);}
      .build-options {display:grid;grid-template-columns:repeat(3,1fr);gap:10px 12px;}
      .build-option {display:flex;align-items:center;gap:10px;text-align:left;padding:11px 13px;margin-bottom:5px;font-size:22px;background:#4f6367;border-radius:10px;box-shadow:0 5px 0 #2c3739;cursor:pointer;}
      .build-option:has(input:checked) {background:#009dff;box-shadow:0 5px 0 #006bad;}
      .build-option:has(input:disabled) {opacity:.4;cursor:not-allowed;}
      .build-option input {accent-color:#fff;width:18px;height:18px;flex:none;margin:0;}
      #randomizer-range {display:flex;gap:16px;flex-wrap:wrap;margin:16px 0;}
      #randomizer-range label {display:grid;gap:7px;text-align:left;font-size:20px;color:#b8d8d8;}
      #randomizer-range p {font-size:18px!important;color:#b8d8d8!important;}
      #randomizer-range input {width:160px;background:#1e2527;border:2px solid #5f7377;color:white;border-radius:8px;padding:9px 10px;font:22px m6x11,monospace;}
      #vanilla-save-row {display:flex;align-items:flex-start;gap:10px;text-align:left;margin:14px 0 0;padding:12px 13px;background:#4f6367;border-radius:10px;cursor:pointer;font-size:22px;}
      #vanilla-save-row:has(input:checked) {background:#b18f43;}
      #vanilla-save-row input {accent-color:#fff;width:18px;height:18px;margin:2px 0 0;flex:none;}
      #vanilla-save-row span {display:grid;gap:4px;}
      #vanilla-save-row small {color:#e4eeee;font-size:18px;line-height:1.1;}
      #vanilla-save-dialog {margin:auto;max-width:min(500px,calc(100vw - 32px));max-height:calc(100dvh - 32px);overflow-y:auto;background:#374244;color:#fff;border:3px solid #b8d8d8;border-radius:16px;padding:20px 22px;text-align:left;font:20px/1.15 m6x11,monospace;}
      #vanilla-save-dialog::backdrop {background:#000b;}
      #vanilla-save-dialog h2 {font-size:30px;font-weight:normal;margin:0 0 12px;}
      #vanilla-save-dialog p {margin:0 0 10px;}
      #vanilla-save-dialog ul {margin:0 0 12px;padding-left:20px;}
      #vanilla-save-run {background:#7a2e29;border-radius:8px;padding:9px 11px;}
      .dialog-actions {display:flex;justify-content:flex-end;gap:12px;margin-top:16px;flex-wrap:wrap;}
      .dialog-actions button {border:0;border-radius:10px;padding:10px 18px;margin-bottom:5px;font:24px m6x11,monospace;color:#fff;cursor:pointer;}
      #vanilla-save-cancel {background:#5f7377;box-shadow:0 5px 0 #3b4a4d;}
      #vanilla-save-confirm {background:#fda200;box-shadow:0 5px 0 #a86c00;}
      #build-actions {display:flex;align-items:center;justify-content:space-between;gap:14px;margin-top:16px;}
      #build-summary {font-size:20px;color:#b8d8d8;text-align:left;line-height:1.1;}
      #launch-build {background:#009dff;color:white;border:0;border-radius:10px;padding:12px 24px;margin-bottom:6px;box-shadow:0 6px 0 #006bad;font:28px/1 m6x11,monospace;cursor:pointer;white-space:nowrap;}
      #launch-build:active {transform:translateY(5px);box-shadow:0 1px 0 #006bad;}
      #build-error {color:#ff8a82;font-size:20px;margin-top:10px;}
      #mode-tooltip {position:fixed;z-index:20;max-width:min(340px,calc(100vw - 24px));background:#374244;border:3px solid #b8d8d8;border-radius:12px;box-shadow:0 5px 0 #0f1314;color:#fff;font:19px/1.1 m6x11,monospace;padding:11px 14px;text-align:left;pointer-events:none;}
      #mode-tooltip[hidden] {display:none;}
      #mode-tooltip strong {display:block;margin-bottom:6px;font-size:24px;font-weight:normal;color:#fda200;}
      #loading-status {font:24px m6x11,monospace;color:#b8d8d8;letter-spacing:0;}
      #progress-track {background:#374244;height:10px;border-radius:5px;}
      #progress-fill {background:#009dff;border-radius:5px;}
      #loading-error-back {pointer-events:auto;background:#009dff;border:0;border-radius:10px;color:white;padding:10px 20px;box-shadow:0 5px 0 #006bad;font:24px m6x11,monospace;cursor:pointer;}
      @media(max-width:700px) {#mode-overlay h1{font-size:48px}#mode-overlay .mode-row{grid-template-columns:repeat(2,1fr)}#mode-overlay .mode-row.featured{grid-template-columns:1fr}#mode-overlay .mode-row.featured button{min-height:76px}.menu-panel,#build-panel{padding:14px 14px 16px}.build-options{grid-template-columns:repeat(2,1fr)}#build-actions{flex-direction:column;align-items:stretch;}#mode-overlay{padding:24px 12px;}}
'''
HTML='''      <div id="mode-overlay">
        <h1>Balatro</h1>
        <div class="menu-panel">
          <section class="mode-group" aria-labelledby="group-vanilla">
            <h2 id="group-vanilla">Vanilla - one shared save</h2>
            <div class="mode-row featured">
              <button id="mode-vanilla" type="button" data-tip="vanilla" style="--c:#009dff;--d:#006aad">Vanilla<span>The original game</span></button>
              <button id="mode-handy" type="button" data-tip="handy" style="--c:#fda200;--d:#ac6e00">Vanilla + Handy<span>Quick controls</span></button>
              <button id="mode-brainstorm" type="button" data-tip="brainstorm" style="--c:#8867a5;--d:#5c4670">Vanilla + Brainstorm Rerolled + Handy<span>Seed finder, with Handy</span></button>
            </div>
          </section>
          <section class="mode-group" aria-labelledby="group-mods">
            <h2 id="group-mods">Mods - separate saves</h2>
            <div class="mode-row">
              <button id="mode-cryptid" type="button" data-tip="cryptid" style="--c:#4bc292;--d:#338363">Cryptid<span>Unbalanced Jokers</span></button>
              <button id="mode-entropy" type="button" data-tip="entropy" style="--c:#fe5f55;--d:#ac4039">Entropy<span>Chaotic expansion</span></button>
              <button id="mode-fish" type="button" data-tip="fish" style="--c:#13afce;--d:#0c778c">Fish &amp; Chips<span>Go fishing</span></button>
              <button id="mode-paperback" type="button" data-tip="paperback" style="--c:#cb724c;--d:#8a4d33">Paperback<span>Vanilla-style cards</span></button>
              <button id="mode-bunco" type="button" data-tip="bunco" style="--c:#646eb7;--d:#444a7c">Bunco<span>Exotic suits</span></button>
              <button id="mode-sleeves" type="button" data-tip="sleeves" style="--c:#4584fa;--d:#2e59aa">CardSleeves<span>Deck + sleeve</span></button>
            </div>
          </section>
          <section class="mode-group" aria-labelledby="group-more">
            <h2 id="group-more">More</h2>
            <div class="mode-row">
              <button id="mode-multiplayer" type="button" data-tip="multiplayer" style="--c:#f06b3f;--d:#a3482a">Multiplayer<span>Host or join a match</span></button>
              <button id="mode-randomizer" type="button" data-tip="randomizer" style="--c:#c75985;--d:#873c5a">Custom Randomizer<span>Rolled Joker values</span></button>
              <button id="mode-custom" type="button" aria-expanded="false" aria-controls="build-panel" data-tip="custom" style="--c:#5f7377;--d:#404e50">Custom Build<span>Mix mods yourself</span></button>
            </div>
          </section>
        </div>
        <section id="saved-builds" hidden aria-labelledby="saved-builds-heading">
          <h2 id="saved-builds-heading">Continue a saved build</h2>
          <div id="saved-builds-list" class="saved-builds-list"></div>
        </section>
        <section id="build-panel" hidden aria-labelledby="build-heading">
          <h2 id="build-heading">Custom Build</h2>
          <div class="build-options">
'''+''.join(f'            <label class="build-option" data-tip="{id}"><input type="checkbox" value="{id}"> {label}</label>\n' for id,label in [('handy','Handy'),('cryptid','Cryptid'),('paperback','Paperback'),('bunco','Bunco'),('multiplayer','Multiplayer'),('sleeves','CardSleeves'),('brainstorm','Brainstorm Rerolled'),('randomizer','Randomizer')])+'''          </div>
          <div id="randomizer-range" hidden>
            <label>Minimum scoring multiplier (×)<input id="randomizer-min" type="number" min="0" max="1000000" step="any" value="0.1"></label>
            <label>Maximum scoring multiplier (×)<input id="randomizer-max" type="number" min="0" max="1000000" step="any" value="10"></label>
            <p style="flex-basis:100%;margin:0;color:#b0ccdd;font-size:13px">Usually near 1×; extreme rolls are rare. Prices, odds and counts vary gently. Your deck’s starting limits and the ante curve stay intact.</p>
          </div>
          <label id="vanilla-save-row" hidden><input id="vanilla-save" type="checkbox"><span>Play on my Vanilla save<small>Uses your Vanilla profile, unlocks and stats instead of a separate save for this build. Not available with Cryptid, which keeps its own profiles.</small></span></label>
          <div id="build-actions"><div id="build-summary" aria-live="polite">Select two or more mods.</div><button id="launch-build" type="button">Launch Build</button></div>
          <div id="build-error" role="alert"></div>
        </section>
        <div id="mode-tooltip" role="tooltip" hidden></div>
        <dialog id="vanilla-save-dialog" aria-labelledby="vanilla-save-title">
          <h2 id="vanilla-save-title">Use your Vanilla save?</h2>
          <p>This modded build will load and update your Vanilla profile, unlocks and stats.</p>
          <p id="vanilla-save-run" role="status" hidden>Your Vanilla save has a run in progress. Finish or abandon it in Vanilla first: continuing it with mods can break it.</p>
          <ul>
            <li>End any run you have in progress before you play.</li>
            <li>Finish this modded run before going back to Vanilla. Vanilla can’t continue a run that has modded cards in it.</li>
          </ul>
          <div class="dialog-actions"><button id="vanilla-save-cancel" type="button">Cancel</button><button id="vanilla-save-confirm" type="button">Play on Vanilla save</button></div>
        </dialog>
      </div>
'''
JS=(ROOT/'browser/mod-selector.js').read_text()
for name in ['index.html','balatro.html']:
    p=ROOT/name;s=p.read_text()
    if '/* MOD_SELECTOR_STYLE */' not in s:s=s.replace('    </style>','      /* MOD_SELECTOR_STYLE */\n'+CSS+'    </style>')
    else:s=re.sub(r'      /\* MOD_SELECTOR_STYLE \*/.*?</style>',lambda _:'      /* MOD_SELECTOR_STYLE */\n'+CSS+'    </style>',s,flags=re.S)
    a=s.index('      <div id="mode-overlay">');b=s.index('      <div id="loading-overlay"',a)
    s=s[:a]+HTML+s[b:]
    if '/* MOD_SELECTOR_SCRIPT */' in s:s=re.sub(r'/\* MOD_SELECTOR_SCRIPT \*/.*?/\* MOD_SELECTOR_SCRIPT_END \*/',lambda _:'/* MOD_SELECTOR_SCRIPT */\n'+JS+'\n/* MOD_SELECTOR_SCRIPT_END */',s,flags=re.S)
    else:s=s.replace('        function bindPicker() {','/* MOD_SELECTOR_SCRIPT */\n'+JS+'\n/* MOD_SELECTOR_SCRIPT_END */\n        function bindPicker() {')
    s=s.replace('          bindMode("mode-pokermon", "pokermon");','          // mode-pokermon remains available by URL hash.\n          bindModSelector();')
    if name == 'balatro.html':
        canonical=(ROOT/'index.html').read_text()
        start=canonical.index('    <!-- OCTOPUS_PINNED_RUNTIME_START -->')
        end=canonical.index('    <!-- OCTOPUS_PINNED_RUNTIME_END -->')+len('    <!-- OCTOPUS_PINNED_RUNTIME_END -->')
        a=s.index('    <script>\n      (function () {',s.index('<!-- OCTOPUS_MULTIPLAYER_BOOTSTRAP_END -->'))
        # Replace an existing pinned block whole so reruns do not repeat its marker.
        marker=s.find('    <!-- OCTOPUS_PINNED_RUNTIME_START -->',s.index('<!-- OCTOPUS_MULTIPLAYER_BOOTSTRAP_END -->'))
        if marker!=-1 and marker<a:a=marker
        b=s.index('\n  </body>',a)
        s=s[:a]+canonical[start:end]+s[b:]
        # The copied strict-mode runtime assigns this global; index.html declares it.
        if 'var REMOTE_ASSET_BASE' not in s:
            anchor='      var canvas = document.getElementById("loadingCanvas");'
            assert s.count(anchor)==1,'balatro.html canvas anchor missing'
            s=s.replace(anchor,'      // Set by the pinned runtime loader once it resolves one exact commit.\n      var REMOTE_ASSET_BASE = "";\n\n'+anchor)
    s=s.replace('          if ([32, 37, 38, 39, 40].indexOf(e.keyCode) > -1) {', '          if (e.target && /^(INPUT|TEXTAREA|BUTTON|SELECT)$/.test(e.target.tagName)) return;\n          if ([32, 37, 38, 39, 40].indexOf(e.keyCode) > -1) {') if 'e.target.tagName' not in s else s
    p.write_text(s)

# Keep the Fish and Chips preset when this selector is regenerated.
if (ROOT / 'fish-and-chips' / 'parts.json').exists():
    from install_fish_launcher import install as install_fish
    install_fish()
