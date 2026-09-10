-- Lua 5.1 implementation of LuaJIT's seeded Tausworthe generator.
-- Algorithm reference: LuaJIT src/lib_math.c and src/lj_prng.c (MIT).
-- Use pairs of 32-bit words so no 64-bit integer precision is lost.
local M = {}
local floor, abs = math.floor, math.abs
local TWO32 = 4294967296
local xor4 = {}
for a = 0, 15 do
    xor4[a] = {}
    for b = 0, 15 do
        local x, y, v, p = a, b, 0, 1
        for _ = 1, 4 do
            if x % 2 ~= y % 2 then v = v + p end
            x, y, p = floor(x / 2), floor(y / 2), p * 2
        end
        xor4[a][b] = v
    end
end
local function xor(a, b)
    local v, p = 0, 1
    for _ = 1, 8 do
        v = v + xor4[a % 16][b % 16] * p
        a, b, p = floor(a / 16), floor(b / 16), p * 16
    end
    return v
end
local function left(h, l, n)
    if n >= 32 then return (l % 2^(64-n)) * 2^(n-32), 0 end
    return (h % 2^(32-n)) * 2^n + floor(l / 2^(32-n)), (l % 2^(32-n)) * 2^n
end
local function right(h, l, n)
    if n >= 32 then return 0, floor(h / 2^(n-32)) end
    return floor(h / 2^n), floor(l / 2^n) + (h % 2^n) * 2^(32-n)
end
local state = {}
local params = {{63,31,18},{58,19,28},{55,24,7},{47,21,8}}
local function step()
    local rh, rl = 0, 0
    for i = 1, 4 do
        local h, l = state[i][1], state[i][2]
        local k, q, s = unpack(params[i])
        local ah, al = left(h, l, q)
        ah, al = right(xor(ah, h), xor(al, l), k-s)
        local bh, bl = left(h, l - l % 2^(64-k), s)
        h, l = xor(ah, bh), xor(al, bl)
        state[i][1], state[i][2] = h, l
        rh, rl = xor(rh, h), xor(rl, l)
    end
    return rh, rl
end
local function words(d)
    -- Preserve the NaN sign: math.abs in pseudoseed produces positive NaN.
    if d ~= d then
        local negative = string.format("%f", d):sub(1, 1) == "-"
        return negative and 4294443008 or 2146959360, 0
    end
    local sign = d < 0 and 2147483648 or 0
    d = abs(d)
    if d == math.huge then return sign + 2146435072, 0 end
    if d == 0 then return sign, 0 end
    local fraction, exponent = math.frexp(d)
    local mantissa = (fraction * 2 - 1) * 4503599627370496
    if exponent < -1021 then
        mantissa, exponent = d / 2^-1074, -1022
    end
    return sign + (exponent + 1022) * 1048576 + floor(mantissa / TWO32), mantissa % TWO32
end
function M.randomseed(d)
    d = assert(tonumber(d), 'number expected')
    for i = 1, 4 do
        d = d * math.pi + 2.7182818284590452354
        local h, l = words(d)
        local minimum = 2^(64-params[i][1])
        if h == 0 and l < minimum then l = l + minimum end
        state[i] = {h, l}
    end
    for _ = 1, 10 do step() end
end
function M.random(a, b)
    local h, l = step()
    local d = ((h % 1048576) * TWO32 + l) / 4503599627370496
    if b ~= nil then return floor(d * (b-a+1)) + a end
    if a ~= nil then return floor(d * a) + 1 end
    return d
end
M.randomseed(0)
return M
