-- Browser platform services for the pinned Steamodded and Multiplayer sources.
-- No match rules live here: MP's existing client and server own those.
require('browser.format').install()
local fs = love.filesystem
local nativefs = require 'browser.nativefs'
package.loaded.nativefs = nativefs
package.loaded['SMODS.nativefs'] = nativefs
_G.load = loadstring or load

local variables = {}
package.loaded.lovely = {
    version = '0.9.0', mod_dir = 'Mods', log_path = 'browser.log',
    set_var = function(k, v) variables[k] = v end,
    remove_var = function(k) local v = variables[k]; variables[k] = nil; return v end,
    apply_patches = function(_, source) return source end, -- applied offline, exactly once
    reload_patches = function() return false, 'Browser patches require rebuilding game.data' end,
}

-- Steamodded's optional local debug socket has no browser endpoint.
package.loaded.socket = {tcp = function()
    return {settimeout = function() end, connect = function() return nil, 'Debug socket unavailable on Web' end}
end}

local thread = love.thread
local channels = {}
for _, name in ipairs({'uiToNetwork', 'networkToUi'}) do
    local queue = {}
    channels[name] = {
        push = function(_, message)
            if name == 'uiToNetwork' then
                local json = require 'json'
                print('callJavascriptFunction window.OctopusMP.send(' .. json.encode(message) .. ')')
            else queue[#queue+1] = message end
        end,
        pop = function() return table.remove(queue, 1) end,
        getCount = function() return #queue end,
        clear = function() for i = #queue, 1, -1 do queue[i] = nil end end,
    }
end
local get_channel = thread.getChannel
thread.getChannel = function(name) return channels[name] or get_channel(name) end

local M = {}
function M.connect()
    local json = require 'json'
    print('callJavascriptFunction window.OctopusMP.attach(' .. json.encode(fs.getSaveDirectory()) .. ')')
end
function M.poll()
    local names = fs.getDirectoryItems('')
    table.sort(names)
    for _, name in ipairs(names) do
        if name:match('^octopus_upstream_%d+%.json$') then
            local packet = fs.read(name)
            fs.remove(name)
            if packet then channels.networkToUi:push(packet) end
        end
    end
end
return M
