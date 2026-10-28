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
def run(seed,minimum=3,maximum=3):
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.globals().test_min=minimum
    lua.globals().test_max=maximum
    lua.execute('''
    function copy_table(t) if type(t)~='table' then return t end local r={} for k,v in pairs(t)do r[k]=copy_table(v)end return r end
    package.loaded.json={decode=function()return {randomizer=true,min=test_min,max=test_max}end}
    love={filesystem={getInfo=function()return true end,read=function()return '{}'end}}
    function localize(s)return s end
    G={P_CENTERS={j_joker={set='Joker',config={mult=4,extra={chips=20,dollars=5}}},
      m_steel={set='Enhanced',config={h_x_mult=1.5}},c_base={set='Default',config={bonus=0}},
      b_yellow={set='Back',config={dollars=10,hand_size=8,joker_slot=-1}},e_foil={set='Edition',config={chips=50}},
      j_blue_joker={set='Joker',config={extra=2}},j_runner={set='Joker',config={extra={chips=0,chip_mod=15}}},
      p_pack={set='Booster',config={choose=1,extra=3}}},P_BLINDS={boss={mult=2,dollars=5}}}
    function generate_starting_seed()return 'GENERATED'end
    Game={start_run=function(self,args)
      G.GAME=args.savetext and args.savetext.GAME or {starting_params={hands=4,discards=3,hand_size=8,joker_slots=5,consumable_slots=2},round_resets={hands=4,discards=3},current_round={},base_reroll_cost=5,hands={Pair={chips=10,mult=2,l_chips=15,l_mult=1}},probabilities={normal=1},dollars=4,pseudorandom={seed=args.seed}}
      G.hand={config={card_limit=8}};G.jokers={config={card_limit=5}};G.consumeables={config={card_limit=2}}
    end}
    Card={set_cost=function(self)self.cost=6;self.sell_cost=3 end,
      calculate_joker=function()return {repetitions=1},'second-return'end}
    function get_blind_amount(ante)return 300*2^(ante-1) end
    ''')
    lua.execute(source)
    lua.globals().test_seed=seed
    return lua

def fixed_factor(seed,factor):
    lua=run(seed,factor,factor)
    lua.globals().factor=factor
    lua.execute('''
    Game:start_run({seed=test_seed})
    assert(G.GAME.dollars==4)
    assert(G.P_CENTERS.b_yellow.config.dollars==10)
    assert(G.P_CENTERS.m_steel.config.h_x_mult==1.5)
    assert(G.P_CENTERS.c_base.config.bonus==0)
    assert(G.P_CENTERS.j_joker.config.mult==4*factor)
    assert(G.P_CENTERS.j_joker.config.extra.dollars==5*factor)
    assert(G.P_CENTERS.j_blue_joker.config.extra==2*factor)
    assert(G.P_CENTERS.j_runner.config.extra.chips==0)
    assert(G.P_CENTERS.b_yellow.config.joker_slot==-factor)
    assert(G.P_CENTERS.e_foil.config.chips==50*factor)
    assert(G.GAME.round_resets.hands==4*factor and G.GAME.round_resets.discards==3*factor)
    assert(G.jokers.config.card_limit==5*factor and G.GAME.hands.Pair.chips==10*factor)
    assert(G.GAME.base_reroll_cost==5*factor and G.GAME.probabilities.normal==factor)
    assert(G.P_BLINDS.boss.mult==2*factor and G.P_BLINDS.boss.dollars==5*factor)
    local c={config={center={key='j_mime'}},ability={extra_value=0}}
    Card.set_cost(c);assert(c.cost==6*factor)
    Card.set_cost(c);assert(c.cost==6*factor) -- Recalculation must not compound.
    local effect,second=Card.calculate_joker(c,{})
    assert(effect.repetitions==factor and second=='second-return')
    c.config.center.key='j_hanging_chad'
    assert(Card.calculate_joker(c,{}).repetitions==2*factor)
    assert(LiminalRandomizer.literal('blue_joker:chip_mod',2)==2*factor)
    assert(get_blind_amount(1)==300*factor and get_blind_amount(2)==600*factor)
    local saved=copy_table(G.GAME);saved.hands.Pair.chips=25
    Game:start_run({savetext={GAME=saved}})
    assert(G.GAME.hands.Pair.chips==25 and G.GAME.dollars==4)
    assert(LiminalRandomizer.seed==test_seed)
    assert(G.P_CENTERS.j_joker.config.mult==4*factor)
    assert(G.P_BLINDS.boss.mult==2*factor) -- Restoring prototypes must not compound.
    ''')
for factor in (1,2,3,10,100):fixed_factor('SHARED',factor)
for seed in ('SHARED','DIFFERENT'):
    lua=run(seed,0.5,2)
    lua.execute('''
    Game:start_run({seed=test_seed})
    for i=1,200 do
        local v=LiminalRandomizer.value('sample.'..i,2,true)
        assert(v>=1 and v<=4)
        local fraction=LiminalRandomizer.value('fraction.'..i,0.2,false)
        assert(fraction>=0.1 and fraction<=0.4)
    end
    local last=0
    for ante=1,12 do local amount=get_blind_amount(ante);assert(amount>last);last=amount end
    assert(G.GAME.round_resets.hands>=2 and G.GAME.round_resets.hands<=8)
    assert(G.jokers.config.card_limit>=3 and G.jokers.config.card_limit<=10)
    ''')
a,b=run('SHARED',0.5,2),run('SHARED',0.5,2)
for lua in (a,b):lua.execute("LiminalRandomizer.prototypes('SHARED')")
assert a.eval("LiminalRandomizer.value('peer.same',2,true)")==b.eval("LiminalRandomizer.value('peer.same',2,true)")
print('64 exact mod recipes, checksums, multiplier math (including 1x identity and 100x), ante progression, exclusions, multiplayer determinism and save restoration passed')
