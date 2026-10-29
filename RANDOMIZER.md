# Randomizer design

This is a seeded Balatro variant for players who want to adapt to strange Joker builds while still making normal shop and hand decisions. Its priorities are surprising card opportunities, readable effects, and runs that remain playable before finding a good Joker. It adds no content or in-game configuration. Multiplayer peers use identical rolls.

The earlier design had three problems. A uniform 0.1×–10× roll averaged 5.05×, so it mostly buffed values. Applying that range separately to starting limits, prices, blind bases and blind multipliers let setup rolls decide the run. Independently rolling related fields also changed what a card meant: an unbuilt ×1 scaler could begin with a huge multiplier, or a decaying card could lose its intended lifetime.

## Rules

| System | Rule | Purpose |
| --- | --- | --- |
| Joker chips, additive Mult and gains | 0.1×–10× by default, with a triangular distribution in log space centered at 1× | Half buff, half nerf; most rolls modest; exceptional finds remain possible. |
| Related Joker scoring fields | One factor per Joker per run | Scholar's chips and Mult stay related; Ice Cream's chips and decay preserve its lifetime. |
| XMult | Scale the bonus above ×1; preserve initial ×1 | A growing Joker must still earn its multiplier. |
| Starting run budgets | Native deck/sleeve rules | Preserve hand count, discards, hand size, slots, starting cards and money. |
| Starting poker hands | Native chips and Mult | A weak shop cannot erase the basic way to score. |
| Planet growth | A modest 0.75×–1.5× variation | Give runs a different direction without flattening hand progression. |
| Blind requirements | One run-wide 0.9×–1.1× factor on the original ante curve; preserve blind multipliers | No tiny late-ante targets or independently multiplied difficulty spikes. |
| Shop prices | Original computed price × a factor between 0.75× and 1.5×, linked to Joker strength | Strong rolls can cost a little more; respect coupons, discounts and rentals. |
| Economy effects | Roughly 0.5×–2×, rounded to currency units | Preserve sources and sinks instead of creating automatic infinite purchasing power. |
| Odds | Small changes around original odds; ordinary denominators remain at least 2 | Keep chance effects recognizable and global luck unchanged. |
| Configurable action counts | Small changes, whole numbers, bounded around the original | Avoid dozens of generated cards or giant retrigger chains. |
| Native hardcoded actions and retriggers | Original counts | Preserve their descriptions and scoring cadence; other card values still change. |
| Targeting requirements and identity data | Original values | Death still requires its expected targets; ranks, suits and asset coordinates stay valid. |
| Unknown mod fields and editions | Gentle variation | Avoid treating an opaque counter as a scoring multiplier. |
| Playing-card enhancements | Original values | Honor the exclusion requested for the mod. |

The launcher bounds control the wide **scoring** rolls. Economy, counts and progression deliberately use the rules above. A fixed 1× reproduces original values. A fixed 10× gives Blue Joker +20 chips per card, while keeping the run's five base Joker slots.

Fractions are valid for scoring; actual counts are whole numbers. Zero counters remain zero. Each Joker's roll is revealed by its existing description and stays fixed for that seed, including future copies. Rolls do not consume gameplay RNG or reroll on purchase. Save and multiplayer identities include `designed-v3`, separating previous randomizer rules.

## Validation and remaining tuning

The automated suite checks 500 seeded setups, distribution across 10,000 seeds, native run budgets, affordable price bands, ante progression, coherent scoring/decay, pack and targeting validity, preserved enhancement/starting-money exclusions, neutral scaler states, save continuation, and matching multiplayer peers. Default distribution targets are approximately 50% below 1× and fewer than 7% above 5×. These validate the rules; they do not prove enjoyment.

Browser checks cover actual WASM startup, a seeded run, Joker creation/descriptions and the Multiplayer + Cryptid combination. Further playtesting should ask whether a weak opening still leaves meaningful purchases, whether players can recognize a strong roll from the card, and whether late-ante choices remain interesting. The numerical bands are tuning choices, not a claim of exhaustive balance across every mod combination.
