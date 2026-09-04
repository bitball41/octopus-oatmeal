local MP = {
  connected = false,
  opponent_score = 0,
  scores = {},
  last_on_blind = {},
  round_cleared_at = nil,
  inbox_timer = 0,
  started_remotely = false,
}

local b64chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

local function b64encode(data)
  return ((data:gsub('.', function(x)
    local r, byte = '', x:byte()
    for i = 8, 1, -1 do
      r = r .. (byte % 2^i - byte % 2^(i - 1) > 0 and '1' or '0')
    end
    return r
  end) .. '0000'):gsub('%d%d%d?%d?%d?%d?', function(x)
    if #x < 6 then return '' end
    local c = 0
    for i = 1, 6 do
      c = c + (x:sub(i, i) == '1' and 2^(6 - i) or 0)
    end
    return b64chars:sub(c + 1, c + 1)
  end) .. ({ '', '==', '=' })[#data % 3 + 1])
end

local function b64decode(data)
  data = data:gsub('[^' .. b64chars .. '=]', '')
  return (data:gsub('.', function(x)
    if x == '=' then return '' end
    local r, f = '', b64chars:find(x) - 1
    for i = 6, 1, -1 do
      r = r .. (f % 2^i - f % 2^(i - 1) > 0 and '1' or '0')
    end
    return r
  end):gsub('%d%d%d?%d?%d?%d?%d?%d?', function(x)
    if #x ~= 8 then return '' end
    local c = 0
    for i = 1, 8 do
      c = c + (x:sub(i, i) == '1' and 2^(8 - i) or 0)
    end
    return string.char(c)
  end))
end

local function js_call(method, fields)
  local encoded = {}
  for _, value in ipairs(fields or {}) do
    encoded[#encoded + 1] = b64encode(tostring(value or ''))
  end
  local packet = table.concat(encoded, '.')
  print("callJavascriptFunction window.OctopusMultiplayer." .. method .. "('" .. packet .. "')")
end

local function blind_index()
  if not G or not G.GAME then return '0' end
  return tostring((G.GAME.round or 0) + (G.GAME.skips or 0))
end

local function show_message(message)
  if attention_text and G and G.ROOM_ATTACH then
    attention_text({
      text = message,
      scale = 0.5,
      hold = 2.2,
      align = 'cm',
      offset = {x = 0, y = -2.7},
      major = G.ROOM_ATTACH,
    })
  else
    print('[Octopus MP] ' .. message)
  end
end

local function grant_reward(kind, value)
  if kind == 'money' then
    if ease_dollars then ease_dollars(tonumber(value) or 5, false) end
    return
  end

  if kind == 'joker' and G and G.jokers and create_card then
    if #G.jokers.cards >= G.jokers.config.card_limit then return end
    G.GAME.joker_buffer = (G.GAME.joker_buffer or 0) + 1
    G.E_MANAGER:add_event(Event({func = function()
      local card = create_card('Joker', G.jokers, nil, nil, nil, nil, nil, 'octomp')
      if card then
        if card.set_perishable then card:set_perishable(true) end
        card:add_to_deck()
        G.jokers:emplace(card)
        card:start_materialize()
      end
      G.GAME.joker_buffer = math.max(0, (G.GAME.joker_buffer or 1) - 1)
      return true
    end}))
    return
  end

  if kind == 'consumable' and G and G.consumeables and create_card then
    if #G.consumeables.cards >= G.consumeables.config.card_limit then return end
    G.GAME.consumeable_buffer = (G.GAME.consumeable_buffer or 0) + 1
    G.E_MANAGER:add_event(Event({func = function()
      local card = create_card('Tarot', G.consumeables, nil, nil, nil, nil, nil, 'octomp')
      if card then
        card:add_to_deck()
        G.consumeables:emplace(card)
        card:start_materialize()
      end
      G.GAME.consumeable_buffer = math.max(0, (G.GAME.consumeable_buffer or 1) - 1)
      return true
    end}))
  end
end

local function handle_packet(parts)
  local kind = parts[1]
  if kind == 'mp_connected' then
    MP.connected = true
    MP.scores = {}
    MP.last_on_blind = {}
    show_message('Multiplayer connected')
    return
  end

  if kind == 'mp_disconnected' then
    MP.connected = false
    MP.opponent_score = 0
    show_message('Multiplayer disconnected')
    return
  end

  if kind == 'opponent_score' then
    local blind = tostring(parts[2] or '0')
    local score = tonumber(parts[3]) or 0
    MP.scores[blind] = math.max(MP.scores[blind] or 0, score)
    MP.opponent_score = score
    return
  end

  if kind == 'start_game' then
    if not G or not G.FUNCS or not G.FUNCS.start_run then return end
    local seed = parts[2]
    local stake = tonumber(parts[3]) or 1
    local deck = parts[4]
    if deck and get_deck_from_name then
      local back = get_deck_from_name(deck)
      if back then
        G.GAME.viewed_back = back
        G.GAME.selected_back = back
      end
    end
    MP.started_remotely = true
    G.FUNCS.start_run(nil, {stake = stake, seed = seed, challenge = nil})
    if G.GAME then G.GAME.seeded = false end
    MP.scores = {}
    show_message('Synced multiplayer run started')
    return
  end

  if kind == 'award' then
    local blind = parts[2] or '?'
    local won = parts[3] == '1'
    local reward = parts[4] or 'none'
    local value = parts[5]
    if won then
      grant_reward(reward, value)
      if reward == 'money' then
        show_message('Won blind ' .. blind .. '  +$' .. tostring(value))
      elseif reward == 'joker' then
        show_message('Won blind ' .. blind .. '  +Perishable Joker')
      elseif reward == 'consumable' then
        show_message('Won blind ' .. blind .. '  +Consumable')
      else
        show_message('Blind ' .. blind .. ' tied')
      end
    else
      if reward == 'none' then
        show_message('Blind ' .. blind .. ' tied')
      else
        show_message('Opponent won blind ' .. blind)
      end
    end
  end
end

local function poll_inbox()
  local items = love.filesystem.getDirectoryItems('') or {}
  table.sort(items)
  for _, filename in ipairs(items) do
    if filename:match('^octopus_mp_inbox_.*%.txt$') then
      local raw = love.filesystem.read(filename)
      if raw and raw ~= '' then
        local parts = {}
        for part in raw:gmatch('[^.]+') do
          parts[#parts + 1] = b64decode(part)
        end
        if #parts > 0 then
          local ok, err = pcall(handle_packet, parts)
          if not ok then print('[Octopus MP] packet error: ' .. tostring(err)) end
        end
      end
      love.filesystem.remove(filename)
    end
  end
end

function MP.init()
  local save_dir = love.filesystem.getSaveDirectory()
  if save_dir then
    js_call('setSaveDirectoryEncoded', {save_dir})
  end
end

function MP.update(dt)
  MP.inbox_timer = MP.inbox_timer + (dt or 0)
  if MP.inbox_timer >= 0.10 then
    MP.inbox_timer = 0
    poll_inbox()
  end

  if MP.connected and G and G.GAME then
    MP.opponent_score = MP.scores[blind_index()] or MP.opponent_score or 0
  end
end

function MP.on_hand_scored(hand_score)
  if not MP.connected or not G or not G.GAME then return end
  local score = (G.GAME.chips or 0) + (tonumber(hand_score) or 0)
  js_call('fromLuaEncoded', {'score', blind_index(), tostring(score)})
end

function MP.on_run_start()
  if not MP.connected or MP.started_remotely or not G or not G.GAME then
    MP.started_remotely = false
    return
  end
  local deck = G.GAME.selected_back and G.GAME.selected_back.name or ''
  local seed = G.GAME.pseudorandom and G.GAME.pseudorandom.seed or ''
  js_call('fromLuaEncoded', {'start_game', seed, tostring(G.GAME.stake or 1), deck})
  MP.scores = {}
end

function MP.on_round_end(game_over)
  if not MP.connected or not G or not G.GAME then return end
  local blind = blind_index()
  js_call('fromLuaEncoded', {
    'round_end',
    blind,
    tostring(G.GAME.chips or 0),
    game_over and '1' or '0',
  })
  MP.started_remotely = false
end

function MP.should_end_round()
  local normal_end = G.GAME.chips - G.GAME.blind.chips >= 0 or G.GAME.current_round.hands_left < 1
  if not MP.connected then return normal_end end

  if MP.round_cleared_at == nil and G.GAME.chips - G.GAME.blind.chips >= 0 then
    MP.round_cleared_at = G.GAME.current_round.hands_left
  end

  if G.GAME.current_round.hands_left < 1 then
    if G.GAME.chips - G.GAME.blind.chips >= 0 and MP.round_cleared_at ~= nil then
      G.GAME.current_round.hands_left = MP.round_cleared_at
      MP.round_cleared_at = nil
    end
    return true
  end
  return false
end

_G.OCTOPUS_MP = MP
return MP
