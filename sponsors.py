# Tackle brands that sponsor the angler. Each offers a signature part, free to sign once the angler
# has enough reputation. A sponsor pays out each game day, but only while their part is fitted.
SPONSORS = [
    {"key": "northwind", "name": "Northwind Tackle", "part": "rod_northwind", "reputation": 3, "pay": 60},
    {"key": "apex", "name": "Apex Reels", "part": "reel_apex", "reputation": 6, "pay": 80},
    {"key": "hookline", "name": "Hookline Co.", "part": "hook_hookline", "reputation": 9, "pay": 60},
]

SPONSOR_BY_KEY = {sponsor["key"]: sponsor for sponsor in SPONSORS}
