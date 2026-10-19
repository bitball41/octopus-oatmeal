#!/usr/bin/env python3
"""Compare bulk sales with serial sales using packed Cryptid/SMODS Lua 5.1.

Rendering is stubbed. The sell callback, sell_card, can_sell_card, event engine,
context/retrigger loops, Crypto Coin and Loopy calculations are shipped code.
"""
import io
import json
import zipfile
from pathlib import Path
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
directory = ROOT / 'cryptid'
z = zipfile.ZipFile(io.BytesIO(b''.join((directory/n).read_bytes()
    for n in json.loads((directory/'parts.json').read_text()))))
files = {name: z.read(name).decode() for name in z.namelist() if name.endswith('.lua')}


def block(source, anchor):
    begin = source.index(anchor)
    end = source.index('\nend', begin) + 4
    return source[begin:end]


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(files['browser/bignum_compare.lua'])
    lua.execute(files['engine/object.lua'])
    lua.execute('''
        clock=0; saves=0; evaluations=0; money_events=0; sold=0; self_sales=0
        function noop() end
        function HEX() return {} end
        function localize(v) return v end
        function to_big(v) return v end
        function lenient_bignum(v) return v end
        function pseudoseed(v) return v end
        function pseudorandom() return math.random() end
        function card_eval_status_text() end
        function play_sound() end
        function attention_text() end
        function juice_card() end
        function delay() end
        function Particles() return {fade=noop} end
        function save_run() saves=saves+1 end
        function inc_career_stat(key) if key=='c_jokers_sold' then sold=sold+1 end end
        love={timer={getTime=function() clock=clock+0.00001; return clock end},
              keypressed=noop, mousepressed=noop, wheelmoved=noop}
        G={STAGE=1,STAGES={RUN=1},STATE=2,STATES={SHOP=2},
           GAME={dollars=0,dollar_buffer=0,STOP_USE=0,modifiers={},round_resets={ante=1}},
           SETTINGS={paused=false,tutorial_complete=true},TIMERS={REAL=0,TOTAL=0},ARGS={},
           C={RED={},GOLD={},GREEN={}},CONTROLLER={locked=false,locks={},
              save_cardarea_focus=noop,recall_cardarea_focus=noop},FUNCS={}}
        G.jokers={cards={},config={type='joker'}}
        Card=Object:extend(); Moveable={juice_up=noop}
        function Card:init(center)
            self.config={center=center}; self.children={}; self.sell_cost=2
            self.ability={set='Joker',extra={},immutable={}}; self.area=G.jokers
            if center.config then
                for k,v in pairs(center.config.extra or {}) do self.ability.extra[k]=v end
                for k,v in pairs(center.config.immutable or {}) do self.ability.immutable[k]=v end
            end
            table.insert(G.jokers.cards,self)
        end
        function Card:juice_up() end
        function Card:stop_hover() end
        function Card:is_jolly() return self.config.center.key=='j_jolly' end
        function Card.get_gameset() return 'madness' end
        function Card:start_dissolve()
            G.E_MANAGER:add_event(Event{trigger='after',delay=0.3,func=function()
                self:remove(); return true
            end})
        end
        function Card:remove()
            for i,c in ipairs(self.area.cards) do
                if c==self then table.remove(self.area.cards,i);break end
            end
            self.REMOVED=true;self.area=nil
        end
        SMODS={optional_features={retrigger_joker=true},context_stack={},ease_types={lerp=function(v) return v end}}
        function SMODS.is_eternal(card) return card.ability.eternal end
        function SMODS.check_looping_context() return false end
        function SMODS.get_card_areas(t) return t=='jokers' and {G.jokers} or {} end
        function SMODS.can_context_retrigger(c) return not c.retrigger_joker_check and not c.retrigger_joker end
        function SMODS.update_context_flags() end
        function SMODS.log_crash_info() return '' end
        function SMODS.push_to_context_stack(c) table.insert(SMODS.context_stack,c) end
        function SMODS.pop_from_context_stack(c) assert(table.remove(SMODS.context_stack)==c) end
        function ease_dollars(n)
            G.GAME.dollars=G.GAME.dollars+n;money_events=money_events+1
        end
        function eval_card(card,context)
            evaluations=evaluations+1
            if context.selling_self then self_sales=self_sales+1 end
            local effect=card.config.center.calculate and card.config.center:calculate(card,context)
            local result=effect and {jokers=effect} or {}
            if not context.retrigger_joker_check and not context.retrigger_joker then
                result.retriggers=SMODS.calculate_retriggers(card,context,result)
            end
            return result,{}
        end
        function SMODS.trigger_effects(effects)
            for _,t in ipairs(effects) do
                for _,effect in pairs(t) do
                    if effect.dollars then ease_dollars(effect.dollars) end
                    if effect.func then effect.func() end
                end
            end
            return {}
        end
        Handy={speed_multiplier={},ARGS={},animation_skip={mute_ease_dollars=0,
            is_skippable_timer=function(t) return t~='REAL' end,
            is_skippable_queue=function(q) return not q or q=='base' end,
            should_skip_unsafe=function() return false end,
            should_skip_everything=function() return false end},
            dangerous_actions={queues={game={},preview={}}},insta_actions={},
            UI={state_panel={display=function(f) f({items={}}) end,update=noop}},
            e_mitter={on=noop}}
        function Handy.dangerous_actions.can_process_card(c) return not c.REMOVED and not c.handy_dangerous_actions_used end
        function Handy.dangerous_actions.process_card(c,remove)
            c.handy_dangerous_actions_used=true
            table.insert(Handy.dangerous_actions.queues.game,{card=c,remove=remove})
        end
    ''')
    lua.execute(files['engine/event.lua'])
    lua.execute(files['Mods/Handy/src/controls/animation_skip/event_manager.lua'])
    lua.execute('G.E_MANAGER=EventManager()')
    misc = files['functions/misc_functions.lua']
    lua.execute(block(misc, 'function stop_use()'))
    lua.execute(block(misc, 'function dec_stop_use('))
    for anchor in ('SMODS.insert_repetitions = function', 'SMODS.calculate_retriggers = function',
                   'function SMODS.calculate_card_areas(', 'function SMODS.calculate_context('):
        lua.execute(block(files['Mods/Steamodded/src/utils.lua'], anchor))
    lua.execute(block(files['card.lua'], 'function Card:sell_card('))
    lua.execute(block(files['card.lua'], 'function Card:can_sell_card('))
    lua.execute(block(files['card.lua'], 'function Card:start_dissolve('))
    callbacks = files['functions/button_callbacks.lua']
    begin = callbacks.index('G.FUNCS.sell_card = function(e)')
    end = callbacks.index('\n  end', begin) + len('\n  end')
    lua.execute(callbacks[begin:end])
    for path, name, following in [('items/m.lua','loopy','scrabble'),
                                  ('items/misc_joker.lua','coin','wheelhope')]:
        source = files['Mods/Cryptid/' + path]
        begin = source.index('local ' + name + ' = {')
        end = source.index('local ' + following + ' = {', begin)
        lua.globals()[name] = lua.execute(source[begin:end] + '\nreturn ' + name)
    lua.execute('''
        function love.update(dt)
            assert(#SMODS.context_stack==0,'Game.update ran during an unfinished sell context')
            G.TIMERS.TOTAL=G.TIMERS.TOTAL+dt;G.TIMERS.REAL=G.TIMERS.REAL+dt
            G.E_MANAGER:update(dt,true)
        end
        function settle()
            for i=1,100000 do
                love.update(1/60)
                if not Handy.browser.job and not next(G.E_MANAGER.queues.base) then return i end
            end
            error('bulk operation never finished')
        end
        function fixture(n)
            math.randomseed(124)
            coin.key='j_cry_coin';loopy.key='j_cry_loopy'
            c=Card(coin);l=Card(loopy)
            -- A money-dependent effect detects payout batching or stale money.
            Card{key='scaler',calculate=function(self,card,ctx)
                if ctx.selling_card then
                    card.ability.extra.n=(card.ability.extra.n or 0)+1
                    card.ability.extra.seen=G.GAME.dollars
                end
            end}
            targets={}
            for i=1,n do targets[i]=Card{key='j_jolly'} end
        end
        function outcome()
            return table.concat({G.GAME.dollars,money_events,l.ability.extra.retrigger,
                sold,self_sales,evaluations,#G.jokers.cards,G.GAME.dollar_buffer,
                G.jokers.cards[3].ability.extra.n or 0,
                G.jokers.cards[3].ability.extra.seen or 0},':')
        end
    ''')
    lua.execute(files['browser/handy.lua']).install()
    return lua


for n in (1, 35, 100):
    reference, bulk = runtime(), runtime()
    for lua in (reference, bulk):
        lua.globals().fixture(n)
    reference.execute('for _,card in ipairs(targets) do G.FUNCS.sell_card{config={ref_table=card}};settle() end')
    bulk.execute('''
        math.randomseed(124)
        for _,card in ipairs(targets) do Handy.dangerous_actions.process_card(card,false) end
        Handy.dangerous_actions.process_game_queue();settle()
        assert(not G.CONTROLLER.locks.handy_bulk_sell)
        assert(saves==1,'bulk must save once after all effects settle')
        assert(Handy.speed_multiplier.max_speed==512)
        assert(not Handy.animation_skip.can_dangerous())
    ''')
    assert reference.globals().outcome() == bulk.globals().outcome(), (n, reference.globals().outcome(), bulk.globals().outcome())
    print(f'{n} Jokers: bulk equals serial money, individual payouts, RNG, Loopy scaling, retriggers, sell stats and remaining cards')

lua = runtime()
lua.execute('''
    fixture(10);targets[2].ability.eternal=true
    for _,card in ipairs(targets) do Handy.dangerous_actions.process_card(card,false) end
    Handy.dangerous_actions.process_game_queue()
    -- New cards generated after selection must survive the original snapshot.
    local generated=Card{key='j_jolly'}
    settle()
    assert(sold==9 and not targets[2].REMOVED and not generated.REMOVED)
    assert(not targets[2].handy_dangerous_actions_used)
''')
print('Eternal revalidation, stable target snapshot and flag cleanup passed')

lua = runtime()
lua.execute('''
    fixture(4)
    local probe=Card{key='probe',calculate=function(self,card,ctx)
        if ctx.selling_card then
            local ok,err=pcall(function() eval_card(card,{retrigger_joker_check=true}) end)
            assert(ok,err)
        end
    end}
    for _,card in ipairs(targets) do Handy.dangerous_actions.process_card(card,false) end
    Handy.dangerous_actions.process_game_queue()
    Handy.browser.frame_budget=0.0005;settle();assert(sold==4)
''')
print('Protected mod calculations survive Lua 5.1 coroutine yield boundaries')

lua = runtime()
lua.execute('''
    fixture(2);inline_calls=0
    Card{key='inline_probe',calculate=function(self,card,ctx)
        if ctx.selling_card then
            Handy.ARGS.extract_func_from_event=1
            G.E_MANAGER:add_event(Event{func=function()
                inline_calls=inline_calls+1
                G.E_MANAGER:add_event(Event{func=function() inline_calls=inline_calls+1;return true end})
                return true
            end})
        end
    end}
    for _,card in ipairs(targets) do Handy.dangerous_actions.process_card(card,false) end
    Handy.dangerous_actions.process_game_queue();settle()
    assert(sold==2 and inline_calls>0 and not Handy.browser.job)
''')
print('Handy inline callbacks and their queued descendants settle without phantom pending events')

lua = runtime()
lua.execute('''
    fixture(1000)
    for _,card in ipairs(targets) do Handy.dangerous_actions.process_card(card,false) end
    Handy.dangerous_actions.process_game_queue()
    Handy.browser.frame_budget=0.00005
    love.update(1/60)
    assert(Handy.browser.co,'large sale must yield while retaining its context')
    Handy.browser.frame_budget=0.004
    love.keypressed('escape');settle()
    assert(sold==1,'cancellation must finish the current sale only')
    assert(saves==1 and #SMODS.context_stack==0 and not Handy.browser.job)
    for _,c in ipairs(targets) do assert(not c.handy_dangerous_actions_used) end
''')
print('1,000-card selection yields; cancellation completes the current sale and preserves the rest')

# Execute the shipped payout hook independently of rendering: money_altered
# consumers must still see every payment even when animation skipping is on.
lua = LuaRuntime()
lua.execute('''
    payouts={};Moveable={};SMODS={};G={}
    Handy={animation_skip={ease_dollars_buffer=0,
        should_skip_animation=function() return true end},ARGS={}}
    function ease_dollars(n,instant,tag) table.insert(payouts,n);assert(instant and tag=='preserved') end
''')
hooks = files['Mods/Handy/src/controls/animation_skip/hooks.lua']
begin = hooks.index('local ease_dollars_ref = ease_dollars')
end = hooks.index('\n-- Other', begin)
lua.execute(hooks[begin:end])
lua.execute("ease_dollars(7,false,'preserved');ease_dollars(13,true,'preserved');assert(#payouts==2 and payouts[1]==7 and payouts[2]==13 and Handy.animation_skip.ease_dollars_buffer==0)")
print('Animation skipping preserves each individual payout without a combined money update')
