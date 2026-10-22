"""The NPC anglers. Walk up to one and press E: they give a tip about the area they fish, then say something in passing.
They always face the water they fish in. They fish too: a float on the water, a bite, a fight, and a fish held up when they land it.
Now and then they go on an errand: a move to another spot, a rest on a bench or deckchair, or a trip to a shop counter.
Two of them now and then strike up a conversation with each other."""
import math
import random

from panda3d.core import LineSegs, Point3

from iso.errands import SHOP_CHANCE, SEAT_CHANCE, Clerk, Errands, Seats
from iso.fish_model import build_fish
from iso.level import HEIGHT, KIOSKS, NPC_TILES, WIDTH
from iso.mesh import MeshBuilder
from iso.people import build_body
from iso.school import WATER_Z

TALK_RANGE = 2.2  # Tiles from an NPC within which they will talk to the angler
NEAR_WATER = 4.5  # Within this many tiles of water an NPC fishes with the rod out. Further off, they carry the rod on their back
CHAT_RANGE = 14  # Tiles within which two anglers will strike up a conversation, when there are two close enough
CHAT_GAP = (15.0, 30.0)  # Seconds between conversations
LINE_TIME = 3.4  # Seconds each line of a conversation stays up
BITE_WAIT = (6.0, 14.0)  # Seconds an angler waits for a bite
BITE_TIME = 0.6  # Seconds the float dips before the fish is on
FIGHT_TIME = (1.2, 2.6)  # Seconds the fight with a fish lasts
MISS_CHANCE = 0.3  # Chance the fish gets away
HOLD_TIME = 3.0  # Seconds a landed fish is held up before it goes in the bucket
MISS_TIME = 2.0  # Seconds an angler looks at the empty line after a miss
MISS_LINES = ["It got away!", "Lost it right at the bank. Bad luck.", "The hook came free. Back in the water."]
FLOAT_RED = (230, 60, 50)
FLOAT_WHITE = (245, 245, 245)
LINE_COLOUR = (0.85, 0.85, 0.8, 1)
ROD_LENGTH = 1.2  # The rod's length, as built in iso/people.py
SPOT_GAP = (180.0, 360.0)  # Seconds an angler fishes one spot before packing up for another: 3 to 6 minutes
SPOT_SEARCH = 8  # Tiles around the angler to look for a new spot
WATER_REACH = 3  # Tiles within which a spot has the water of its own kind
FIGHT_MOOD = {"bite": "surprised", "fight": "strain", "hold": "happy", "miss": "sad"}  # The face for each fishing state

EXCHANGES = [
    ["Anything biting over your side?", "Nothing but weed. The fish are sulking.", "Sulking, my foot. They know I'm watching."],
    ["Did you hear the boat horn this morning?", "Ines lost her hat to it again.", "Typical. Tie the hat on with a line."],
    ["Shall we share the bait, then?", "Only if you bring the sandwiches.", "Deal. Pen always has too many."],
    ["Your float's dancing.", "Just the wind, I hope.", "Then keep your eyes on it."],
    ["The sea's rough out past the surf.", "Good for the big ones, bad for the boats.", "Ines will be out there anyway."],
    ["Any sign of the carp under the jetty?", "Not since the campers lit their fire.", "Then they'll be back at dusk, same as always."],
]

NPCS = [
    {
        "name": "Old Ray", "area": "pond", "tile": NPC_TILES["pond"], "coat": (96, 120, 70), "hat": (120, 84, 50), "face": 0,
        "greet": ["Morning. Quiet one today.", "Ah, you again. Pull up a bit of grass.", "Mind the reeds, they like a hook."],
        "tips": [
            "Bluegill feed in the day. Carp come up at night, so fish the pond after dark for them.",
            "Watch the float. A small nibble is a warning. Wait for the big dip before you strike.",
            "A full cast reaches the fish far out. A short one only reaches the ones under your feet.",
            "Scent pulls the nearby fish towards your bait, so they come to it instead of drifting past.",
        ],
        "chat": ["My knees say rain. My line says nothing yet.", "Lost a hook to that old branch last week.",
                 "The ducks have gone quiet. Usually a good sign."],
    },
    {
        "name": "Marisol", "area": "shore", "tile": NPC_TILES["shore"], "coat": (180, 96, 70), "hat": (230, 220, 200), "face": 0,
        "hair": (90, 55, 35), "skirt": True,
        "greet": ["Hey there. Surf's up a bit.", "You fishing the shore? Good, I could use the company.", "Careful on the sand, it's soft."],
        "tips": [
            "Reel a paddletail steadily through the surf, then tap Up to twitch it. The fish strike at the flicker.",
            "Keep the fight marker in the green. When the tension bar goes coral, ease off on Up.",
            "Clam scent is worth the money on the surf. It pulls the fish in close to the beach.",
            "Watch the weather. The fish strike differently in a storm, so change your tactics.",
        ],
        "chat": ["The gulls are following a shoal today.", "I have a good feeling about the tide. Don't ask me why.",
                 "Never fish the surf with frayed line. Ask me how I know."],
    },
    {
        "name": "Tom", "area": "pond", "tile": NPC_TILES["jetty"], "coat": (150, 110, 80), "hat": (70, 70, 80), "face": 0,
        "greet": ["Off the jetty today. Bank's quiet.", "Morning. Mind the boards, they're slippery.", "Pull up a plank, the fish won't mind."],
        "tips": [
            "Fish the jetty's edge, where the reeds drop off. The pike lie just under the boards.",
            "A slow retrieve beats a fast one in the pond. Let the bait settle between turns.",
            "Watch the ducks. When they dive, something is feeding below them.",
        ],
        "chat": ["The campers on the sand made a fire again last night.", "Best catch I ever had came off this jetty.",
                 "Too still for my liking. A breeze brings the fish up."],
    },
    {
        "name": "Pen", "area": "pond", "tile": NPC_TILES["camp"], "coat": (120, 150, 90), "hat": (230, 200, 90), "face": 0,
        "hair": (210, 170, 90), "skirt": True,
        "greet": ["Lovely day for a picnic. Want a sandwich?", "Our camp is a bit far from the water, but the view's grand.", "Mind the fire pit."],
        "tips": [
            "Fish the pond from the jetty at dusk. The bream feed as the light goes.",
            "A bobber that sinks slowly means a fish has taken the bait and is moving off.",
            "Keep your bait fresh. Old bait draws fewer bites from the pond.",
        ],
        "chat": ["The ice cream van is parked by the south road today.", "I haven't caught a thing, but the sunsets make up for it.",
                 "Souvenirs in the stall, if you want a keepsake."],
    },
    {
        "name": "Ines", "area": "boat", "tile": NPC_TILES["boat"], "coat": (70, 110, 150), "hat": (200, 60, 50), "face": 0,
        "hair": (40, 30, 30), "skirt": True,
        "greet": ["Morning out here. Breeze cuts right through.", "Good, you came to the end of the pier. Nobody else bothers.", "Ahoy. Watch the planks.",
                     "Hire a rowing boat at the kiosk by the pier if you want the open sea. It lasts the day."],
        "tips": [
            "Let the micro jig fall, then jerk it in rhythm. Three jerks in a row bring the predators up.",
            "Deep fish are big fish. Sink your jig to their layer before you start the rhythm.",
            "Chum draws the big ones in. It costs more, but one good strike pays for the block.",
            "The depth readout tells you how far down the jig is. Trust it more than your eye.",
        ],
        "chat": ["Saw a dolphin off the end of the pier this morning.", "The ships keep their distance. Suits me.",
                 "Gulls circle when there is bait in the water."],
    },
]


def nearest_water(level, x, y):
    """The middle of the water tile closest to this point, and how far off it is. (None, None) if the map has no water."""
    best, best_d = None, None
    for ty in range(HEIGHT):
        for tx in range(WIDTH):
            if level.water_zone(tx, ty):
                d = math.hypot(tx + 0.5 - x, ty + 0.5 - y)
                if best_d is None or d < best_d:
                    best, best_d = (tx + 0.5, ty + 0.5), d
    return best, best_d


class NPC(Errands):
    """A fisher standing on their spot. Blocks their tile, so people walk round them. They always face the water they fish in,
    and hold the rod out only when it is close, so an angler who is far from the water carries the rod on their back.
    Every few minutes they go on an errand, and then fish from a spot on the same water."""

    is_angler = True  # Counts towards the story's first job, of saying hello to the anglers

    def __init__(self, render, level, data, catch_fish, clerks, seats):
        self.render = render
        self.level = level
        self.data = data
        self.name = data["name"]
        self.tile = data["tile"]
        self.catch_fish = catch_fish  # Gives a random fish from an area, for the angler to land
        self.x, self.y = self.tile[0] + 0.5, self.tile[1] + 0.5
        self.body = build_body(render, self.name, data["coat"], data["hat"], rod=True, hair=data.get("hair"), skirt=data.get("skirt", False))
        self.node = self.body.node
        self.node.setPos(self.x, self.y, 0)
        self.init_errands(seats, clerks)
        self.talking = False  # Talking with the angler
        self.speaking = False  # Saying a line to another angler, whose mouth moves
        self.catches = 0
        self.state = "wait"  # The fishing: wait, bite, fight, hold (a landed fish), or miss
        self.timer = random.uniform(*BITE_WAIT)
        self.events = []  # (speaker, text) pairs for the bubbles: what they say, and what a clerk answers
        self.held = None  # The fish held up after a catch
        self.float = None
        self.line = None  # The line from the rod to the float, drawn each frame
        self.spot_timer = random.uniform(*SPOT_GAP)
        self.water = None
        self.near_water = False
        level.blocked.add(self.tile)
        self.settle()

    def settle(self):
        """Works out the water they fish in from where they stand: the rod comes out and the float is set if it is close,
        and they turn to face it."""
        self.water, water_distance = nearest_water(self.level, self.x, self.y)
        self.near_water = water_distance is not None and water_distance <= NEAR_WATER
        self.body.set_rod_out(self.near_water)
        self.body.pose("rod" if self.near_water else "rest")
        if self.near_water and self.float is None:
            self.float = self.build_float(self.render)
        if self.float:
            self.float.show() if self.near_water else self.float.hide()
        self.face_water()

    def build_float(self, render):
        """A float on the water they fish in, which dips when a fish bites."""
        mesh = MeshBuilder()
        mesh.ellipsoid(0, 0, 0.03, 0.05, 0.05, 0.05, FLOAT_RED, steps=3)
        mesh.ellipsoid(0, 0, 0.1, 0.03, 0.03, 0.03, FLOAT_WHITE, steps=3)
        float_node = mesh.build("npc_float")
        float_node.reparentTo(render)
        return float_node

    def face_water(self):
        """Turns to look at the water, which is where they fish. Always: walking, sitting, buying or fishing."""
        if self.water:
            self.face_point(*self.water)

    def distance(self, x, y):
        return math.hypot(self.x - x, self.y - y)

    def update(self, dt, frame):
        """A little idle sway, so they do not look like a statue. The face shows what they are doing: watching the water
        while they fish, mouth moving while they talk, and a fish's fight while it bites."""
        self.node.setZ(self.height + math.sin(frame * 0.05 + self.x) * 0.02)
        if not self.run_errand(dt):
            self.update_fishing(dt)
            self.spot_timer -= dt
            if self.spot_timer <= 0 and self.state == "wait" and not self.talking and not self.speaking:
                self.start_errand()
        self.face_water()  # Always turned to the water they fish in
        if self.talking or self.speaking:
            self.body.set_expression("talk" if frame // 15 % 2 == 0 else "smile")
        else:
            self.body.set_expression(FIGHT_MOOD.get(self.state, "focus"))
        if self.float and self.near_water:
            dip = 0.12 if self.state in ("bite", "fight") else 0.0
            bob = math.sin(frame * 0.1 + self.x) * 0.02
            self.float.setPos(self.water[0], self.water[1], WATER_Z + 0.02 - dip + bob)
            self.draw_line()

    def draw_line(self):
        """The line from the rod's tip down to the float, redrawn each frame as the rod and float move."""
        if self.line:
            self.line.removeNode()
        tip = self.render.getRelativePoint(self.body.rod, Point3(0, ROD_LENGTH, 0))  # The rod runs along its own +y to its tip
        float_pos = self.float.getPos(self.render)
        lines = LineSegs()
        lines.setColor(*LINE_COLOUR)
        lines.setThickness(1.5)
        lines.moveTo(tip)
        lines.drawTo(float_pos)
        self.line = self.render.attachNewNode(lines.create())

    def update_fishing(self, dt):
        """An angler waits for a bite, the float dips, they fight the fish, and land it or lose it. A landed fish is held up
        and then goes in the bucket. Anglers who are far from the water do not fish."""
        if not self.near_water:
            return
        self.timer -= dt
        if self.timer > 0:
            return
        if self.state == "wait":
            self.set_state("bite", BITE_TIME)
        elif self.state == "bite":
            self.set_state("fight", random.uniform(*FIGHT_TIME))
        elif self.state == "fight":
            if random.random() < MISS_CHANCE:
                self.say(random.choice(MISS_LINES))
                self.set_state("miss", MISS_TIME)
            else:
                self.land()
        elif self.state == "hold":
            self.release()
            self.set_state("wait", random.uniform(*BITE_WAIT))
        elif self.state == "miss":
            self.set_state("wait", random.uniform(*BITE_WAIT))

    def set_state(self, state, seconds):
        self.state = state
        self.timer = seconds

    def land(self):
        """Lands a fish and holds it up in front of them for a few seconds."""
        fish = self.catch_fish(self.data["area"])
        self.catches += 1
        self.held = build_fish(self.render, fish)[0]
        self.held.reparentTo(self.node)
        self.held.setPos(0.1, 0.55, 1.0)  # Held out in front, at the height of the hands
        self.held.setH(90)  # Turned to face the way the angler faces, so the catch can be seen
        self.held.setScale(0.7)
        self.say(f"Got one! A {fish.name}")
        self.set_state("hold", HOLD_TIME)

    def release(self):
        if self.held:
            self.held.removeNode()
            self.held = None

    def start_errand(self):
        """When the spot has been fished long enough, the angler goes off on an errand: a rest on a seat, a trip to a shop,
        or simply a move to another spot. If an errand has no way to get to it, they move instead."""
        self.spot_timer = random.uniform(*SPOT_GAP)
        roll = random.random()
        if roll < SEAT_CHANCE and self.try_seat():
            return
        if roll < SEAT_CHANCE + SHOP_CHANCE and self.try_shop():
            return
        self.start_walk()

    def start_walk(self):
        """Picks a new spot a few tiles off, on the same water, and sets off for it. If there is none, they keep their place."""
        here = (int(self.x), int(self.y))
        options = []
        for dx in range(-SPOT_SEARCH, SPOT_SEARCH + 1):
            for dy in range(-SPOT_SEARCH, SPOT_SEARCH + 1):
                tile = (here[0] + dx, here[1] + dy)
                if tile != self.tile and self.level.walkable(*tile) and self.has_water(tile):
                    options.append(tile)
        if options:
            self.go_to(random.choice(options), "spot")

    def has_water(self, tile):
        """Whether there is water of this angler's own kind within a few tiles of the tile."""
        tx, ty = tile
        return any(self.level.water_zone(tx + dx, ty + dy) == self.data["area"]
                   for dx in range(-WATER_REACH, WATER_REACH + 1) for dy in range(-WATER_REACH, WATER_REACH + 1))

    def leave_post(self):
        """Packs up for the walk: the rod goes on the back, and the float and line come in."""
        self.near_water = False
        self.body.set_rod_out(False)
        self.body.pose("rest")
        if self.float:
            self.float.hide()
        if self.line:
            self.line.removeNode()
            self.line = None

    def after_errand(self):
        """Back from a seat or a counter: they go on to a new spot to fish from."""
        self.start_walk()

    def arrived(self, errand):
        """At a new spot: their tile is theirs again, and they set up to fish there."""
        if errand == "spot":
            self.tile = (int(self.x), int(self.y))
            self.level.blocked.add(self.tile)
            self.state = "wait"
            self.timer = random.uniform(*BITE_WAIT)
            self.settle()

    def lines(self, rng):
        """What they say when talked to: a greeting, a tip about their area, and a bit of small talk."""
        chat = rng.choice(self.data["chat"])
        if self.catches:
            chat = f"I've landed {self.catches} since I got here. Don't tell the others."
        return [rng.choice(self.data["greet"]), rng.choice(self.data["tips"]), chat]


class Chatter:
    """People talk to one another now and then. Two of them, close together where they can be, trade a few lines,
    each in a bubble above their head, and face each other while they talk. Anyone talking with the angler stays out of it."""

    def __init__(self, people, exchanges=EXCHANGES):
        self.people = people
        self.exchanges = exchanges  # The conversations they may have, each a list of lines that alternate between the two
        self.timer = random.uniform(*CHAT_GAP)
        self.lines = []  # The conversation still to say: (speaker, partner, text)
        self.members = []  # The two people in the conversation under way
        self.left = 0.0  # Seconds the line on show has left

    def update(self, dt, bubbles, busy):
        """Says the next line when the last one has had its time. busy is the names of the people talking with the angler."""
        if any(person.name in busy for person in self.members):
            self.lines = []
            self.end()
        self.timer -= dt
        if not self.lines and not self.members and self.timer <= 0:
            self.start(busy)
            self.timer = random.uniform(*CHAT_GAP)
        self.left -= dt
        if self.lines and self.left <= 0:
            speaker, partner, text = self.lines.pop(0)
            self.show_line(speaker, partner, text, bubbles)
            self.left = LINE_TIME
        if not self.lines and self.members and self.left <= 0:
            self.end()

    def start(self, busy):
        free = [person for person in self.people if person.name not in busy]
        pairs = [(a, b) for i, a in enumerate(free) for b in free[i + 1:]]
        if not pairs:
            return
        close = [(a, b) for a, b in pairs if a.distance(b.x, b.y) <= CHAT_RANGE]
        a, b = random.choice(close or pairs)
        exchange = random.choice(self.exchanges)
        self.lines = [(a, b, text) if i % 2 == 0 else (b, a, text) for i, text in enumerate(exchange)]
        self.left = 0.0

    def show_line(self, speaker, partner, text, bubbles):
        for person, other in ((speaker, partner), (partner, speaker)):
            if not person.is_angler:  # Anglers keep facing the water, so only the townsfolk turn to each other
                person.face_point(other.x, other.y)
        speaker.speaking = True
        partner.speaking = False
        self.members = [speaker, partner]
        bubbles.say(f"chat-{speaker.name}", speaker, text, LINE_TIME - 0.4)

    def end(self):
        for person in self.members:
            person.speaking = False
        self.members = []


def build_clerks(level):
    """The shop clerks, one behind each shop counter, by kiosk key."""
    return {key: Clerk(key, KIOSKS[key]["name"], counter, front)
            for key, (counter, front) in level.counters().items() if KIOSKS[key].get("shop", True)}


def build_seats(benches, deckchairs):
    return Seats(benches, deckchairs)


def build_npcs(render, level, catch_fish, clerks, seats):
    return [NPC(render, level, data, catch_fish, clerks, seats) for data in NPCS]
