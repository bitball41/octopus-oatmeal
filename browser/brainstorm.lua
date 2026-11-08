-- Brainstorm Rerolled for the browser builds (required at the end of
-- main.lua by the launcher, which also packs brainstorm_rerolled/*.lua and
-- starts the WebAssembly search engine, brainstorm/host.js).
--
-- Upstream's Lovely manifest appends Core/Brainstorm.lua to main.lua and
-- calls Brainstorm.init() once the profile has loaded; this does the same.
if Brainstorm and Brainstorm.PATH then return Brainstorm end
assert(love.filesystem.load('brainstorm_rerolled/core.lua'))()

local start_up_ref = Game.start_up
function Game:start_up(...)
    local result = start_up_ref(self, ...)
    local ok, err = pcall(Brainstorm.init)
    if not ok then print('[Brainstorm-Rerolled] could not start: ' .. tostring(err)) end
    return result
end

return Brainstorm
