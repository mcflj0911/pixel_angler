# Tackle parts. The setup menu picks one part for each slot, and the stats of those parts
# change how casting, hooksets, the fight and the retrieve feel.
SLOTS = ["rod", "reel", "line", "hook", "scope"]
SLOT_NAMES = {"rod": "Rod", "reel": "Reel", "line": "Line", "hook": "Hooks", "scope": "Scope"}

PARTS = [
    # Rod: rating is the weight it can handle before it strains, power boosts the fight, length adds casting reach
    {"key": "rod_basic", "slot": "rod", "name": "Basic Rod", "price": 0, "rating": 2, "power": 1.0, "reach": 0,
     "desc": "A starter rod. Strains on big fish"},
    {"key": "rod_graphite", "slot": "rod", "name": "Graphite Rod", "price": 180, "rating": 4, "power": 1.15, "reach": 25,
     "desc": "Lighter and longer, so it casts further"},
    {"key": "rod_pro", "slot": "rod", "name": "Pro Rod", "price": 450, "rating": 6, "power": 1.3, "reach": 45,
     "desc": "Strong fighting rod with long reach"},
    {"key": "rod_northwind", "slot": "rod", "name": "Northwind Rod", "price": 0, "rating": 7, "power": 1.4, "reach": 60,
     "desc": "Signature rod from Northwind Tackle"},
    # Reel: speed sets the retrieve, drag softens each lunge of the fish
    {"key": "reel_spincast", "slot": "reel", "name": "Spincast Reel", "price": 0, "speed": 1.0, "drag": 1.0,
     "desc": "Simple and slow to wind in"},
    {"key": "reel_spinning", "slot": "reel", "name": "Spinning Reel", "price": 160, "speed": 1.35, "drag": 1.2,
     "desc": "Faster retrieve with smoother drag"},
    {"key": "reel_big", "slot": "reel", "name": "Big Game Reel", "price": 420, "speed": 1.6, "drag": 1.6,
     "desc": "Fast, with heavy drag for big fish"},
    {"key": "reel_apex", "slot": "reel", "name": "Apex Reel", "price": 0, "speed": 1.8, "drag": 1.8,
     "desc": "Signature reel from Apex Reels"},
    # Line: strength decides when a fish snaps it, stealth sets how often fish bite
    {"key": "line_mono", "slot": "line", "name": "Mono 8lb", "price": 0, "strength": 4, "stealth": 1.0,
     "desc": "Cheap, and easy for fish to see"},
    {"key": "line_fluoro", "slot": "line", "name": "Fluoro 14lb", "price": 150, "strength": 5, "stealth": 1.15,
     "desc": "Nearly invisible underwater"},
    {"key": "line_braid", "slot": "line", "name": "Braid 40lb", "price": 400, "strength": 8, "stealth": 1.1,
     "desc": "Very strong, for the heaviest fish"},
    # Hooks: a wider window makes the hookset easier
    {"key": "hook_basic", "slot": "hook", "name": "Bronze Hooks", "price": 0, "window": 1.0,
     "desc": "Standard hookset timing"},
    {"key": "hook_sharp", "slot": "hook", "name": "Sharp Hooks", "price": 120, "window": 1.5,
     "desc": "Wider hookset timing window"},
    {"key": "hook_circle", "slot": "hook", "name": "Circle Hooks", "price": 260, "window": 1.9,
     "desc": "Forgiving hookset with a big target"},
    # Scope: a wider spot-on window for casting, which also helps in bad weather
    {"key": "scope_none", "slot": "scope", "name": "No Scope", "price": 0, "tolerance": 1.0,
     "desc": "Judge the cast by eye"},
    {"key": "hook_hookline", "slot": "hook", "name": "Hookline Hooks", "price": 0, "window": 2.0,
     "desc": "Signature hooks from Hookline Co."},
    {"key": "scope_glass", "slot": "scope", "name": "Casting Scope", "price": 200, "tolerance": 1.6,
     "desc": "Wider spot-on window for a true cast"},
    {"key": "scope_laser", "slot": "scope", "name": "Laser Sight", "price": 500, "tolerance": 2.2,
     "desc": "The widest spot-on window"},
]

PART_BY_KEY = {part["key"]: part for part in PARTS}
SHOP_PARTS = [part for part in PARTS if part["price"] > 0]
STARTING_PARTS = ["rod_basic", "reel_spincast", "line_mono", "hook_basic", "scope_none"]

# Summary rows on the setup screen: (stat key, label, format, the value that fills the bar)
STAT_ROWS = [
    ("reach", "Casting reach", "+{:.0f}px", 60),
    ("tolerance", "Spot-on window", "x{:.1f}", 2.2),
    ("rating", "Rod rating", "{:.0f}", 8),
    ("power", "Fight power", "x{:.2f}", 1.4),
    ("speed", "Reel speed", "x{:.2f}", 1.8),
    ("drag", "Reel drag", "x{:.1f}", 1.8),
    ("strength", "Line strength", "{:.0f}", 8),
    ("stealth", "Line stealth", "x{:.2f}", 1.15),
    ("window", "Hookset window", "x{:.1f}", 2.0),
]
