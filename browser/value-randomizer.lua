-- Optional mod. Configuration is supplied by the launcher, never an in-game UI.
local fs = love.filesystem
local config = fs.getInfo('browser/build_config.json') and require('json').decode(fs.read('browser/build_config.json')) or {}
if not config.randomizer then return end
local R = {min=tonumber(config.min) or 0.1, max=tonumber(config.max) or 10, seed='', policy='designed-v3'}
LiminalRandomizer = R
assert(R.min>=0 and R.min==R.min and R.max==R.max and R.min<=R.max, 'Invalid randomizer bounds')
local function clamp(n,lo,hi) return math.max(lo,math.min(hi,n)) end
local function round(n) return math.floor(n+0.5) end

-- Stateless rolls leave gameplay RNG untouched and agree on both peers.
function R.unit(key)
    local hash=5381
    local text=R.policy..':'..R.seed..':'..tostring(R.min)..':'..tostring(R.max)..':'..key
    for i=1,#text do hash=(hash*33+text:byte(i))%2147483647 end
    for i=1,3 do hash=(hash*48271)%2147483647 end
    return hash/2147483647
end
function R.factor(key)
    if R.min==R.max then return R.min end
    if R.roll_seed~=R.seed then R.roll_seed=R.seed;R.rolls={} end
    if R.rolls[key]~=nil then return R.rolls[key] end
    -- Triangular in log space, with its mode at 1x. At 0.1x--10x,
    -- half of rolls buff and half nerf; extreme rolls are uncommon.
    local lower=R.min>0 and R.min or math.min(0.0001,R.max/10000)
    local lo,hi=math.log(lower),math.log(R.max)
    local mode=math.log(clamp(1,lower,R.max))
    local u=R.unit(key)
    local split=(mode-lo)/(hi-lo)
    local value
    if u<split then value=lo+math.sqrt(u*(hi-lo)*(mode-lo))
    else value=hi-math.sqrt((1-u)*(hi-lo)*(hi-mode)) end
    local result=clamp(math.exp(value),R.min,R.max)
    R.rolls[key]=result
    return result
end
function R.value(key,original,integer)
    local n=original*R.factor(key)
    if integer then n=round(n) end
    return n
end
function R.strength(center) return R.factor('center.'..center) end
function R.apply(key,original,kind,center)
    if original==0 or kind=='fixed' then return original end
    local f=R.strength(center or key)
    if kind=='score' then return original*f end
    if kind=='xmult' then
        -- Scale the bonus, never turn an unbuilt x1 scaler into free x10.
        if original>=1 then return 1+(original-1)*f end
        return original*clamp(f^0.25,0.5,2)
    end
    if kind=='count' then
        local magnitude=math.abs(original)
        local radius=math.max(1,math.floor(magnitude*0.25))
        local n=round(magnitude*clamp(f^0.2,0.75,1.5))
        n=clamp(n,math.max(1,magnitude-radius),magnitude+radius)
        return original<0 and -n or n
    end
    if kind=='cash' then
        local n=round(math.abs(original)*clamp(f^0.25,0.5,2))
        return (original<0 and -1 or 1)*math.max(1,n)
    end
    if kind=='odds' then
        local minimum=original>1 and 2 or 1
        return math.max(minimum,round(original*clamp(f^(-0.2),2/3,1.5)))
    end
    if kind=='chance' then return clamp(original*clamp(f^0.2,2/3,1.5),0,1) end
    local n=original*clamp(f^0.12,0.8,1.25)
    if original==math.floor(original) then n=round(n) end
    return n
end
function R.count(key,original)
    local center=key:match('^(j_[^%.]+)') or key
    return math.max(1,R.apply(key,original or 1,'count',center))
end

local counts={hands=true,discards=true,hand_size=true,h_size=true,d_size=true,
    h_plays=true,h_mod=true,joker_slot=true,joker_slots=true,consumable_slot=true,
    consumable_slots=true,retriggers=true,repetitions=true,extra_slots=true,
    choose=true,max_highlighted=true,min_highlighted=true,extra_cards=true}
local fixed={size=true,faces=true,every=true,rank=true,suit=true,id=true,order=true,
    rarity=true,pos=true,atlas=true,card_key=true,colour=true,color=true,scale=true,
    rotation=true,seed=true,cards=true,remove_faces=true,remove_ranks=true,
    remove_suits=true,enhancement=true,ante_scaling=true,starting_money=true,
    starting_dollars=true,remaining=true,min_highlighted=true,max_highlighted=true}
local extra_kinds={}
local function tag(kind,names) for name in names:gmatch('%S+') do extra_kinds['j_'..name]=kind end end
-- Vanilla uses the same opaque `extra` field for very different mechanics.
-- Unknown mod fields get gentle rolls until their meaning is known.
tag('score','banner fibonacci steel_joker scary_face abstract even_steven odd_todd supernova ride_the_bus blue_joker constellation hiker red_card madness vampire hologram obelisk erosion fortune_teller stone lucky_cat bull flash popcorn trousers ramen smiley campfire throwback arrowhead onyx_agate glass shoot_the_moon hit_the_road caino')
tag('xmult','blackboard baron photograph baseball ancient acrobat flower_pot idol seeing_double drivers_license triboulet')
tag('cash','credit_card delayed_grat egg cloud_9 gift mail to_the_moon golden trading ticket rough_gem matador satellite')
tag('odds','8_ball business space hallucination')
tag('count','burglar selzer seltzer invisible')
tag('fixed','vagabond burnt mime dusk hack sock_and_buskin hanging_chad marble chaos riff_raff')
local repeat_defaults={j_mime=1,j_hack=1,j_dusk=1,j_sock_and_buskin=1,j_selzer=1,j_seltzer=1,j_hanging_chad=2}
local function kind_for(field,original,center)
    local name=tostring(field):lower()
    if fixed[name] then return 'fixed' end
    if (name=='repetitions' or name=='retriggers') and repeat_defaults[center.key] then return 'fixed' end
    if counts[name] then return 'count' end
    if name=='odds' or name=='denominator' then return 'odds' end
    if name=='probability' or name=='numerator' then return original<=1 and 'chance' or 'odds' end
    if name:find('dollar') or name:find('money') or name:find('cost') or name=='extra_value' then return 'cash' end
    if center.set=='Booster' and name=='extra' then return 'count' end
    if center.set=='Edition' then return 'gentle' end
    if center.set~='Joker' then return 'gentle' end
    if name=='extra' then return extra_kinds[center.key] or 'gentle' end
    if name:find('mult') then
        if name:find('x') and not name:find('mod') then return 'xmult' end
        return 'score'
    end
    if name:find('chip') or name=='bonus' or name=='hand_add' or name=='discard_sub' or
       (center.key=='j_misprint' and (name=='min' or name=='max')) then return 'score' end
    if center.key=='j_rocket' and name=='increase' then return 'cash' end
    return 'gentle'
end
local originals,original_blinds={},{}
local function clone(t) return type(t)=='table' and copy_table(t) or t end
local function randomize(t,path,center)
    for k,v in pairs(t) do
        local key=path..'.'..tostring(k)
        if not fixed[tostring(k):lower()] then
            if type(v)=='number' then t[k]=R.apply(key,v,kind_for(k,v,center),center.key)
            elseif type(v)=='table' and not v.is and not v.array then randomize(v,key,center) end
        end
    end
    if type(t.min)=='number' and type(t.max)=='number' and t.min>t.max then t.min,t.max=t.max,t.min end
end
function R.prototypes(seed)
    R.seed=tostring(seed or '')
    for key,center in pairs(G.P_CENTERS) do
        local set=center.set
        -- Deck/sleeve rules anchor the run, including its starting resources.
        if center.config and (set=='Joker' or set=='Tarot' or set=='Planet' or
           set=='Spectral' or set=='Voucher' or set=='Booster' or set=='Edition' or
           (center.consumeable and set~='Back' and set~='Sleeve')) then
            if not originals[key] then originals[key]=clone(center.config) end
            center.config=clone(originals[key])
            randomize(center.config,key,{key=key,set=set})
            if set=='Booster' and center.config.choose and center.config.extra then
                center.config.choose=math.min(center.config.choose,math.max(1,center.config.extra))
            end
            if center.config.min_highlighted and center.config.max_highlighted then
                center.config.min_highlighted=math.min(center.config.min_highlighted,center.config.max_highlighted)
            end
        end
    end
    for key,blind in pairs(G.P_BLINDS or {}) do
        if not original_blinds[key] then original_blinds[key]={mult=blind.mult,dollars=blind.dollars} end
        local original=original_blinds[key]
        blind.mult=original.mult -- Preserve Small < Big < Boss and modded blind rules.
        if original.dollars then
            blind.dollars=math.max(0,round(original.dollars*clamp(R.factor('blind.reward.'..key)^0.1,0.8,1.25)))
        end
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
    G.GAME.liminal_randomizer_policy=R.policy
    if not saved then
        G.GAME.seeded=not not explicit_seed
        -- Leave run budgets, level-one poker hands and the global luck numerator
        -- native. Planet growth can vary without making the opening unplayable.
        for name,hand in pairs(G.GAME.hands) do
            local f=clamp(R.factor('planet.'..name)^0.2,0.75,1.5)
            for _,key in ipairs({'l_chips','l_mult'}) do
                if type(hand[key])=='number' then hand[key]=hand[key]*f end
            end
        end
        local cost=G.GAME.base_reroll_cost
        G.GAME.base_reroll_cost=math.max(0,round(cost*clamp(R.factor('shop.reroll')^0.1,0.8,1.25)))
        G.GAME.round_resets.reroll_cost=G.GAME.base_reroll_cost
        G.GAME.current_round.reroll_cost=G.GAME.base_reroll_cost
    end
    return result
end
local cost=Card.set_cost
function Card:set_cost(...)
    local result=cost(self,...)
    if G.GAME and G.GAME.liminal_randomizer_seed and self.config and self.config.center and not self.playing_card then
        local key=self.config.center.key or self.ability.name
        -- Strong rolls cost modestly more; discounts/free cards/rentals still work.
        if self.cost>0 and not self.ability.rental then
            self.cost=math.max(1,round(self.cost*clamp(R.strength(key)^0.18,0.75,1.5)))
            self.sell_cost=math.max(1,math.floor(self.cost/2))+(self.ability.extra_value or 0)
            self.sell_cost_label=self.facing=='back' and '?' or self.sell_cost
        end
    end
    return result
end
local blind_amount=get_blind_amount
function get_blind_amount(ante)
    local original=blind_amount(ante)
    if G.GAME and G.GAME.liminal_randomizer_seed then
        local f=clamp(R.factor('blind.difficulty')^0.05,0.9,1.1)
        if type(original)=='number' then return math.max(1,round(original*f)) end
        return original*f -- Preserve Cryptid's big-number arithmetic.
    end
    return original
end
function R.literal(key,original)
    if R.seed=='' then return original end
    local field=key:match(':([^:]+)$') or 'mult_mod'
    local center=R.active_center or key
    local kind=kind_for(field,original,{key=center,set='Joker'})
    -- In an effect return table Xmult_mod is the final multiplier; the same
    -- name in a prototype can be a growth increment. Keep x1 neutral here too.
    if field:lower()=='xmult_mod' then kind='xmult' end
    return R.apply(key,original,kind,center)
end
-- This context also makes hardcoded scoring effects share their Joker's roll.
-- Native retrigger counts keep their original descriptions and avoid multiplying
-- several independent high rolls into an enormous animation chain.
local calculate=Card.calculate_joker
function Card:calculate_joker(context)
    local key=self.config and self.config.center and self.config.center.key
    local previous=R.active_center
    R.active_center=key
    local effect,post=calculate(self,context)
    R.active_center=previous
    return effect,post
end
