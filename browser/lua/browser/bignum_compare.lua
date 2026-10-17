-- Only Cryptid loads these helpers. Lua 5.1 rejects mixed-type comparison
-- before checking metamethods; LuaJIT's cdata behavior has to be explicit.
-- Capture native type before Amulet's optional type adapter.
local type = type
local function big_pair(a, b, aa, bb)
    if not Big then return false end
    return (aa == 'table' and Big.is(a) and (bb == 'number' or (bb == 'table' and Big.is(b))))
        or (aa == 'number' and bb == 'table' and Big.is(b))
end
function __octopus_lt(a, b)
    local aa, bb = type(a), type(b)
    if (aa == 'table' or bb == 'table') and big_pair(a, b, aa, bb) then return Big.compareTo(a, b) < 0 end
    return a < b
end
function __octopus_le(a, b)
    local aa, bb = type(a), type(b)
    if (aa == 'table' or bb == 'table') and big_pair(a, b, aa, bb) then return Big.compareTo(a, b) <= 0 end
    return a <= b
end
function __octopus_gt(a, b)
    local aa, bb = type(a), type(b)
    if (aa == 'table' or bb == 'table') and big_pair(a, b, aa, bb) then return Big.compareTo(a, b) > 0 end
    return a > b
end
function __octopus_ge(a, b)
    local aa, bb = type(a), type(b)
    if (aa == 'table' or bb == 'table') and big_pair(a, b, aa, bb) then return Big.compareTo(a, b) >= 0 end
    return a >= b
end
function __octopus_eq(a, b)
    local aa, bb = type(a), type(b)
    if (aa == 'table' or bb == 'table') and big_pair(a, b, aa, bb) then return Big.compareTo(a, b) == 0 end
    return a == b
end
function __octopus_ne(a, b)
    local aa, bb = type(a), type(b)
    if (aa == 'table' or bb == 'table') and big_pair(a, b, aa, bb) then return Big.compareTo(a, b) ~= 0 end
    return a ~= b
end
return true
