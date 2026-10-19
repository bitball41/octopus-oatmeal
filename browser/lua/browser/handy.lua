-- Browser scheduling for Handy. All sales go through the current modded
-- callback, including selling_self, selling_card, retriggers, and removal.
local M = {frame_budget = 0.004, event_limit = 128}
local now = love.timer.getTime

function M.install()
    if M.installed then return end
    M.installed = true
    Handy.browser = M

    -- Keep unsafe event reordering and uncapped speed out of this distribution.
    Handy.speed_multiplier.max_speed = 512
    Handy.speed_multiplier.is_uncapped = function() return false end
    Handy.animation_skip.can_dangerous = function() return false end

    local function in_run()
        return G and G.GAME and G.STAGE == G.STAGES.RUN
    end

    local function finish(no_save)
        local job = M.job
        if not job then return end
        for _, target in ipairs(job.queue) do
            if target.card then target.card.handy_dangerous_actions_used = nil end
            if target.tag then target.tag.handy_dangerous_actions_used = nil end
        end
        Handy.dangerous_actions.queues.game = {}
        G.CONTROLLER.locks.handy_bulk_sell = nil
        M.job, M.capture, M.co = nil, nil, nil
        Handy.UI.state_panel.display(function(state)
            if state.items.browser_bulk_sale then state.items.browser_bulk_sale.hold = false end
            return true
        end)
        if not no_save and in_run() and G.GAME == job.game then save_run() end
    end

    -- Snapshot selected targets in upstream order. Generated Jokers are never
    -- appended to the snapshot, and no live array is mutated by this traversal.
    Handy.dangerous_actions.process_game_queue = function()
        if M.job or not in_run() or G.SETTINGS.paused or G.OVERLAY_MENU then return end
        local queue = Handy.dangerous_actions.queues.game
        if #queue == 0 then return end
        M.job = {queue=queue, index=1, game=G.GAME, pending=0, done=0, total=#queue}
        G.CONTROLLER.locks.handy_bulk_sell = true
    end

    local process_card = Handy.dangerous_actions.process_card
    Handy.dangerous_actions.process_card = function(card, remove)
        if M.job or not Handy.dangerous_actions.can_process_card(card, remove) then return false end
        return process_card(card, remove)
    end

    -- Only events owned by the sale (and their descendants) are accelerated.
    -- Neither callbacks nor blocking/condition semantics are discarded.
    local add_event = EventManager.add_event
    function EventManager:add_event(event, queue, ...)
        local job = M.capture
        -- Handy executes cosmetic update_hand_text callbacks inline at its
        -- Everything level. Those never enter a queue and must not leave a
        -- phantom pending event; their children still inherit M.capture.
        local inline = job and Handy.animation_skip.is_skippable_queue(queue)
            and not event.handy_never_modify and (Handy.ARGS.extract_func_from_event or 0) > 0
            and event.trigger ~= 'ease'
        if job and not event.handy_web_job and not inline then
            event.handy_web_job = job
            job.pending = job.pending + 1
            if Handy.animation_skip.is_skippable_timer(event.timer) then
                event.delay = event.trigger == 'ease' and 0.0001 or 0
            end
        end
        return add_event(self, event, queue, ...)
    end

    local handle = Event.handle
    function Event:handle(results)
        if M.job and (M.events >= M.event_limit or now() >= M.deadline) then
            results.blocking, results.completed, results.time_done = true, false, false
            return
        end
        M.events = (M.events or 0) + 1
        local capture = M.capture
        if self.handy_web_job then M.capture = self.handy_web_job end
        handle(self, results)
        M.capture = capture
        if self.handy_web_job and not self.handy_web_finished and results.completed and results.time_done then
            self.handy_web_finished = true
            self.handy_web_job.pending = self.handy_web_job.pending - 1
        end
    end

    local clear_queue = EventManager.clear_queue
    function EventManager:clear_queue(...)
        local result = clear_queue(self, ...)
        if M.job then
            local pending = 0
            for _, queue in pairs(self.queues) do
                for _, event in ipairs(queue) do
                    if event.handy_web_job == M.job and not event.handy_web_finished then pending = pending + 1 end
                end
            end
            M.job.pending = pending
        end
        return result
    end

    -- Yield between evaluations, never omit one. Suspend Game.update while
    -- this coroutine owns SMODS's context stack so unrelated work cannot enter it.
    local function can_yield()
        -- Lua 5.1 cannot yield across a mod's pcall/C callback. Wait for the
        -- next unprotected evaluation instead of turning that into a crash.
        local depth = 2
        while true do
            local info = debug.getinfo(depth, 'S')
            if not info then return true end
            if info.what == 'C' then return false end
            depth = depth + 1
        end
    end
    local eval = eval_card
    function eval_card(...)
        if M.co and coroutine.running() == M.co and now() >= M.deadline and can_yield() then coroutine.yield() end
        return eval(...)
    end

    local function busy()
        if G.SCORING_COROUTINE or Handy.insta_actions.action_blocker then return true end
        if (G.GAME.STOP_USE or 0) > 0 then return true end
        for key, value in pairs(G.CONTROLLER.locks) do
            if key ~= 'handy_bulk_sell' and key ~= 'frame' and value then return true end
        end
        return false
    end

    local function resume_sale()
        M.capture = M.job
        local locked = G.CONTROLLER.locked
        G.CONTROLLER.locked = false -- Only bypass our own lock during this callback.
        local ok, err = coroutine.resume(M.co)
        G.CONTROLLER.locked = locked
        M.capture = nil
        if not ok then
            finish(true)
            error('Handy bulk sale failed: ' .. tostring(err))
        end
        if coroutine.status(M.co) == 'dead' then M.co = nil end
    end

    function M.update()
        local job = M.job
        if not job then return end
        if G.GAME ~= job.game or not in_run() then finish(); return end
        if M.co then resume_sale(); return end
        if job.pending > 0 or busy() or G.SETTINGS.paused or G.OVERLAY_MENU then return end
        if job.current then
            job.current.handy_dangerous_actions_used = nil
            job.current = nil
        end
        if job.cancel or job.index > job.total then finish(); return end
        local target = job.queue[job.index]
        job.index, job.done = job.index + 1, job.done + 1
        local card = target.card
        if target.remove then
            -- Upstream's separate Remove action remains opt-in, with no sell effects.
            if card and not card.REMOVED then card:stop_hover(); card:remove() end
            if target.tag and not target.tag.REMOVED then target.tag:remove() end
            return
        end
        if not card or card.REMOVED or card.cry_monopoly_destroyed or not card.area then return end
        job.current = card
        M.co = coroutine.create(function()
            -- Revalidate at execution time: an earlier sale may change eternal
            -- status, permissions, prices, or even remove another selected card.
            if card:can_sell_card() then
                G.FUNCS.sell_card({config={ref_table=card}})
            end
        end)
        resume_sale()
    end

    local update = love.update
    function love.update(dt, ...)
        M.events, M.deadline = 0, now() + M.frame_budget
        M.notify()
        M.update()
        if not M.co then return update(dt, ...) end
        Handy.UI.state_panel.update(dt)
    end

    local keypressed = love.keypressed
    function love.keypressed(key, ...)
        if M.job then
            if key == 'escape' then M.job.cancel = true end
            return
        end
        return keypressed(key, ...)
    end
    for _, name in ipairs({'mousepressed', 'wheelmoved', 'gamepadpressed', 'touchpressed'}) do
        local callback = love[name]
        if callback then love[name] = function(...)
            if not M.job then return callback(...) end
        end end
    end

    -- Progress lives in Handy's existing notification panel, with no extra HUD.
    function M.notify()
        if not M.job then return end
        if M.job.notified == M.job.done then return end
        M.job.notified = M.job.done
        Handy.UI.state_panel.display(function(state)
            state.items.browser_bulk_sale = {
                text='Selling ' .. M.job.done .. '/' .. M.job.total .. ' (Esc to stop)',
                hold=true, order=1,
            }
            return true
        end)
    end

    local save = save_run
    function save_run(...)
        -- Never serialize a half-completed sell/context; persist at the boundary.
        if M.job then return end
        return save(...)
    end

    -- Prevent runaway sound/pop-up queues during a bulk operation. The normal
    -- status-text callback still executes (it may carry gameplay side effects).
    for _, name in ipairs({'attention_text', 'play_sound', 'juice_card', 'delay'}) do
        local callback = _G[name]
        _G[name] = function(...)
            if not M.job then return callback(...) end
        end
    end
    local juice = Moveable.juice_up
    function Moveable:juice_up(...)
        if not M.job then return juice(self, ...) end
    end
    return M
end

return M
