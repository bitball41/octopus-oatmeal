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
            custom:['Custom Build','Mix two or more mods in one game. Combinations are experimental and keep their own saves, or can play on your Vanilla save. Builds you launch are saved for one-click continuing and stay downloaded until you remove them.']
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
          var boxes=[].slice.call(panel.querySelectorAll('.build-option input[type=checkbox]'));
          var minimum=document.getElementById('randomizer-min'),maximum=document.getElementById('randomizer-max');
          var vanillaBox=document.getElementById('vanilla-save'),vanillaRow=document.getElementById('vanilla-save-row');
          try{var saved=JSON.parse(localStorage.getItem('octopus-custom-build')||'null');if(saved){boxes.forEach(function(b){b.checked=saved.mods.includes(b.value);});if(saved.rangeMode==='multiplier'){minimum.value=saved.min;maximum.value=saved.max;}vanillaBox.checked=!!saved.vanillaSave;}}catch(_){}
          var standalone=false;
          function update(){
            var chosen=boxes.filter(function(b){return b.checked;}),ids=chosen.map(function(b){return b.value;});
            document.getElementById('randomizer-range').hidden=ids.indexOf('randomizer')<0;
            var eligible=ids.length>0&&canUseVanillaSave(ids);
            vanillaRow.hidden=!eligible;
            var save=eligible&&vanillaBox.checked?' · Vanilla save':' · Separate save';
            document.getElementById('build-summary').textContent=chosen.length?chosen.map(function(b){return tips[b.value][0];}).join(' + ')+(chosen.length>1?' · Experimental':'')+save:'Select two or more mods.';
            document.getElementById('build-error').textContent='';
            try{localStorage.setItem('octopus-custom-build',JSON.stringify({mods:ids,min:minimum.value,max:maximum.value,rangeMode:'multiplier',vanillaSave:vanillaBox.checked}));}catch(_){}
          }
          boxes.forEach(function(b){b.addEventListener('change',update);});minimum.addEventListener('input',update);maximum.addEventListener('input',update);vanillaBox.addEventListener('change',update);
          function open(single){hideTip();standalone=!!single;panel.hidden=false;document.getElementById('mode-custom').setAttribute('aria-expanded','true');
            if(single)boxes.forEach(function(b){b.checked=b.value===single;});
            document.getElementById('build-heading').textContent=single?tips[single][0]:'Custom Build';update();panel.scrollIntoView({block:'nearest',behavior:'smooth'});
          }
          document.getElementById('mode-custom').onclick=function(){standalone=false;open();};
          document.getElementById('mode-randomizer').onclick=function(){open('randomizer');minimum.focus();};
          document.getElementById('mode-sleeves').onclick=function(){launchCustom(['sleeves'],{}).catch(showBuildError);};
          function showBuildError(error){booting=false;document.getElementById('mode-overlay').classList.remove('hidden');document.getElementById('loading-overlay').classList.add('hidden');panel.hidden=false;document.getElementById('build-error').textContent=error.message||String(error);}
          function launchSaved(selected,bounds,vanillaSave){
            confirmVanillaSave(selected,vanillaSave).then(function(ok){
              if(ok)return launchCustom(selected,bounds,{vanillaSave:vanillaSave,remember:true});
            }).catch(showBuildError);
          }
          document.getElementById('launch-build').onclick=function(){
            var selected=boxes.filter(function(b){return b.checked;}).map(function(b){return b.value;});
            if(!standalone&&selected.length<2){showBuildError(new Error('Select at least two mods for a custom build.'));return;}
            launchSaved(selected,{min:minimum.value,max:maximum.value},vanillaBox.checked&&canUseVanillaSave(selected));
          };
          // Saved builds: one click relaunches the same mods, bounds and save.
          var labels={};boxes.forEach(function(b){labels[b.value]=b.parentNode.textContent.trim();});
          var savedList=document.getElementById('saved-builds-list'),savedSection=document.getElementById('saved-builds');
          function renderSaved(){
            var entries=readSavedBuilds();
            savedSection.hidden=!entries.length;
            savedList.replaceChildren.apply(savedList,entries.map(function(entry){
              var item=document.createElement('div');item.className='saved-build';
              var play=document.createElement('button');play.type='button';play.className='saved-build-play';
              var name=document.createElement('strong');name.textContent=savedBuildName(entry,labels);
              var detail=document.createElement('span');detail.textContent=entry.vanillaSave?'Vanilla save':'Own save';
              play.append(name,detail);
              play.onclick=function(){hideTip();launchSaved(entry.mods,{min:entry.min,max:entry.max},entry.vanillaSave);};
              var remove=document.createElement('button');remove.type='button';remove.className='saved-build-remove';remove.textContent='×';
              remove.setAttribute('aria-label','Remove '+name.textContent+' from saved builds and delete its cached download. Its save data is kept.');
              remove.title='Remove and delete cached download (save data is kept)';
              remove.onclick=function(){forgetSavedBuild(entry.key);renderSaved();};
              item.append(play,remove);return item;
            }));
          }
          window.OctopusLaunch.custom=launchCustom;
          renderSaved();
          update();
        }
        var SAVED_BUILDS_KEY='octopus-saved-builds';
        function canUseVanillaSave(selected){return selected.indexOf('cryptid')<0;}
        function readSavedBuilds(){
          try{var list=JSON.parse(localStorage.getItem(SAVED_BUILDS_KEY)||'[]');return Array.isArray(list)?list.filter(function(e){return e&&Array.isArray(e.mods)&&e.key;}):[];}catch(_){return [];}
        }
        function writeSavedBuilds(list){
          list.slice(12).forEach(function(e){deleteCachedBuild(e.key);});
          try{localStorage.setItem(SAVED_BUILDS_KEY,JSON.stringify(list.slice(0,12)));}catch(_){}
        }
        function savedBuildKey(build){return build.identity+(build.vanillaSave?'@vanilla':'');}
        // Saved builds keep their assembled archive until the player removes them,
        // so relaunching skips the mod downloads and assembly entirely.
        function savedArchiveStore(mode,work){
          return new Promise(function(resolve){
            try{
              var request=indexedDB.open('octopus-saved-build-archives',1);
              request.onupgradeneeded=function(){request.result.createObjectStore('archives');};
              request.onerror=function(){resolve(null);};
              request.onsuccess=function(){
                var db=request.result,tx=db.transaction('archives',mode),result=null;
                work(tx.objectStore('archives'),function(value){result=value;});
                tx.oncomplete=function(){db.close();resolve(result);};
                tx.onerror=tx.onabort=function(e){if(e&&e.preventDefault)e.preventDefault();db.close();resolve(null);};
              };
            }catch(_){resolve(null);}
          });
        }
        function readCachedBuild(key){
          return savedArchiveStore('readonly',function(store,done){var r=store.get(key);r.onsuccess=function(){done(r.result||null);};});
        }
        function storeCachedBuild(key,result){
          return savedArchiveStore('readwrite',function(store){store.put({archive:result.archive,config:result.config,savedAt:Date.now()},key);});
        }
        function deleteCachedBuild(key){
          return savedArchiveStore('readwrite',function(store){store.delete(key);});
        }
        function rememberBuild(build){
          var key=savedBuildKey(build);
          var list=readSavedBuilds().filter(function(e){return e.key!==key;});
          list.unshift({key:key,mods:build.mods,min:build.min,max:build.max,vanillaSave:build.vanillaSave,lastPlayed:Date.now()});
          writeSavedBuilds(list);
        }
        function forgetSavedBuild(key){deleteCachedBuild(key);writeSavedBuilds(readSavedBuilds().filter(function(e){return e.key!==key;}));}
        function savedBuildName(entry,labels){
          return entry.mods.map(function(id){
            if(id==='randomizer')return 'Randomizer '+entry.min+'×–'+entry.max+'×';
            return labels[id]||id;
          }).join(' + ');
        }
        // Reads the Vanilla save without creating it: a new empty database would
        // break the game's own first open of it.
        function vanillaRunInProgress(){
          return new Promise(function(resolve){
            var done=false,timer=setTimeout(function(){finish(null);},2000);
            function finish(value){if(done)return;done=true;clearTimeout(timer);resolve(value);}
            try{
              var req=indexedDB.open('/home/web_user/love-vanilla');
              req.onupgradeneeded=function(e){e.target.transaction.abort();};
              req.onerror=function(e){if(e&&e.preventDefault)e.preventDefault();finish(false);};
              req.onblocked=function(){finish(null);};
              req.onsuccess=function(){
                var db=req.result;
                try{
                  if(!db.objectStoreNames.contains('FILE_DATA')){db.close();return finish(false);}
                  var keys=db.transaction('FILE_DATA','readonly').objectStore('FILE_DATA').getAllKeys();
                  keys.onsuccess=function(){db.close();finish(keys.result.some(function(k){return /\/save\.jkr$/.test(String(k));}));};
                  keys.onerror=function(){db.close();finish(null);};
                }catch(_){db.close();finish(null);}
              };
            }catch(_){finish(null);}
          });
        }
        function confirmVanillaSave(selected,vanillaSave){
          if(!vanillaSave)return Promise.resolve(true);
          var dialog=document.getElementById('vanilla-save-dialog');
          if(!dialog||typeof dialog.showModal!=='function')return Promise.resolve(window.confirm('Play this build on your Vanilla save? End any run you have in progress first, and finish this modded run before going back to Vanilla.'));
          var runNote=document.getElementById('vanilla-save-run');runNote.hidden=true;
          vanillaRunInProgress().then(function(inProgress){runNote.hidden=!inProgress;});
          return new Promise(function(resolve){
            function close(result){
              dialog.removeEventListener('close',onClose);
              document.getElementById('vanilla-save-confirm').onclick=null;
              resolve(result);
            }
            function onClose(){close(dialog.returnValue==='play');}
            dialog.returnValue='';
            dialog.addEventListener('close',onClose);
            document.getElementById('vanilla-save-cancel').onclick=function(){dialog.close('cancel');};
            document.getElementById('vanilla-save-confirm').onclick=function(){dialog.close('play');};
            dialog.showModal();
          });
        }
        async function launchCustom(selected,bounds,options){
          if(booting)return;
          options=options||{};
          await customModule();
          var build=window.OctopusCustom.normalizeBuild(selected,bounds,{vanillaSave:options.vanillaSave});
          if(options.remember)rememberBuild(build);
          booting=true;
          document.getElementById('mode-tooltip').hidden=true;
          document.getElementById('mode-overlay').classList.add('hidden');document.getElementById('loading-overlay').classList.remove('hidden');
          var w=await warmupPromise;
          var cached=options.remember?await readCachedBuild(savedBuildKey(build)):null;
          var result;
          if(cached&&cached.archive&&cached.config){
            Module.setStatus('Loading your saved build…');
            result={archive:cached.archive instanceof Uint8Array?cached.archive:new Uint8Array(cached.archive),config:cached.config};
          }else{
            Module.setStatus('Preparing your mod combination…');
            result=await window.OctopusCustom.assembleBuild(build,w.assetBase,cachedAsset,function(t){Module.setStatus(t);});
            if(options.remember){Module.setStatus('Saving this build for next time…');await storeCachedBuild(savedBuildKey(build),result);}
          }
          window.__octopusBuild=result.config;window.__octopusMode='custom';
          Module.persistenceDatabase=build.persist;
          Module.archiveCacheNamespace=build.cache;
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
