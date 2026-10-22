from fish import SPECIES

AREAS = ["pond", "shore", "boat"]
AREA_NAMES = {"pond": "Pond", "shore": "Shore", "boat": "Open Sea"}
AREA_BY_NAME = {spec["name"]: area for area in AREAS for spec in SPECIES[area]}

LORE = {
    "Bluegill": "A small sunfish that hangs in the lily pads. Easy to catch, and a fine place to start.",
    "Carp": "Big, tough and patient. Carp feed in the mud at night and do not spook easily.",
    "Moonlit Bream": "A silver bream that only shows under the moon, and only to anglers who have helped the town. Old Ray swears they are lucky.",
    "Largemouth Bass": "The pond's top predator. Bass ambush bait near cover at dawn and dusk.",
    "Mullet": "Schools of mullet work the surf line. Fast and skittish, they are easy to lose.",
    "Trevally": "A fast, hard-fighting hunter that chases baitfish through the surf at dawn and dusk.",
    "Grouper": "A heavy bottom fish that lives around rocks. It feeds at night and does not give up ground.",
    "Mackerel": "Fast schooling fish that go wild for a jig fluttering through the water by day.",
    "Yellowfin Tuna": "A powerful open-sea hunter that feeds at first light. It needs braid and a strong rod.",
    "Sailfish": "The fastest fish in the sea, and the trophy of open water. Only the best tackle can hold one.",
}

# (area, kinds of fish caught, title, money reward). "all" counts every area.
MILESTONES = [
    ("pond", 2, "Pond regular: 2 kinds of pond fish", 100),
    ("shore", 2, "Surf regular: 2 kinds of shore fish", 150),
    ("boat", 2, "Open sea regular: 2 kinds of sea fish", 200),
    ("all", 6, "Field biologist: 6 kinds of fish", 400),
]


def log_catch(log, fish):
    """Keeps a count and the personal bests for each kind of fish."""
    entry = log.setdefault(fish.name, {"count": 0, "best_lbs": 0.0, "best_len": 0.0})
    entry["count"] += 1
    entry["best_lbs"] = max(entry["best_lbs"], fish.lbs)
    entry["best_len"] = max(entry["best_len"], fish.length)


def kinds_caught(log, key):
    if key == "all":
        return len(log)
    return sum(1 for name in log if AREA_BY_NAME[name] == key)


def claim_rewards(economy):
    """Pays out any milestone that has just been reached. Returns a message for each one."""
    messages = []
    for key, need, title, reward in MILESTONES:
        if key in economy.claimed or kinds_caught(economy.catch_log, key) < need:
            continue
        economy.claimed.add(key)
        economy.money += reward
        messages.append(f"{title} (+${reward})")
    return messages
