-- Keep consumables when a shared Handy/Overflow run is opened in plain Vanilla.
-- Overflow stores a stack as one card plus overflow_amount; Vanilla needs each card.
local load_area = CardArea.load
function CardArea:load(saved)
    local total = 0
    local has_stack = false
    for _, card in ipairs(saved.cards or {}) do
        local qty = card.overflow_amount or 1
        if card.overflow_infinite or type(qty) ~= 'number' or qty ~= qty or qty == math.huge or qty < 1 then
            error('Open this run in Vanilla + Handy to retain its Overflow consumables.')
        end
        total = total + math.floor(qty)
        has_stack = has_stack or qty > 1
    end
    if not has_stack then return load_area(self, saved) end
    if total > 10000 then
        error('This run has too many stacked consumables for plain Vanilla. Open Vanilla + Handy to continue.')
    end
    local expanded = {config = saved.config, cards = {}}
    for _, card in ipairs(saved.cards) do
        for i = 1, math.floor(card.overflow_amount or 1) do
            local item = copy_table(card)
            item.overflow_amount = nil
            item.overflow_infinite = nil
            item.highlighted = false
            expanded.cards[#expanded.cards+1] = item
        end
    end
    return load_area(self, expanded)
end
