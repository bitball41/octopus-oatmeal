local M = {}
local pending, serial = nil, 0
local fs = love.filesystem
function M.request(e)
    local field = e.UIBox:get_UIE_by_ID('text_input')
    if not field then return end
    serial = serial + 1
    pending = {id = serial, field = field, overlay = G.OVERLAY_MENU}
    print('callJavascriptFunction window.OctopusClipboard.read(' .. serial .. ')')
end
function M.poll()
    if not fs.getInfo('octopus_clipboard.json') then return end
    local raw = fs.read('octopus_clipboard.json')
    fs.remove('octopus_clipboard.json')
    local ok, result = pcall(require('json').decode, raw or '')
    if not ok or not pending or result.id ~= pending.id then return end
    local request = pending; pending = nil
    if result.cancelled or request.overlay ~= G.OVERLAY_MENU then return end
    local seed = tostring(result.text or ''):gsub('%s+', ''):upper():sub(1, 8)
    if seed == '' then return end
    G.CONTROLLER.text_input_hook = request.field.children[1].children[1]
    G.CONTROLLER.text_input_id = 'text_input'
    for i = 1, 8 do G.FUNCS.text_input_key({key = 'right'}) end
    for i = 1, 8 do G.FUNCS.text_input_key({key = 'backspace'}) end
    for i = 1, #seed do G.FUNCS.text_input_key({key = seed:sub(i,i), browser_text = true}) end
    G.FUNCS.text_input_key({key = 'return'})
end
return M
