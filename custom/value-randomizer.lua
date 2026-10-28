-- Optional mod: all configuration comes from the web launcher, never an in-game menu.
local fs = love.filesystem
local config = fs.getInfo('browser/build_config.json') and require('json').decode(fs.read('browser/build_config.json')) or {}
if not config.randomizer then return end
local R = {min = tonumber(config.min) or 1, max = tonumber(config.max) or 100, seed = ''}
LiminalRandomizer = R
assert(R.min == R.min and R.max == R.max and R.min <= R.max, 'Invalid randomizer bounds')

-- A stateless hash does not consume Balatro's card/shop RNG. Identical seeds,
-- build settings and effect keys produce identical rolls on both peers.
function R.value(key, integer)
    local hash = 5381
    local text = R.seed .. ':' .. tostring(R.min) .. ':' .. tostring(R.max) .. ':' .. key
    for i=1,#text do hash = (hash * 33 + text:byte(i)) % 2147483647 end
    local n = R.min + (R.max - R.min) * hash / 2147483646
    if integer then
        local lo,hi=math.ceil(R.min),math.floor(R.max)
        if lo>hi then return math.max(1,math.floor(n+0.5)) end
        n=math.min(hi,lo+math.floor(hash/2147483647*(hi-lo+1)))
    end
    return n
end
function R.literal(key, original)
    if R.seed=='' then return original end
    return R.value('literal.'..key,original==math.floor(original))
end
function R.count(key) return math.max(1,R.value(key,true)) end
local originals={}
local excluded={dollars=true,money=true,starting_money=true,starting_dollars=true,
    rank=true,suit=true,id=true,order=true,rarity=true,pos=true,atlas=true,
    card_key=true,colour=true,color=true,scale=true,rotation=true,seed=true,
    cards=true,remove_faces=true,remove_ranks=true,remove_suits=true,enhancement=true,
    probability=false,odds=false,denominator=false,numerator=false}
local counts={hands=true,discards=true,hand_size=true,h_size=true,d_size=true,
    joker_slot=true,joker_slots=true,consumable_slot=true,consumable_slots=true,
    retriggers=true,repetitions=true,extra_slots=true,choose=true}
local function clone(t) return type(t)=='table' and copy_table(t) or t end
local function randomize(t,path,deck)
    for k,v in pairs(t) do
        local key=path..'.'..tostring(k)
        local skip=excluded[k] and (deck or not (k=='dollars' or k=='money'))
        if not skip then
            if type(v)=='number' then
                -- 0/1 identity values still count when explicitly configured.
                t[k]=R.value(key,counts[k] or v==math.floor(v))
                if counts[k] then t[k]=math.max(1,t[k]) end
                if k=='odds' or k=='denominator' then t[k]=math.max(1,t[k]) end
            elseif type(v)=='table' and not v.is and not v.array then randomize(v,key,deck) end
        end
    end
end
function R.prototypes(seed)
    R.seed=tostring(seed or '')
    for key,center in pairs(G.P_CENTERS) do
        local set=center.set
        if set~='Enhanced' and set~='Default' and set~='Stake' and center.config and
           (set=='Joker' or set=='Tarot' or set=='Planet' or set=='Spectral' or set=='Voucher' or set=='Booster' or set=='Back' or set=='Sleeve' or set=='Edition' or center.consumeable) then
            if not originals[key] then originals[key]=clone(center.config) end
            center.config=clone(originals[key])
            randomize(center.config,key,set=='Back' or set=='Sleeve')
            if set=='Booster' and center.config.choose and center.config.extra then center.config.choose=math.min(center.config.choose,math.max(1,center.config.extra)) end
        end
    end
    for key,blind in pairs(G.P_BLINDS or {}) do
        blind.mult=R.value('boss.'..key..'.mult',true)
        blind.dollars=math.max(0,R.value('boss.'..key..'.dollars',true))
    end
end
local start=Game.start_run
function Game:start_run(args)
    args=args or {}
    local saved=args.savetext and args.savetext.GAME
    local seed=saved and saved.liminal_randomizer_seed or args.seed or generate_starting_seed()
    R.prototypes(seed)
    local explicit_seed=args.seed
    if not saved then args.seed=seed end
    local result=start(self,args)
    G.GAME.liminal_randomizer_seed=seed
    if not saved then
        G.GAME.seeded=not not explicit_seed
        for _,key in ipairs({'hands','discards','hand_size','joker_slots','consumable_slots'}) do
            G.GAME.starting_params[key]=R.count('run.'..key)
        end
        G.GAME.round_resets.hands=G.GAME.starting_params.hands
        G.GAME.round_resets.discards=G.GAME.starting_params.discards
        G.GAME.current_round.hands_left=G.GAME.round_resets.hands
        G.GAME.current_round.discards_left=G.GAME.round_resets.discards
        G.hand.config.card_limit=G.GAME.starting_params.hand_size
        G.jokers.config.card_limit=G.GAME.starting_params.joker_slots
        G.consumeables.config.card_limit=G.GAME.starting_params.consumable_slots
        for name,hand in pairs(G.GAME.hands) do
            for _,k in ipairs({'chips','mult','l_chips','l_mult'}) do hand[k]=R.value('hand.'..name..'.'..k,true) end
        end
        G.GAME.base_reroll_cost=math.max(0,R.value('shop.reroll',true))
        G.GAME.round_resets.reroll_cost=G.GAME.base_reroll_cost
        G.GAME.current_round.reroll_cost=G.GAME.base_reroll_cost
        for key in pairs(G.GAME.probabilities) do G.GAME.probabilities[key]=math.max(0,R.value('probability.'..key,false)) end
    end
    return result
end
local cost=Card.set_cost
function Card:set_cost(...)
    local result=cost(self,...)
    if G.GAME and G.GAME.liminal_randomizer_seed and self.config and self.config.center and not self.playing_card then
        local key=self.config.center.key or self.ability.name
        self.cost=math.max(0,R.value('cost.'..key,true))
        self.sell_cost=math.max(0,math.floor(self.cost/2))+(self.ability.extra_value or 0)
        self.sell_cost_label=self.facing=='back' and '?' or self.sell_cost
    end
    return result
end
local blind_amount=get_blind_amount
function get_blind_amount(ante)
    if G.GAME and G.GAME.liminal_randomizer_seed then return math.max(1,R.value('blind.'..tostring(ante),true)) end
    return blind_amount(ante)
end
-- Hardcoded vanilla effects without a configurable prototype (Mime, Chad, etc.).
local repeat_defaults={j_mime=1,j_hack=1,j_dusk=1,j_sock_and_buskin=1,j_seltzer=1,j_hanging_chad=2}
local calculate=Card.calculate_joker
function Card:calculate_joker(context)
    local effect,post=calculate(self,context)
    local key=self.config and self.config.center and self.config.center.key
    if type(effect)=='table' and effect.repetitions and repeat_defaults[key] then
        effect.repetitions=R.count(key..'.repetitions')
        effect.message=localize('k_again_ex')
    end
    return effect,post
end
-- Show hardcoded retrigger counts in the existing descriptions too.
for key in pairs(repeat_defaults) do
    local center=G.P_CENTERS[key]
    if center then
        local previous=center.loc_vars
        center.loc_vars=function(self,info_queue,card)
            local result=previous and previous(self,info_queue,card) or {vars={}}
            result.vars=result.vars or {};result.vars[1]=R.count(key..'.repetitions')
            return result
        end
    end
end
