"""The townsfolk: people about the town who are not anglers. Walk up to one and press E, and they talk. Each one has a story of
their own, which moves on one part at a time with every visit. Now and then they go to a bench, a deckchair or a shop counter,
and come back to their spot. They chat with one another in bubbles, and turn to face the angler while they talk to them."""
import math
import random

from iso.errands import SEAT_CHANCE, SHOP_CHANCE, Errands
from iso.people import build_body

ERRAND_GAP = (60.0, 150.0)  # Seconds between a townsperson's trips about the town
FLOOR_TILES = "gwdb"  # Grass, pavement, planks and sand: where people stand

TOWN_EXCHANGES = [
    ["Has Biscuit turned up yet?", "Not yet. He is probably chasing a duck.", "Give him a biscuit when he does."],
    ["Sitting or standing today?", "Sitting. That bench has the best view of the sea.", "Lucky you. My feet are killing me."],
    ["Two ice creams and a lemonade, please.", "Coming up. Only just stocked the strawberry.", "Lovely, Nell."],
    ["Mind the surf today, Sam.", "Always do. The red flags are up.", "Good. I would hate to lose a jogger."],
    ["Any news from the harbour, Gil?", "The rope has been replaced. Nothing else.", "That is a relief."],
    ["Is it going to rain?", "Not with the gulls out like this.", "Then I will sit a while longer."],
]

TOWNSFOLK = [
    {"name": "Bea", "near": (31, 46), "coat": (200, 120, 160), "hat": None, "hair": (110, 70, 40), "skirt": True,
     "greet": ["Oh, hello! Don't mind Biscuit, he's harmless."], "chat": ["Biscuit thinks every bench belongs to him.", "Lovely day for a walk."],
     "story": ["My dog Biscuit ran off into the reeds this morning.",
               "I heard barking out by the pond, but I daren't go in after him.",
               "Old Ray says he saw a dog swimming round the jetty.",
               "Biscuit is home! He had a fish, the cheeky thing. Thank you for asking."]},
    {"name": "Nell", "near": (15, 47), "coat": (240, 240, 235), "hat": (200, 60, 60), "hair": None, "skirt": False,
     "greet": ["Ice cream? Strawberry's the best today."], "chat": ["Sun like this sells more cones than the tide.", "Mind the drips, love."],
     "story": ["Ice cream's going fast today.",
               "The campers keep sending their kids over for a second cone.",
               "Tell Pen I've saved her the strawberry one.",
               "The big van is back on Saturday, with two new flavours. Don't tell the others."]},
    {"name": "Lou", "near": (34, 4), "coat": (60, 60, 70), "hat": None, "hair": (90, 60, 30), "skirt": False,
     "greet": ["Morning! Just catching my breath."], "chat": ["Five laps round the playground before breakfast.", "Good legs for it, I reckon."],
     "story": ["I jog the front every morning before the sun is up.",
               "Last week I found a little brass spoon in the reeds near the jetty.",
               "I gave it back to Old Ray. He was made up, and he told me it was his lucky one.",
               "There's a race along the front at the end of the summer. You should enter."]},
    {"name": "Sam", "near": (44, 30), "coat": (220, 40, 40), "hat": (240, 240, 240), "hair": None, "skirt": False,
     "greet": ["Keep out of the red flags, friend."], "chat": ["Sun's out, but the sea is never sunny.", "Stay where I can see you."],
     "story": ["Keep an eye on the surf. The red flags are up for a reason.",
               "A swimmer got caught in the current yesterday, out past the ropes.",
               "We got her back in, and she's fine, but she won't go near the water again.",
               "The sea's calmer now. If you hire a boat, row out past the surf and you'll be safe."]},
    {"name": "Gil", "near": (58, 23), "coat": (30, 80, 110), "hat": (30, 30, 40), "hair": None, "skirt": False,
     "greet": ["Harbour's busy this morning. Mind the ropes."], "chat": ["Every boat is back by dusk, or I hear about it.", "Ships keep their distance. Good."],
     "story": ["Boats are my life. Every one of them comes back by dusk.",
               "Someone took a rowing boat out before dawn and left it drifting.",
               "Ines brought it back in. She was not best pleased about the rope.",
               "Tell the boat hire clerk I want a full log before the next day starts."]},
]


def find_spot(level, x, y):
    """The nearest tile to (x, y) where someone can stand: open ground, pavement, planks or sand, and not taken."""
    for radius in range(0, 9):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue
                tile = (x + dx, y + dy)
                if level.walkable(*tile) and level.tile(*tile) in FLOOR_TILES:
                    return tile
    return x, y


class Townsperson(Errands):
    """Someone standing about the town. Blocks their tile when at home, so people walk round them. Each visit gives the next part
    of their story, and between visits they go on the odd errand and come back."""

    is_angler = False

    def __init__(self, render, level, data, clerks, seats):
        self.data = data
        self.name = data["name"]
        self.level = level
        self.tile = find_spot(level, *data["near"])  # Their home spot
        self.x, self.y = self.tile[0] + 0.5, self.tile[1] + 0.5
        self.body = build_body(render, self.name, data["coat"], data["hat"], hair=data["hair"], skirt=data["skirt"])
        self.node = self.body.node
        self.node.setPos(self.x, self.y, 0)
        self.body.pose("rest")
        self.init_errands(seats, clerks)
        level.blocked.add(self.tile)
        self.talking = False
        self.speaking = False
        self.beat = 0  # The part of the story the next visit gives
        self.events = []  # (speaker, text) pairs for the bubbles
        self.wander = random.uniform(*ERRAND_GAP)  # Seconds until the next trip about the town

    def distance(self, x, y):
        return math.hypot(self.x - x, self.y - y)

    def update(self, dt, frame):
        """Carries on with a trip if one is under way, or starts one when the time comes. The face shows them talking, or idle."""
        self.node.setZ(self.height + math.sin(frame * 0.05 + self.x) * 0.02)
        if not self.run_errand(dt):
            self.wander -= dt
            if self.wander <= 0 and not self.talking and not self.speaking:
                self.wander = random.uniform(*ERRAND_GAP)
                self.start_errand()
        if self.talking or self.speaking:
            self.body.set_expression("talk" if frame // 15 % 2 == 0 else "smile")
        else:
            self.body.set_expression("focus")

    def start_errand(self):
        """A trip to a bench or deckchair, to a shop counter, or nowhere this time."""
        roll = random.random()
        if roll < SEAT_CHANCE:
            self.try_seat()
        elif roll < SEAT_CHANCE + SHOP_CHANCE:
            self.try_shop()

    def after_errand(self):
        """Back from a seat or a counter: they walk home to their spot."""
        self.go_to(self.tile, "home")

    def arrived(self, errand):
        """Home again: their tile is theirs, and they stand there until the next trip."""
        if errand == "home":
            self.errand = None
            self.level.blocked.add(self.tile)

    def lines(self, rng):
        """Three lines: a greeting, the next part of the story, and a bit of small talk. Once the story is told, they just chat."""
        beats = self.data["story"]
        if self.beat < len(beats):
            story_line = beats[self.beat]
            self.beat += 1
        else:
            story_line = rng.choice(self.data["chat"])
        return [rng.choice(self.data["greet"]), story_line, rng.choice(self.data["chat"])]


def build_townsfolk(render, level, clerks, seats):
    return [Townsperson(render, level, data, clerks, seats) for data in TOWNSFOLK]
