--[[
  native.lua (browser) — Brainstorm Rerolled's searcher, reached through the
  page instead of LuaJIT's FFI.

  Upstream loads Immolate.dll/.dylib with LuaJIT's FFI and searches on
  native threads. The browser game is plain Lua 5.1 in WebAssembly, so the
  page runs Immolate compiled to WebAssembly in Web Workers instead
  (brainstorm/host.js, brainstorm/immolate.wasm). This file offers the same
  native.load/start/poll/cancel/free/check_seed calls as upstream's
  Core/native.lua, so the rest of the mod is unchanged.

  How a call works: print("callJavascriptFunction ...") is run by the page
  immediately (index.html evaluates it inside the print call), and the page
  answers before print returns by writing a Lua table to brainstorm_reply.lua
  in the save folder, which is read and deleted here.
]]

local native = {}

-- Must match BS_API_VERSION in Immolate's brainstorm_api.h.
native.API_VERSION = 2

native.lib = nil

local REPLY = "brainstorm_reply.lua"

-- Plain values and tables as JSON, which the page reads as a JS literal.
local function encode(value)
  local kind = type(value)
  if kind == "string" then
    return '"' .. value:gsub('[%c"\\]', function(c)
      if c == "\n" then
        return "\\n"
      end
      return string.format("\\u%04x", c:byte())
    end) .. '"'
  elseif kind == "number" then
    return value == value and value ~= math.huge and value ~= -math.huge and string.format("%.17g", value) or "0"
  elseif kind == "boolean" then
    return tostring(value)
  elseif kind == "table" then
    local parts = {}
    for k, v in pairs(value) do
      if type(k) == "string" then
        parts[#parts + 1] = encode(k) .. ":" .. encode(v)
      end
    end
    return "{" .. table.concat(parts, ",") .. "}"
  end
  return "null"
end
native.encode = encode

local function call(request)
  if love.filesystem.getInfo(REPLY) then
    love.filesystem.remove(REPLY)
  end
  print(
    "callJavascriptFunction window.OctopusBrainstorm&&window.OctopusBrainstorm.call("
      .. encode(love.filesystem.getSaveDirectory())
      .. ","
      .. encode(request)
      .. ")"
  )
  if not love.filesystem.getInfo(REPLY) then
    return nil
  end
  local text = love.filesystem.read(REPLY)
  love.filesystem.remove(REPLY)
  local chunk = text and loadstring(text)
  if not chunk then
    return nil
  end
  setfenv(chunk, {})
  local ok, reply = pcall(chunk)
  return ok and type(reply) == "table" and reply or nil
end

-- Returns true, or false and an error message. Safe to call more than once.
function native.load()
  if native.lib then
    return true
  end
  local reply = call({ op = "info" })
  if not reply then
    return false, "the seed search engine did not load; reload the page"
  end
  if reply.error then
    return false, tostring(reply.error)
  end
  if reply.api_version ~= native.API_VERSION then
    return false, string.format("the search engine has API version %s but the mod expects %d", tostring(reply.api_version), native.API_VERSION)
  end
  native.lib = true
  native.info = reply.info
  return true
end

function native.build_info()
  return native.info or "not loaded"
end

-- Starts a background search. Returns a job handle, or nil and an error.
function native.start(opts)
  local reply = call({ op = "start", options = opts })
  if not reply then
    return nil, "the seed search engine is not available"
  end
  if not reply.job then
    return nil, tostring(reply.error)
  end
  return { id = reply.job }
end

-- Returns status ("running", "found", "exhausted", "cancelled", "error"),
-- the seed string (only when "found"), the number of seeds checked, and,
-- for "error", why (browser: upstream only reports the status).
-- A single missing answer from the page is not an error: the search keeps
-- running there, so it is asked again next frame.
function native.poll(job)
  local reply = call({ op = "poll", job = job.id })
  if not reply then
    job.misses = (job.misses or 0) + 1
    if job.misses < 120 then
      return "running", nil, job.checked or 0
    end
    return "error", nil, job.checked or 0, "the page stopped answering"
  end
  job.misses = 0
  job.checked = reply.checked or job.checked
  local status = reply.status or "error"
  return status, reply.seed, reply.checked or 0, reply.error
end

function native.cancel(job)
  call({ op = "cancel", job = job.id })
end

-- Stops the search and releases it. Do not use `job` afterwards.
function native.free(job)
  call({ op = "free", job = job.id })
end

-- Checks one seed without starting a search. Returns true/false, or nil and
-- an error message.
function native.check_seed(opts, seed)
  local reply = call({ op = "check", options = opts, seed = seed })
  if not reply then
    return nil, "the seed search engine is not available"
  end
  if reply.error then
    return nil, tostring(reply.error)
  end
  return reply.match == true
end

return native
