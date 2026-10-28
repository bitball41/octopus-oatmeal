#!/usr/bin/env python3
"""Validate actual published recipes and randomizer behavior against Lua 5.1."""
import hashlib,io,json,zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'custom/manifest.json').read_text())
assert len(manifest['builds'])==64, 'Every supported mod subset must have a recipe'
seen={}
for key,recipe in manifest['builds'].items():
    assert key==('+'.join(sorted(recipe['mods'])) or 'base')
    for pack in [*recipe['packs'],recipe['overlay']]:
        if pack['sha256'] in seen:continue
        chunks=[]
        for name in pack['parts']:
            data=(ROOT/'custom'/name).read_bytes()
            assert 0<len(data)<=18*1024*1024
            chunks.append(data)
        blob=b''.join(chunks);assert hashlib.sha256(blob).hexdigest()==pack['sha256']
        seen[pack['sha256']]=set(zipfile.ZipFile(io.BytesIO(blob)).namelist())
for key in ['base','CardSleeves','Cryptid+Multiplayer','CardSleeves+Cryptid+Handy+Multiplayer']:
    spec=manifest['builds'][key];names=set().union(*(seen[p['sha256']] for p in [*spec['packs'],spec['overlay']]))
    assert 'Mods/ValueRandomizer/ValueRandomizer.lua' in names
    for mod in ['CardSleeves','Cryptid','Handy','Multiplayer','Bunco']:
        assert any(n.startswith('Mods/'+mod+'/') for n in names)==(mod in spec['mods']), (key,mod)

source=(ROOT/'browser/value-randomizer.lua').read_text()
def run(seed):
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
    function copy_table(t) if type(t)~='table' then return t end local r={} for k,v in pairs(t)do r[k]=copy_table(v)end return r end
    package.loaded.json={decode=function()return {randomizer=true,min=3,max=3}end}
    love={filesystem={getInfo=function()return true end,read=function()return '{}'end}}
    function localize(s)return s end
    G={P_CENTERS={j_joker={set='Joker',config={mult=4,extra={chips=20,dollars=5}}},
      m_steel={set='Enhanced',config={h_x_mult=1.5}},c_base={set='Default',config={bonus=0}},
      b_yellow={set='Back',config={dollars=10,hand_size=8}},e_foil={set='Edition',config={chips=50}},
      p_pack={set='Booster',config={choose=1,extra=3}}},P_BLINDS={boss={mult=2,dollars=5}}}
    function generate_starting_seed()return 'GENERATED'end
    Game={start_run=function(self,args)
      G.GAME=args.savetext and args.savetext.GAME or {starting_params={},round_resets={},current_round={},hands={Pair={chips=10,mult=2,l_chips=15,l_mult=1}},probabilities={normal=1},dollars=4,pseudorandom={seed=args.seed}}
      G.hand={config={}};G.jokers={config={}};G.consumeables={config={}}
    end}
    Card={set_cost=function(self)self.cost=6;self.sell_cost=3 end,
      calculate_joker=function()return {repetitions=1},'second-return'end}
    function get_blind_amount()return 300 end
    ''')
    lua.execute(source)
    lua.globals().test_seed=seed
    lua.execute('''
    Game:start_run({seed=test_seed})
    assert(G.GAME.dollars==4)
    assert(G.P_CENTERS.b_yellow.config.dollars==10)
    assert(G.P_CENTERS.m_steel.config.h_x_mult==1.5)
    assert(G.P_CENTERS.c_base.config.bonus==0)
    assert(G.P_CENTERS.j_joker.config.mult==3)
    assert(G.P_CENTERS.j_joker.config.extra.dollars==3)
    assert(G.P_CENTERS.e_foil.config.chips==3)
    assert(G.GAME.round_resets.hands==3 and G.GAME.round_resets.discards==3)
    assert(G.jokers.config.card_limit==3 and G.GAME.hands.Pair.chips==3)
    local c={config={center={key='j_mime'}},ability={extra_value=0}}
    Card.set_cost(c);assert(c.cost==3)
    local effect,second=Card.calculate_joker(c,{})
    assert(effect.repetitions==3 and second=='second-return')
    assert(get_blind_amount(1)==3)
    local saved=copy_table(G.GAME);saved.hands.Pair.chips=25
    Game:start_run({savetext={GAME=saved}})
    assert(G.GAME.hands.Pair.chips==25 and G.GAME.dollars==4)
    assert(LiminalRandomizer.seed==test_seed)
    assert(G.P_CENTERS.j_joker.config.mult==3)
    ''')
    return lua.eval("LiminalRandomizer.value('peer.same',true)")
assert run('SHARED')==run('SHARED')
print('64 exact mod recipes, pack checksums/CDN sizes, selected-only files, Lua 5.1 randomizer bounds, exclusions, return values and save restoration passed')
