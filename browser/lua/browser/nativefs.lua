-- NativeFS-compatible access to the bundled Mods tree and LÖVE save directory.
local fs = love.filesystem
local working = ''
local M = {}
local function path(value)
    value = tostring(value or ''):gsub('\\', '/')
    local save = fs.getSaveDirectory():gsub('\\', '/')
    if value:sub(1, #save) == save then value = value:sub(#save+1):gsub('^/', '')
    elseif value:sub(1, 5) ~= 'Mods/' and value ~= 'Mods' and value:sub(1,1) ~= '/' and working ~= '' then
        value = working .. '/' .. value
    end
    local parts = {}
    for part in value:gmatch('[^/]+') do
        if part == '..' then assert(#parts > 0, 'Path outside virtual filesystem'); table.remove(parts)
        elseif part ~= '.' then parts[#parts+1] = part end
    end
    return table.concat(parts, '/')
end
function M.setWorkingDirectory(value) working = path(value); return true end
function M.getWorkingDirectory() return working end
function M.getInfo(value) return fs.getInfo(path(value)) end
function M.read(value) return fs.read(path(value)) end
function M.write(value, data) return fs.write(path(value), data) end
function M.append(value, data) return fs.append(path(value), data) end
function M.remove(value) return fs.remove(path(value)) end
function M.createDirectory(value) return fs.createDirectory(path(value)) end
function M.getDirectoryItems(value) local t=fs.getDirectoryItems(path(value)); table.sort(t); return t end
function M.getDirectoryItemsInfo(value)
    local result = {}
    for _, name in ipairs(M.getDirectoryItems(value)) do
        local info = M.getInfo(value .. '/' .. name)
        if info then info.name = name; result[#result+1] = info end
    end
    return result
end
function M.lines(value)
    local data = assert(M.read(value))
    return (data .. '\n'):gmatch('([^\n]*)\n')
end
function M.newFileData(value) return fs.newFileData(assert(M.read(value)), value:match('[^/]+$')) end
function M.newFile(value, mode) return fs.newFile(path(value), mode) end
function M.getSaveDirectory() return fs.getSaveDirectory() end
return M
