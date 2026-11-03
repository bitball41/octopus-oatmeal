"""Embed the selector in both standalone launchers; no external CSS/JS dependency."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
CSS='''
      #mode-overlay {overflow-y:auto;justify-content:safe center;gap:20px;padding:40px 20px;}
      #mode-overlay h1 {margin:0 0 12px;}
      .mode-row {gap:12px;width:100%;max-width:1000px;}
      .mode-row button {min-width:180px;min-height:58px;padding:15px 22px;letter-spacing:.02em;text-transform:none;color:white;transition:transform .14s,box-shadow .14s;}
      .mode-row button:hover,.mode-row button:focus-visible {transform:translateY(-2px);box-shadow:0 0 0 3px #ffffff42;outline:none;}
      #mode-paperback,#mode-bunco,#mode-pokermon,#mode-cryptid,#mode-entropy {min-width:180px;}
      #mode-entropy {background:#9b2946;}
      #mode-brainstorm {background:#6b4bb0;}
      #mode-sleeves {background:#336eaa;} #mode-randomizer {background:#bb4774;}
      #mode-custom {background:transparent;border:1px solid #6b8ba3;min-width:240px;}
      #build-panel {width:min(760px,100%);padding:22px;background:#102b3f;border:1px solid #355266;border-radius:14px;}
      #build-panel[hidden],#randomizer-range[hidden],#saved-builds[hidden],#vanilla-save-row[hidden],#vanilla-save-run[hidden] {display:none;}
      #saved-builds {width:min(760px,100%);}
      #saved-builds h2 {font-size:15px;font-weight:600;color:#b0ccdd;margin:0 0 10px;}
      .saved-builds-list {display:flex;flex-wrap:wrap;justify-content:center;gap:10px;}
      .saved-build {display:flex;align-items:stretch;border:1px solid #426077;border-radius:10px;background:#102b3f;overflow:hidden;}
      .saved-build button {background:transparent;border:0;color:white;cursor:pointer;font:inherit;}
      .saved-build-play {display:grid;gap:3px;text-align:left;padding:11px 14px;min-width:0;}
      .saved-build-play strong {font-size:14px;overflow-wrap:anywhere;}
      .saved-build-play span {font-size:12px;color:#9fbdd0;}
      .saved-build-remove {padding:0 13px;color:#9fbdd0!important;font-size:18px!important;border-left:1px solid #2c4a5e!important;}
      .saved-build button:hover,.saved-build button:focus-visible {background:#214760;outline:none;}
      #vanilla-save-row {display:flex;align-items:flex-start;gap:10px;text-align:left;margin:16px 0 0;padding:12px 13px;border:1px solid #426077;border-radius:8px;cursor:pointer;}
      #vanilla-save-row:has(input:checked) {border-color:#e6c46a;background:#2f3a2c;}
      #vanilla-save-row input {accent-color:#e6c46a;width:17px;height:17px;margin:2px 0 0;flex:none;}
      #vanilla-save-row span {display:grid;gap:3px;}
      #vanilla-save-row small {color:#b0ccdd;font-size:12.5px;line-height:1.45;}
      #vanilla-save-dialog {margin:auto;max-width:min(480px,calc(100vw - 32px));max-height:calc(100dvh - 32px);overflow-y:auto;background:#102b3f;color:#daebf6;border:1px solid #6b5a2a;border-radius:14px;padding:22px;text-align:left;line-height:1.5;}
      #vanilla-save-dialog::backdrop {background:#000a;}
      #vanilla-save-dialog h2 {font-size:18px;margin:0 0 10px;color:white;}
      #vanilla-save-dialog p {margin:0 0 10px;font-size:14px;}
      #vanilla-save-dialog ul {margin:0 0 12px;padding-left:20px;font-size:14px;}
      #vanilla-save-run {background:#4a2a1a;border:1px solid #b06a3a;border-radius:8px;padding:9px 11px;color:#ffd9c2;}
      .dialog-actions {display:flex;justify-content:flex-end;gap:10px;margin-top:16px;flex-wrap:wrap;}
      .dialog-actions button {border:0;border-radius:8px;padding:11px 18px;font:inherit;font-weight:700;cursor:pointer;}
      #vanilla-save-cancel {background:transparent;color:#daebf6;border:1px solid #6b8ba3;}
      #vanilla-save-confirm {background:#c9a13a;color:#1c1606;}
      #build-panel h2 {font-size:18px;margin:0 0 18px;}
      .build-options {display:grid;grid-template-columns:repeat(3,1fr);gap:10px;}
      .build-option {display:flex;align-items:center;gap:10px;text-align:left;padding:13px;border:1px solid #426077;border-radius:8px;cursor:pointer;}
      .build-option:has(input:checked) {border-color:#8ec3e3;background:#214760;}
      .build-option input {accent-color:#87c8ef;width:17px;height:17px;}
      #randomizer-range {display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin:18px 0;}
      #randomizer-range label {display:grid;gap:7px;text-align:left;font-size:13px;color:#b0ccdd;}
      #randomizer-range input {width:150px;background:#091f2f;border:1px solid #638297;color:white;border-radius:7px;padding:10px;font:inherit;}
      #build-actions {display:flex;align-items:center;justify-content:space-between;gap:14px;margin-top:18px;}
      #build-summary {font-size:13px;color:#abc5d6;text-align:left;line-height:1.5;}
      #launch-build {background:#3d9be8;color:white;border:0;border-radius:8px;padding:13px 22px;font-weight:700;cursor:pointer;white-space:nowrap;}
      #build-error {color:#ffb5b5;font-size:14px;margin-top:12px;}
      #mode-tooltip {position:fixed;z-index:20;max-width:min(340px,calc(100vw - 24px));background:#071621;border:1px solid #52758d;border-radius:10px;box-shadow:0 10px 30px #0006;color:#daebf6;font-size:14px;line-height:1.5;padding:13px 16px;text-align:left;pointer-events:none;}
      #mode-tooltip[hidden] {display:none;}
      #mode-tooltip strong {display:block;margin-bottom:4px;color:white;}
      #loading-error-back {pointer-events:auto;background:#3d9be8;border:0;border-radius:8px;color:white;padding:12px 20px;cursor:pointer;}
      @media(max-width:620px) {.mode-row{gap:9px}.mode-row button{min-width:135px!important;padding:12px 14px;font-size:14px;}.build-options{grid-template-columns:repeat(2,1fr)}#build-actions{flex-direction:column;align-items:stretch;}#mode-overlay{padding:24px 14px;}}
'''
HTML='''      <div id="mode-overlay">
        <h1>Balatro</h1>
        <div class="mode-row" aria-label="Original game">
          <button id="mode-vanilla" type="button" data-tip="vanilla">Vanilla</button>
        </div>
        <div class="mode-row" aria-label="Featured modes">
          <button id="mode-handy" type="button" data-tip="handy">Vanilla + Handy</button>
          <button id="mode-brainstorm" type="button" data-tip="brainstorm">Vanilla + Brainstorm</button>
          <button id="mode-cryptid" type="button" data-tip="cryptid">Cryptid</button>
          <button id="mode-entropy" type="button" data-tip="entropy">Entropy</button>
        </div>
        <div class="mode-row" aria-label="More mods">
          <button id="mode-paperback" type="button" data-tip="paperback">Paperback</button>
          <button id="mode-bunco" type="button" data-tip="bunco">Bunco</button>
          <button id="mode-multiplayer" type="button" data-tip="multiplayer">Multiplayer</button>
          <button id="mode-sleeves" type="button" data-tip="sleeves">CardSleeves</button>
          <button id="mode-randomizer" type="button" data-tip="randomizer">Custom Randomizer</button>
        </div>
        <div class="mode-row">
          <button id="mode-custom" type="button" aria-expanded="false" aria-controls="build-panel" data-tip="custom">Custom Build</button>
        </div>
        <section id="saved-builds" hidden aria-labelledby="saved-builds-heading">
          <h2 id="saved-builds-heading">Continue a saved build</h2>
          <div id="saved-builds-list" class="saved-builds-list"></div>
        </section>
        <section id="build-panel" hidden aria-labelledby="build-heading">
          <h2 id="build-heading">Custom Build</h2>
          <div class="build-options">
'''+''.join(f'            <label class="build-option" data-tip="{id}"><input type="checkbox" value="{id}"> {label}</label>\n' for id,label in [('handy','Handy'),('cryptid','Cryptid'),('paperback','Paperback'),('bunco','Bunco'),('multiplayer','Multiplayer'),('sleeves','CardSleeves'),('brainstorm','Brainstorm'),('randomizer','Randomizer')])+'''          </div>
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
