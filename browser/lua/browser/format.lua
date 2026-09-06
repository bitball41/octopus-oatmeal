-- LuaJIT permits tostring conversion for non-string %s arguments; Lua 5.1
-- does not. Upstream uses that behavior in diagnostics and optional lookups.
local M = {}
local native_format = string.format
local find, sub = string.find, string.sub
local select, unpack, tostring, type = select, unpack, tostring, type

function M.format(pattern, ...)
    if type(pattern) ~= 'string' then return native_format(pattern, ...) end
    local count, args = select('#', ...), {...}
    local position, argument = 1, 0
    while true do
        local percent = find(pattern, '%', position, true)
        if not percent then break end
        if sub(pattern, percent+1, percent+1) == '%' then
            position = percent+2 -- escaped percent does not consume an argument
        else
            local first, last, specifier = find(pattern, '%%[-+ #0]*%d*%.?%d*([cdiouxXeEfgGqs])', percent)
            if first ~= percent then break end -- native formatter reports invalid formats
            argument = argument+1
            if specifier == 's' and argument <= count then
                local kind = type(args[argument])
                if kind ~= 'string' and kind ~= 'number' then args[argument] = tostring(args[argument]) end
            end
            position = last+1
        end
    end
    -- Explicit length preserves trailing nil and missing-argument errors.
    return native_format(pattern, unpack(args, 1, count))
end

function M.install() string.format = M.format end
return M
