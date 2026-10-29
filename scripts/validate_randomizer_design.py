#!/usr/bin/env python3
"""Test playable-run invariants, not just whether random numbers are in range."""
from pathlib import Path
from statistics import median
from lupa.lua51 import LuaRuntime
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'browser/value-randomizer.lua').read_text()

def runtime(minimum=0.1,maximum=10):
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.globals().minimum=minimum;lua.globals().maximum=maximum
    lua.execute('''
    function copy_table(t) if type(t)~='table' then return t end local r={} for k,v in pairs(t) do r[k]=copy_table(v) end return r end
    package.loaded.json={decode=function() return {randomizer=true,min=minimum,max=maximum} end}
    love={filesystem={getInfo=function()return true end,read=function()return '{}'end}}
    G={P_CENTERS={
      j_joker={set='Joker',config={mult=4}},j_blue_joker={set='Joker',config={extra=2}},
      j_scholar={set='Joker',config={extra={chips=20,mult=4}}},
      j_runner={set='Joker',config={extra={chips=0,chip_mod=15}}},
      j_constellation={set='Joker',config={extra=0.1,Xmult=1}},
      j_duo={set='Joker',config={Xmult=2}},j_gros_michel={set='Joker',config={extra={odds=6,mult=15}}},
      j_ice_cream={set='Joker',config={extra={chips=100,chip_mod=5}}},
      j_reserved_parking={set='Joker',config={extra={odds=2,dollars=1}}},
      j_burglar={set='Joker',config={extra=3}},j_mime={set='Joker',config={extra=1}},
      j_hanging_chad={set='Joker',config={extra=2}},j_selzer={set='Joker',config={extra=10}},
      j_modded={set='Joker',config={extra={repetitions=2,unknown=4}}},
      m_steel={set='Enhanced',config={h_x_mult=1.5}},c_base={set='Default',config={bonus=0}},
      b_yellow={set='Back',config={dollars=10,hand_size=2,joker_slot=-1}},
      s_sleeve={set='Sleeve',config={dollars=8,joker_slot=-1}},
      e_foil={set='Edition',config={chips=50}},p_pack={set='Booster',config={choose=1,extra=3}},
      c_tarot={set='Tarot',config={min_highlighted=1,max_highlighted=2}}
    },P_BLINDS={small={mult=1,dollars=3},big={mult=1.5,dollars=4},boss={mult=2,dollars=5}}}
    function generate_starting_seed()return 'GENERATED'end
    Game={start_run=function(self,args)
      G.GAME=args.savetext and args.savetext.GAME or {starting_params={hands=4,discards=3,hand_size=8,joker_slots=5,consumable_slots=2},round_resets={hands=4,discards=3},current_round={},base_reroll_cost=5,hands={Pair={chips=10,mult=2,l_chips=15,l_mult=1}},probabilities={normal=1},dollars=4,pseudorandom={seed=args.seed}}
      G.hand={config={card_limit=8}};G.jokers={config={card_limit=5}};G.consumeables={config={card_limit=2}}
    end}
    Card={set_cost=function(self)
      self.cost=self.native_cost or 6;self.sell_cost=math.max(1,math.floor(self.cost/2))+(self.ability.extra_value or 0)
    end,calculate_joker=function(self)
      if self.inner then Card.calculate_joker(self.inner,{}) end
      return {repetitions=LiminalRandomizer.literal('card.lua:123:repetitions',1),
              mult_mod=LiminalRandomizer.literal('card.lua:124:mult_mod',4)},'second-return'
    end}
    function get_blind_amount(ante)return 300*2^(ante-1) end
    ''')
    lua.execute(SOURCE)
    return lua

def validate():
    lua=runtime()
    lua.execute('''
    for i=1,500 do
      Game:start_run({seed='RUN'..i})
      local R=LiminalRandomizer
      -- No random roll can decide the entire run at setup.
      assert(G.GAME.dollars==4 and G.hand.config.card_limit==8)
      assert(G.GAME.round_resets.hands==4 and G.GAME.round_resets.discards==3)
      assert(G.jokers.config.card_limit==5 and G.consumeables.config.card_limit==2)
      assert(G.GAME.hands.Pair.chips==10 and G.GAME.hands.Pair.mult==2)
      assert(G.GAME.probabilities.normal==1)
      assert(G.P_CENTERS.b_yellow.config.hand_size==2 and G.P_CENTERS.b_yellow.config.joker_slot==-1)
      assert(G.P_CENTERS.b_yellow.config.dollars==10 and G.P_CENTERS.s_sleeve.config.dollars==8)
      assert(G.P_CENTERS.m_steel.config.h_x_mult==1.5 and G.P_CENTERS.c_base.config.bonus==0)
      assert(G.P_CENTERS.j_constellation.config.Xmult==1 and G.P_CENTERS.j_runner.config.extra.chips==0)
      local scholar=G.P_CENTERS.j_scholar.config.extra
      assert(math.abs(scholar.chips/20-scholar.mult/4)<1e-10)
      local ice=G.P_CENTERS.j_ice_cream.config.extra
      assert(math.abs(ice.chips/ice.chip_mod-20)<1e-10)
      assert(G.P_CENTERS.j_mime.config.extra==1 and G.P_CENTERS.j_hanging_chad.config.extra==2)
      assert(G.P_CENTERS.j_burglar.config.extra>=2 and G.P_CENTERS.j_burglar.config.extra<=4)
      assert(G.P_CENTERS.j_modded.config.extra.repetitions>=1 and G.P_CENTERS.j_modded.config.extra.repetitions<=3)
      local pack=G.P_CENTERS.p_pack.config
      assert(pack.choose>=1 and pack.choose<=pack.extra and pack.extra<=4)
      local tarot=G.P_CENTERS.c_tarot.config
      assert(tarot.min_highlighted>=1 and tarot.min_highlighted<=tarot.max_highlighted)
      assert(tarot.min_highlighted==1 and tarot.max_highlighted==2)
      assert(G.P_CENTERS.j_reserved_parking.config.extra.odds>=2)
      assert(G.P_CENTERS.j_reserved_parking.config.extra.dollars<=2)
      local last=0
      for ante=1,12 do
        local amount=get_blind_amount(ante);local base=300*2^(ante-1)
        assert(amount>last and amount>=base*0.9-0.5 and amount<=base*1.1+0.5);last=amount
      end
      assert(G.P_BLINDS.small.mult==1 and G.P_BLINDS.big.mult==1.5 and G.P_BLINDS.boss.mult==2)
      assert(G.GAME.base_reroll_cost>=4 and G.GAME.base_reroll_cost<=6)
      local c={config={center={key='j_joker'}},ability={extra_value=2}}
      Card.set_cost(c);local price=c.cost;assert(price>=5 and price<=9)
      assert(c.sell_cost==math.max(1,math.floor(price/2))+2)
      Card.set_cost(c);assert(c.cost==price)
      c.native_cost=0;Card.set_cost(c);assert(c.cost==0)
      c.native_cost=1;c.ability.rental=true;Card.set_cost(c);assert(c.cost==1)
      local inner={config={center={key='j_mime'}}}
      local effect,second=Card.calculate_joker({config={center={key='j_scholar'}},inner=inner},{})
      assert(second=='second-return' and math.abs(effect.mult_mod-scholar.mult)<1e-10)
      assert(R.active_center==nil)
      assert(R.literal('card.lua:125:Xmult_mod',1)==1)
      assert(Card.calculate_joker(inner,{}).repetitions==1)
    end
    local saved=copy_table(G.GAME);saved.hands.Pair.chips=87;saved.round_resets.hands=6
    local previous=G.P_CENTERS.j_blue_joker.config.extra
    Game:start_run({savetext={GAME=saved}})
    assert(G.GAME.hands.Pair.chips==87 and G.GAME.round_resets.hands==6)
    assert(G.P_CENTERS.j_blue_joker.config.extra==previous)
    ''')
    factors=lua.execute("local t={} for i=1,10000 do LiminalRandomizer.seed='SAMPLE'..i;t[i]=LiminalRandomizer.strength('j_blue_joker') end return t")
    rolls=sorted(factors[i] for i in range(1,10001))
    below=sum(x<1 for x in rolls)/len(rolls)
    extreme=sum(x>5 for x in rolls)/len(rolls)
    assert 0.47<below<0.53 and 0.9<median(rolls)<1.1,(below,median(rolls))
    assert 0.025<extreme<0.07 and min(rolls)>=0.1 and max(rolls)<=10,extreme
    for factor in (0,1,2,10,100):
        fixed=runtime(factor,factor);fixed.globals().factor=factor
        fixed.execute('''
        Game:start_run({seed='FIXED'})
        assert(G.P_CENTERS.j_blue_joker.config.extra==2*factor)
        assert(G.P_CENTERS.j_constellation.config.Xmult==1)
        assert(G.P_CENTERS.j_duo.config.Xmult==1+factor)
        assert(G.GAME.hands.Pair.chips==10 and G.GAME.round_resets.hands==4)
        assert(G.jokers.config.card_limit==5)
        ''')
    for bounds in ((0,0.2),(0.1,0.2),(3,3.5)):
        narrow=runtime(*bounds)
        for i in range(100):
            n=narrow.eval(f"LiminalRandomizer.factor('edge.{i}')")
            assert bounds[0]<=n<=bounds[1]
    a,b=runtime(),runtime()
    for peer in (a,b):peer.execute("Game:start_run({seed='SAME_PEER_SEED'})")
    assert a.eval('G.P_CENTERS.j_scholar.config.extra.chips')==b.eval('G.P_CENTERS.j_scholar.config.extra.chips')
    print(f'Design: 500 seeded runs keep native budgets/progression; 10,000 rolls: median {median(rolls):.3f}x, {below:.1%} below 1x, {extreme:.1%} above 5x; safe costs, odds, counts, growth, saves and peers passed')

if __name__=='__main__':validate()
