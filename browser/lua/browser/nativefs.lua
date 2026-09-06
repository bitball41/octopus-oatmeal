-- NativeFS-compatible access to the bundled Mods tree and LÖVE save directory.
local fs = love.filesystem
local working = ''
local M = {}
local sub, gsub, gmatch, match = string.sub, string.gsub, string.gmatch, string.match
local function path(value)
    value = gsub(tostring(value or ''), '\\', '/')
    local save = gsub(fs.getSaveDirectory(), '\\', '/')
    if value == save or sub(value, 1, #save+1) == save .. '/' then value = gsub(sub(value, #save+1), '^/', '')
    elseif sub(value, 1, 5) ~= 'Mods/' and value ~= 'Mods' and sub(value,1,1) ~= '/' and working ~= '' then
        value = working .. '/' .. value
    end
    local parts = {}
    for part in gmatch(value, '[^/]+') do
        if part == '..' then assert(#parts > 0, 'Path outside virtual filesystem'); table.remove(parts)
        elseif part ~= '.' then parts[#parts+1] = part end
    end
    return table.concat(parts, '/')
end
function M.setWorkingDirectory(value) working = path(value); return true end
function M.getWorkingDirectory() return working end
function M.getInfo(value) return fs.getInfo(path(value)) end
function M.read(containerOrName, nameOrSize, sizeOrNil)
    local typed = type(nameOrSize) == 'string' and nameOrSize ~= 'all'
    local filename = path(typed and nameOrSize or containerOrName)
    if nameOrSize == 'all' then nameOrSize = nil end
    if sizeOrNil == 'all' then sizeOrNil = nil end
    -- Config files are optional on first boot. Match NativeFS's nil/error
    -- contract instead of entering the Web runtime's missing-file error path.
    local info = fs.getInfo(filename)
    if not info or info.type ~= 'file' then return nil, 'File not found: ' .. filename end
    local ok, data, size
    if typed then ok, data, size = pcall(fs.read, containerOrName, filename, sizeOrNil)
    else ok, data, size = pcall(fs.read, filename, nameOrSize) end
    if not ok then return nil, tostring(data) end
    return data, size
end
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
    return gmatch(data .. '\n', '([^\n]*)\n')
end
function M.newFileData(value) return fs.newFileData(assert(M.read(value)), match(value, '[^/]+$')) end
function M.newFile(value, mode) return fs.newFile(path(value), mode) end
function M.getSaveDirectory() return fs.getSaveDirectory() end
return M
