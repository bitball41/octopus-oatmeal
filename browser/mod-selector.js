        var customModulePromise;
        function customModule() {
          if(window.OctopusCustom)return Promise.resolve();
          if (!customModulePromise) customModulePromise=warmupPromise.then(function(w){return loadScript(w.assetBase+'custom-runtime.js',false);}).then(function(){if(!window.OctopusCustom)throw new Error('The custom build loader did not initialize. Please try again.');}).catch(function(error){customModulePromise=null;throw error;});
          return customModulePromise;
        }
        function bindModSelector() {
          var panel=document.getElementById('build-panel');
          if(!panel) return;
          var tooltip=document.getElementById('mode-tooltip');
          var tips={
            vanilla:['Vanilla','The original game, plus the existing cheats. Start here if you’re new.'],
            handy:['Vanilla + Handy','The original game with quick controls, bulk selling, faster speeds and animation skipping. Includes JokerDisplay overlays and Overflow consumable stacking. Shares your Vanilla save.'],
            entropy:['Entropy','A chaotic expansion with inverted consumables, new Jokers and decks. Includes Handy and Spectrallib. Separate save.'],
            cryptid:['Cryptid','Unbalanced Jokers, strange decks and enormous scores. Includes Handy. Separate save.'],
            paperback:['Paperback','A vanilla-style content expansion with new Jokers, cards and mechanics. Separate save.'],
            bunco:['Bunco','A vanilla-style expansion with new Jokers, exotic suits and extra mechanics. Separate save.'],
            multiplayer:['Multiplayer','Host or join a match. For modded matches, both players must select the same build and randomizer bounds.'],
            sleeves:['CardSleeves','Combine a deck with a sleeve for two sets of effects. Choose your sleeve during run setup.'],
            randomizer:['Custom Randomizer','Joker scoring rolls range from 0.1×–10× and usually stay near 1×. Related effects share a roll. Prices, odds and counts vary gently; deck rules and ante progression stay intact. Playing-card enhancements, starting cards and starting money stay unchanged.'],
            custom:['Custom Build','Mix two or more mods in one game. Combinations are experimental and keep their own saves.']
          };
          var activeTooltip;
          function hideTip(){tooltip.hidden=true;if(activeTooltip)activeTooltip.removeAttribute('aria-describedby');activeTooltip=null;}
          function showTip(el){
            var tip=tips[el.dataset.tip];if(!tip)return;hideTip();activeTooltip=el;
            var title=document.createElement('strong');title.textContent=tip[0];tooltip.replaceChildren(title,document.createTextNode(tip[1]));
            tooltip.hidden=false;el.setAttribute('aria-describedby','mode-tooltip');
            var r=el.getBoundingClientRect(),t=tooltip.getBoundingClientRect();
            tooltip.style.left=Math.max(12,Math.min(innerWidth-t.width-12,r.left+r.width/2-t.width/2))+'px';
            tooltip.style.top=(r.bottom+t.height+18<innerHeight?r.bottom+10:Math.max(12,r.top-t.height-10))+'px';
          }
          document.querySelectorAll('[data-tip]').forEach(function(el){
            el.addEventListener('mouseenter',function(){showTip(el);});el.addEventListener('mouseleave',hideTip);
            el.addEventListener('focusin',function(){showTip(el);});el.addEventListener('focusout',hideTip);
          });
          document.addEventListener('keydown',function(e){if(e.key==='Escape'){hideTip();panel.hidden=true;document.getElementById('mode-custom').setAttribute('aria-expanded','false');}});
          panel.addEventListener('scroll',hideTip);window.addEventListener('resize',hideTip);
          var boxes=[].slice.call(panel.querySelectorAll('input[type=checkbox]'));
          var minimum=document.getElementById('randomizer-min'),maximum=document.getElementById('randomizer-max');
          try{var saved=JSON.parse(localStorage.getItem('octopus-custom-build')||'null');if(saved){boxes.forEach(function(b){b.checked=saved.mods.includes(b.value);});if(saved.rangeMode==='multiplier'){minimum.value=saved.min;maximum.value=saved.max;}}}catch(_){}
          var standalone=false;
          function update(){
            var chosen=boxes.filter(function(b){return b.checked;});
            document.getElementById('randomizer-range').hidden=!chosen.some(function(b){return b.value==='randomizer';});
            document.getElementById('build-summary').textContent=chosen.length?chosen.map(function(b){return tips[b.value][0];}).join(' + ')+(chosen.length>1?' · Experimental · Separate save':' · Separate save'):'Select two or more mods.';
            document.getElementById('build-error').textContent='';
            try{localStorage.setItem('octopus-custom-build',JSON.stringify({mods:chosen.map(function(b){return b.value;}),min:minimum.value,max:maximum.value,rangeMode:'multiplier'}));}catch(_){}
          }
          boxes.forEach(function(b){b.addEventListener('change',update);});minimum.addEventListener('input',update);maximum.addEventListener('input',update);
          function open(single){hideTip();standalone=!!single;panel.hidden=false;document.getElementById('mode-custom').setAttribute('aria-expanded','true');
            if(single)boxes.forEach(function(b){b.checked=b.value===single;});
            document.getElementById('build-heading').textContent=single?tips[single][0]:'Custom Build';update();panel.scrollIntoView({block:'nearest',behavior:'smooth'});
          }
          document.getElementById('mode-custom').onclick=function(){standalone=false;open();};
          document.getElementById('mode-randomizer').onclick=function(){open('randomizer');minimum.focus();};
          document.getElementById('mode-sleeves').onclick=function(){launchCustom(['sleeves'],{}).catch(showBuildError);};
          function showBuildError(error){booting=false;document.getElementById('mode-overlay').classList.remove('hidden');document.getElementById('loading-overlay').classList.add('hidden');panel.hidden=false;document.getElementById('build-error').textContent=error.message||String(error);}
          document.getElementById('launch-build').onclick=function(){
            var selected=boxes.filter(function(b){return b.checked;}).map(function(b){return b.value;});
            if(!standalone&&selected.length<2){showBuildError(new Error('Select at least two mods for a custom build.'));return;}
            launchCustom(selected,{min:minimum.value,max:maximum.value}).catch(showBuildError);
          };
          window.OctopusLaunch.custom=launchCustom;
          update();
        }
        async function launchCustom(selected,bounds){
          if(booting)return;
          await customModule();
          var build=window.OctopusCustom.normalizeBuild(selected,bounds);
          booting=true;
          document.getElementById('mode-tooltip').hidden=true;
          document.getElementById('mode-overlay').classList.add('hidden');document.getElementById('loading-overlay').classList.remove('hidden');
          var w=await warmupPromise;
          Module.setStatus('Preparing your mod combination…');
          var result=await window.OctopusCustom.assembleBuild(build,w.assetBase,cachedAsset,function(t){Module.setStatus(t);});
          window.__octopusBuild=result.config;window.__octopusMode='custom';
          Module.persistenceDatabase='/home/web_user/love-custom-'+build.identity;
          Module.archiveCacheNamespace=Module.persistenceDatabase;
          Module.INITIAL_MEMORY=536870912;
          Module.getPreloadedPackage=function(){return result.archive.buffer.slice(result.archive.byteOffset,result.archive.byteOffset+result.archive.byteLength);};
          var template=await (await cachedAsset(w.assetBase+'game.js')).text();
          template=template.replace('openDatabase(function (db) {', 'if (Module.getPreloadedPackage) { processPackageData(Module.getPreloadedPackage()); } else openDatabase(function (db) {')
            .replace('function fetchRemotePackage(packageName, packageSize, callback, errback) {', 'function fetchRemotePackage(packageName, packageSize, callback, errback) { if (Module.getPreloadedPackage) { callback(Module.getPreloadedPackage()); return; }')
            .replace(/var SPLIT_PACKAGE_PARTS = \[[^\]]*\];/,'var SPLIT_PACKAGE_PARTS = [];')
            .replace(/remote_package_size:\s*\d+/,'remote_package_size: '+result.archive.length)
            .replace(/(filename:\s*"\/game\.love",\s*crunched:\s*0,\s*start:\s*0,\s*end:)\s*\d+/,'$1 '+result.archive.length);
          var src=URL.createObjectURL(new Blob([template],{type:'text/javascript'}));
          try{
            await Promise.all([loadScript(src,false),loadScript(w.assetBase+'love.js',false),build.multiplayer?loadScript(w.assetBase+'multiplayer_upstream.js',true):Promise.resolve()]);
            await wasmReady;applicationLoad();
          }finally{URL.revokeObjectURL(src);}
        }
