-- Only Cryptid loads these helpers. Lua 5.1 rejects mixed-type comparison
-- before checking metamethods; LuaJIT's cdata behavior has to be explicit.
local function big_pair(a, b)
    if not Big then return false end
    local aa, bb = Big.is(a), Big.is(b)
    return (aa and (bb or type(b) == 'number')) or (bb and type(a) == 'number')
end
function __octopus_lt(a, b)
    if big_pair(a, b) then return Big.compareTo(a, b) < 0 end
    return a < b
end
function __octopus_le(a, b)
    if big_pair(a, b) then return Big.compareTo(a, b) <= 0 end
    return a <= b
end
function __octopus_gt(a, b)
    if big_pair(a, b) then return Big.compareTo(a, b) > 0 end
    return a > b
end
function __octopus_ge(a, b)
    if big_pair(a, b) then return Big.compareTo(a, b) >= 0 end
    return a >= b
end
function __octopus_eq(a, b)
    if big_pair(a, b) then return Big.compareTo(a, b) == 0 end
    return a == b
end
function __octopus_ne(a, b) return not __octopus_eq(a, b) end
return true
