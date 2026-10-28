#!/usr/bin/env python3
"""Compile exact mod combinations into deduplicated asset packs and Lua overlays.

The browser assembles a real LÖVE archive locally. No service, native loader,
preinstalled mods or duplicated 30MB runtimes are needed for custom builds.
"""
import argparse, hashlib, itertools, json, io, zipfile, sys, subprocess, multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from functools import lru_cache
from lupa.lua51 import LuaRuntime
import build_upstream as b
ROOT = b.ROOT
OUT = ROOT/'custom'
MODS = ['Bunco','CardSleeves','Cryptid','Handy','Multiplayer','Paperback']
LUA = LuaRuntime(unpack_returned_tuples=True)
CHECK = LUA.eval('function(s,n) local f,e=loadstring(s,n); return f~=nil,e end')
# Independent calls mutate dictionaries, not byte values. Avoid repeatedly inflating assets.
original_unpack = b.unpack
@lru_cache(maxsize=16)
def cached_unpack(blob): return original_unpack(blob)
b.unpack = lambda blob: dict(cached_unpack(blob))
base = b.browser_base
@lru_cache(maxsize=1)
def cached_base(): return base()
b.browser_base = lambda: dict(cached_base())


def pack(files):
    identity=hashlib.sha256()
    for name,data in sorted(files.items()):
        identity.update(name.encode()+b'\0'+hashlib.sha256(data).digest())
    cache=ROOT/'build/pack-cache'/identity.hexdigest()
    if cache.exists():return json.loads(cache.read_text())
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2026,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
    blob=buf.getvalue(); sha=hashlib.sha256(blob).hexdigest()
    parts=[]
    for i,start in enumerate(range(0,len(blob),b.PART_SIZE)):
        name=f'packs/{sha}.{i}.zip';path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():path.write_bytes(blob[start:start+b.PART_SIZE])
        parts.append(name)
    spec={'parts':parts,'sha256':sha}
    cache.parent.mkdir(parents=True,exist_ok=True);cache.write_text(json.dumps(spec))
    return spec


def compile_combo(mods):
    lock=json.loads((ROOT/'vendor/upstream.json').read_text())
    cryptid='Cryptid' in mods;mp='Multiplayer' in mods
    if cryptid:lock['Steamodded']=lock['SteamoddedCryptid']
    selected=['Steamodded']+(['Amulet'] if cryptid else [])+mods
    flavor='cryptid' if cryptid else ('multiplayer' if mp else ('bunco' if 'Bunco' in mods else 'custom'))
    files,report=b.build_smods_pack(selected,flavor,() if mp else ('browser/menu.lua',),lock)
    failures=b.summarize_report(report,'+'.join(mods) or 'randomizer','patch-report-custom-'+('-'.join(mods) or 'base')+'.json',True)
    if failures:
        raise RuntimeError(json.dumps(failures))
    sources={n:d.decode() for n,d in files.items() if n.endswith('.lua')}
    result=subprocess.run(['node',str(ROOT/'scripts/randomize_literals.mjs')],input=json.dumps(sources),text=True,capture_output=True,check=True)
    files.update({n:s.encode() for n,s in json.loads(result.stdout).items()})
    # Randomizer is initialized last, after SMODS and every selected mod loads.
    files['Mods/ValueRandomizer/ValueRandomizer.json']=json.dumps({
        'id':'ValueRandomizer','name':'Value Randomizer','author':['Liminal'],
        'description':'Launcher-configured gameplay value multiplier randomizer.',
        'prefix':'lvr','main_file':'ValueRandomizer.lua','version':'1.0.0','priority':2147483647,
    }).encode()
    files['Mods/ValueRandomizer/ValueRandomizer.lua']=(ROOT/'browser/value-randomizer.lua').read_bytes()
    for name,data in files.items():
        if name.endswith('.lua'):
            ok,error=CHECK(data.decode(),name)
            if not ok:raise RuntimeError(name+': '+error)
    groups={};overlay={}
    for name,data in files.items():
        if not b.keep_packed_file(name):continue
        if name.endswith(('.lua','.json','.toml','.fs','.vs','.txt')) or not Path(name).suffix:
            overlay[name]=data
        else:
            group='/'.join(name.split('/')[:2]) if name.startswith('Mods/') else 'base'
            groups.setdefault(group,{})[name]=data
    return {'mods':mods,'packs':[pack(items) for _,items in sorted(groups.items())],
            'overlay':pack(overlay),'multiplayer':mp,'cryptid':cryptid,
            'patches':sum(r['status']=='applied' for r in report)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--only');args=parser.parse_args()
    OUT.mkdir(exist_ok=True)
    (OUT/'value-randomizer.lua').write_bytes((ROOT/'browser/value-randomizer.lua').read_bytes())
    inputs=sorted([*ROOT.glob('scripts/*.py'), ROOT/'scripts/compile_cryptid_lua.mjs', ROOT/'scripts/randomize_literals.mjs', *ROOT.glob('browser/lua/**/*.lua'), ROOT/'browser/value-randomizer.lua', ROOT/'vendor/upstream.json', ROOT/'148 jokers.HTML'])
    digest=hashlib.sha256()
    for path in inputs:digest.update(path.relative_to(ROOT).as_posix().encode()+b'\0'+path.read_bytes())
    fingerprint=digest.hexdigest()
    manifest={'version':1,'fingerprint':fingerprint,'builds':{}}
    if (OUT/'manifest.json').exists():
        previous=json.loads((OUT/'manifest.json').read_text())
        if args.only or previous.get('fingerprint')==fingerprint:manifest=previous
    manifest['fingerprint']=fingerprint
    combos=[sorted(args.only.split(','))] if args.only else [list(c) for n in range(7) for c in itertools.combinations(MODS,n)]
    # Exercise the main requested combinations before the rest.
    if not args.only:combos.sort(key=lambda c:(not ('Multiplayer' in c and 'Cryptid' in c),len(c),c))
    pending=[]
    for mods in combos:
        key='+'.join(mods) or 'base';recipe=manifest['builds'].get(key)
        if recipe and all((OUT/part).exists() for pack in [*recipe['packs'],recipe['overlay']] for part in pack['parts']):
            print('Cached:',key,flush=True)
        else:pending.append(mods)
    failed=[]
    with ProcessPoolExecutor(max_workers=3,mp_context=multiprocessing.get_context('fork')) as pool:
        futures={pool.submit(compile_combo,mods):mods for mods in pending}
        for future in as_completed(futures):
            mods=futures[future];key='+'.join(mods) or 'base'
            try:
                manifest['builds'][key]=future.result()
                print(f'Completed {len(manifest["builds"])}/64: {key}',flush=True)
            except Exception as e:
                print('FAILED',key,str(e),flush=True);failed.append(key)
            (OUT/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    if failed:raise SystemExit('Unbuilt combinations: '+', '.join(failed))
    (ROOT/'build/custom-complete-manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    print('Compiled',len(manifest['builds']),'combinations')

if __name__=='__main__':main()
