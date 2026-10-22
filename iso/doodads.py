# Background life, so the place feels used. Walkers come in along the road with a trip to make: to a shop, to fish,
# out on the pier, or to talk to an NPC angler. Cars drive in along the road, park in a car park, and wait while their
# passenger goes on the trip, then drive back out. Boats, gulls and dolphins cross the sea and sky.
# Every doodad stays inside the map, and walkers stay on land while boats and dolphins stay on the sea.
# Doodads only decorate the scene. They use their own random stream and never touch the fish.
import math
import random

from panda3d.core import NodePath

from iso.level import HEIGHT, WIDTH, CAR_PARKS, PLAYGROUND, ROAD_ENTRY, ROAD_ROWS, SOUTH_ENTRY, SOUTH_ROWS, SPOTS, SPURS
from iso.lights import Signals
from iso.mesh import MeshBuilder
from iso.npcs import NPCS
from iso.passersby import line_pool, make_person
from iso.people import build_body

CLOTHES = [(200, 70, 70), (70, 120, 200), (230, 200, 80), (90, 170, 110), (160, 110, 190)]
HATS = [(60, 50, 40), (240, 240, 235), (200, 150, 60), (40, 60, 90)]
CAR_COLOURS = [(190, 40, 40), (230, 230, 235), (50, 100, 190), (230, 190, 60), (60, 60, 70)]
HULL = (120, 60, 50)
SAIL = (246, 246, 240)
DOLPHIN = (90, 130, 170)
DOLPHIN_BELLY = (200, 220, 235)
GULL = (250, 250, 250)
BIRD = (40, 40, 50)
SHIP_HULL = (60, 70, 90)
SHIP_CABIN = (240, 240, 240)
SHIP_DECK = (120, 90, 70)
SHIP_STRIPE = (200, 50, 45)
SHIP_FUNNEL = (200, 60, 50)
CONTAINERS = [(200, 70, 60), (60, 120, 200), (230, 190, 60), (90, 160, 100), (230, 230, 235)]
HULL_DECK = (150, 120, 90)
KEEL = (60, 60, 66)
MAST = (210, 210, 205)
JIB = (236, 236, 228)
DOG = (150, 100, 60)
DOG_DARK = (96, 62, 36)  # Legs, ears and tail
NOSE = (30, 25, 25)
WHEEL = (30, 30, 34)

WALK_SPEED = 1.6  # Tiles a second on foot
CAR_SPEED = 4.8  # Tiles a second on the road: about twice a walker's pace, so a car always outruns someone on foot
KID_SPEED = 2.3  # Children run about, faster than grown-ups walk
CHILD_SCALE = 0.62  # Children are built like grown-ups, then scaled down
CHILD_WITH_ADULT = 0.25  # Chance a grown-up on an ordinary trip has a child along
CHASE_EVERY = 0.5  # Seconds between a companion re-planning its way to the one it goes with
NEAR = 1  # A companion stops once it is this many tiles from the one it goes with
ROAM_RADIUS = 3  # How far a child runs about from the grown-up it is with
ROAM_REST = (0.4, 2.0)  # Seconds a child stops for between runs
SIT_DROP = -0.42  # How far a seated person's body sinks, to sit on the grass
PICNIC_AREA = (28, 30, 34, 38)  # x0, y0, x1, y1 of the grass for picnics and reading, east of the car park D
DOG_TRIPS = ("pond", "shore")  # Trips a walker brings the dog along on
RUN_SPEED = 2.6  # Tiles a second for a jogger
BEACH_AREA = (50, 16, 56, 44)  # x0, y0, x1, y1 of the sand where people sunbathe
CAR_ENTRIES = (ROAD_ENTRY, SOUTH_ENTRY)  # Where cars come in: the north road, and the south road, both from the west
WALKER_ENTRY = (1, ROAD_ROWS[0] - 1)  # Walkers come in on the pavement just inside the gate, not on the road at it
SOUTH_CAR_LOTS = ("C", "D")  # The car parks a car from the south road can reach: C by the seafront link, D from below
NORTH_CAR_LOTS = ("A", "B", "C")  # The car parks a car from the main road can reach. D is only entered from the south road
MAIN_SPUR_END = 13  # Spurs above this row run south from the main road into the north car parks. Below it, the links run north
HAIRS = [(70, 44, 28), (30, 24, 22), (200, 150, 80), (120, 60, 40)]
WOMAN_LEGS = (70, 62, 80)  # What shows under a skirt
SEA_X = (61.0, WIDTH - 1.5)  # The sea starts past the beach and the surf, and the boats cross it from one edge of the sea to the other
# Where each boat's centre may go, so the whole hull stays on the open sea and inside the map: the stern clears the beach
# and the bow clears the far edge. A boat turns out of sight once its centre passes the end of its span.
# The boats sail north and south, parallel to the shore, out on the open sea at their own column. Spans are for the
# centre along the run, and keep the whole hull inside the map: the yacht is 1.1 long behind its centre and 1.8 ahead, the ship 3 and 4.
SAILBOAT_LANE = 68.0  # The yacht's column
SHIP_LANE = 71.0  # The ship's column
SAILBOAT_SPAN = (9.0 + 1.1, HEIGHT - 1.5 - 1.8)
SHIP_SPAN = (9.0 + 3.0, HEIGHT - 1.5 - 4.0)
SKY_X = (1.5, WIDTH - 1.5)  # Birds and gulls cross the whole map at height
HEIGHT_LIMIT = 34  # Birds fly over the map, so their y stays inside it
DRIVABLE = "ak"  # Road and car park tiles, which cars can use
BLOCKED_PATIENCE = 6.0  # Seconds a traveller waits behind another before it looks for a way round
DEADLOCK_LIMIT = 12.0  # Seconds held up in a row, when no way round exists, before the traveller gives up and leaves
ENTRY_RETRY = 20  # Frames before another arrival is tried, when the road's entry is taken
BAYS = {"A": [(8, 12), (11, 12), (14, 12)], "B": [(33, 12), (36, 12), (39, 12)],
        "C": [(43, 15), (46, 15), (49, 15)], "D": [(18, 37), (21, 37), (24, 37)]}  # Parking bays in each car park, as tiles. C is the seafront one at the bend of the road
JUNCTIONS = {0, 1} | {x for columns in SPURS.values() for x in columns}  # Where cars may change lane: the entrance and the spurs
SPUR_LANES = {lot: (columns[0], columns[1]) for lot, columns in SPURS.items()}  # The column cars come in on, and the one they go out on
PLAYER = object()  # Stands in for the angler on the tiles they occupy, so travellers wait for them rather than walk through them

# What a walker sets off to do. Each trip is a goal and how long they linger there in seconds: (min, max).
# A shop trip ends at the door, where the walker goes in and is gone.
TRIPS = {
    "bait": {"stay": None, "weight": 2},
    "food": {"stay": None, "weight": 2},
    "pond": {"stay": (10, 20), "weight": 3},
    "shore": {"stay": (8, 14), "weight": 2},
    "pier": {"stay": (6, 12), "weight": 2},
    "talk": {"stay": (4, 7), "weight": 2},
    "ice": {"stay": None, "weight": 2},  # To the ice cream stall, on the south road
    "stroll": {"stay": (6, 12), "weight": 2},  # Along the south road's pavement, and back again
    # Group trips. A family takes children along and sits on the grass while they run about; two women stop to talk; a woman reads.
    "picnic": {"stay": (30, 50), "weight": 2, "group": "family", "sit": True},
    "gossip": {"stay": (12, 20), "weight": 2, "group": "friends", "lead": "woman"},
    "read": {"stay": (30, 50), "weight": 1, "lead": "woman", "sit": True},
    "play": {"stay": (25, 40), "weight": 2, "group": "family"},  # A family on the north lawn, with the children on the playground
    "beach": {"stay": (40, 60), "weight": 2, "sit": True},  # Someone sitting on the sand by the sea
    "jog": {"stay": None, "weight": 1},  # A runner along the seafront pavement, out of sight at the bend
}

# How often each kind arrives, in frames (60 a second): (min, max) gap between arrivals
SCHEDULE = [
    ("walker", (400, 900)), ("car", (420, 800)), ("birds", (3000, 5000)), ("gulls", (2400, 4000)),
    ("sailboat", (1200, 2400)), ("ship", (2400, 3600)), ("dolphin", (400, 900)),
]
WARM_UP_FRAMES = 1800  # Simulated on arrival, so the scene is already busy when you start


def area_spot(level, rng, area, ground):
    """A free tile of the given ground in an area, chosen at random, so people spread out over it rather than gathering in one place."""
    x0, y0, x1, y1 = area
    tiles = [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1) if level.tile(x, y) == ground and (x, y) not in level.blocked]
    return rng.choice(tiles)


def trip_goal(level, trip, rng):
    """Where a trip ends, as a tile. Shop trips go to the door, talk trips to a tile beside an NPC."""
    if trip in ("bait", "food"):
        return level.counters()[trip][1]
    if trip == "talk":
        spots = [level.stand_beside(npc["tile"]) for npc in NPCS]
        return rng.choice([spot for spot in spots if spot])
    if trip == "pier":
        return (47, 25)
    if trip == "ice":
        return level.counters()["icecream"][1]
    if trip in ("stroll", "gossip"):
        return (30, SOUTH_ROWS[0] - 1)
    if trip in ("picnic", "read"):
        return area_spot(level, rng, PICNIC_AREA, "g")
    if trip == "play":
        return area_spot(level, rng, PLAYGROUND, "g")
    if trip == "beach":
        return area_spot(level, rng, BEACH_AREA, "b")
    if trip == "jog":
        return (49, ROAD_ROWS[0] - 1)
    return SPOTS[trip]


class Mover:
    """Something that travels along its span from one end to the other, then leaves. Used for boats and birds.
    It travels along x at height fixed in y, or, with along_y, along y at fixed x, the way a boat runs parallel to the shore."""

    def __init__(self, root, right, span, fixed, z, speed, mesh, along_y=False):
        self.lo, self.hi = span
        self.along_y = along_y
        self.fixed = fixed
        self.pos = self.lo if right else self.hi  # Along the way it travels
        self.z = z
        self.speed = abs(speed) * (1 if right else -1)
        self.frame = 0
        self.node = mesh
        self.node.reparentTo(root)
        # The model is built along +x, so along y it turns a quarter turn to face the way it travels
        self.node.setH((90 if right else -90) if along_y else (0 if right else 180))
        self.place()

    def position(self):
        """The ground position of the centre, as (x, y)."""
        return (self.fixed, self.pos) if self.along_y else (self.pos, self.fixed)

    def place(self):
        x, y = self.position()
        self.node.setPos(x, y, self.z)

    def update(self, dt):
        self.pos += self.speed * dt * 60
        self.frame += 1
        self.place()

    def done(self):
        return self.pos < self.lo or self.pos > self.hi

    def remove(self):
        self.node.removeNode()


class Traveller:
    """Something that follows a route of tiles, one tile centre after another, and faces the way it moves.
    Two travellers never share a tile. A traveller reserves the next tile on its route, and waits while someone else
    holds it. After BLOCKED_PATIENCE seconds it looks for another way round, and keeps waiting if there is none.
    Subclasses decide what happens when the route ends."""

    diagonal = True  # Whether this kind may cut across diagonally, as people do on foot
    vehicle = False  # Cars wait for the green light at a crossing. People wait for the walk light

    def __init__(self, root, node, origin, route, speed):
        self.node = node
        self.node.reparentTo(root)
        self.x, self.y = origin[0] + 0.5, origin[1] + 0.5
        self.goal = (int(origin[0]), int(origin[1]))
        self.set_route(route)
        self.speed = speed
        self.moving = False
        self.stage = "out"
        self.occupancy = {}  # Set by the ambience each frame: which travellers stand on each tile
        self.ignore = ()  # Travellers this one may pass through, such as the car a passenger just got out of
        self.waited = 0.0
        self.stuck = 0.0  # Seconds in a row held up, with no way round, after which the traveller leaves the scene
        self.tile_now = (int(self.x), int(self.y))
        self.trail = None  # The tile this one just left
        self.place()

    def tiles(self):
        """The tiles this traveller takes up: where it stands, and the tiles ahead that it has reserved."""
        taken = [self.tile_now]
        for tile in self.ahead():
            if tile not in taken:
                taken.append(tile)
        return taken

    def ahead(self):
        """The tiles needed before the next step: the next tile on the route. A car needs more, see Car."""
        return [self.next_tile()] if self.route else []

    def next_tile(self):
        tx, ty = self.route[0]
        return (int(tx), int(ty))

    def base_passable(self, x, y):
        """Whether this kind of traveller may stand on the tile at all, ignoring other travellers."""
        return True

    def clear_ahead(self, tile):
        """Whether the tile is free for this traveller: nobody else is on it or has reserved it, and the lights let it step on."""
        if not self.level.may_enter(self, tile):
            return False
        return all(other is self or other in self.ignore for other in self.occupancy.get(tile, ()))

    def set_route(self, tiles):
        """Takes a route given as whole tiles, and turns it into the centres of those tiles. The goal is its last tile."""
        self.route = [(x + 0.5, y + 0.5) for x, y in tiles]
        if tiles:
            self.goal = (int(tiles[-1][0]), int(tiles[-1][1]))

    def reroute(self):
        """Looks for another way to the goal that avoids the tiles other travellers hold. Keeps the old route if there is none."""
        found = self.level.route(self.tile_now, self.goal, lambda x, y: self.base_passable(x, y) and self.clear_ahead((x, y)),
                                 diagonal=self.diagonal)
        if found:
            self.set_route(found)

    def advance(self, dt):
        """Moves along the route. Waits while the next tile is held, and tries another way round when it has waited a while.
        It never steps onto a tile someone else is on. Returns True once the route is finished."""
        self.moving = bool(self.route)
        if not self.route:
            return True
        needed = self.ahead()
        if not all(self.clear_ahead(tile) for tile in needed):
            self.moving = False
            if any(not self.level.may_enter(self, tile) for tile in needed):
                return False  # Held by a red light, which is not a jam, so it does not count towards giving up
            self.waited += dt
            self.stuck += dt
            if self.stuck >= DEADLOCK_LIMIT:
                # Two travellers are each waiting for the other, and no way round exists. The traveller leaves the scene.
                self.stage = "gone"
                self.route = []
                return False
            if self.waited >= BLOCKED_PATIENCE:
                self.waited = 0.0
                self.reroute()
            return False
        self.waited = 0.0
        self.stuck = 0.0
        # Claims the tiles, so nobody else who moves this frame steps onto them
        for tile in needed:
            self.occupancy.setdefault(tile, []).append(self)
        tx, ty = self.route[0]
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        step = self.speed * dt
        if dist <= step:
            self.x, self.y = tx, ty
            self.route.pop(0)
        else:
            self.x += dx / dist * step
            self.y += dy / dist * step
            self.face(dx, dy)
        self.place()
        return not self.route

    def face(self, dx, dy):
        self.node.setH(math.degrees(math.atan2(-dx, dy)))

    def place(self):
        self.node.setPos(self.x, self.y, 0)
        tile = (int(self.x), int(self.y))
        if tile != self.tile_now:
            self.trail = self.tile_now
            self.tile_now = tile

    def done(self):
        return self.stage == "gone"

    def remove(self):
        self.node.removeNode()


def random_adult(rng):
    return rng.choice(["man", "woman"])


def build_person(root, rng, kind):
    """Builds a man, a woman or a child under root. A woman has long hair and a skirt, and sometimes a bonnet.
    A child is built like a grown-up and scaled down."""
    coat = rng.choice(CLOTHES)
    if kind == "woman":
        hat = rng.choice(HATS) if rng.random() < 0.3 else None
        return build_body(root, "walker", coat, hat, trousers=WOMAN_LEGS, hair=rng.choice(HAIRS), skirt=True)
    body = build_body(root, "walker", coat, rng.choice(HATS))
    if kind == "child":
        body.node.setScale(CHILD_SCALE)
    return body


def walker_group(root, rng, level, origin, trip, goal):
    """The people who set off on one trip. A family takes one or two children and sometimes a second grown-up, two women go together,
    and any grown-up on an ordinary trip may have a child along. The first walker is the one the rest go with."""
    info = TRIPS[trip]
    lead = Walker(root, rng, level, origin, trip, goal, kind=info.get("lead") or random_adult(rng))
    group = [lead]
    if info.get("group") == "family":
        for _ in range(rng.choice((1, 1, 2))):
            group.append(Walker(root, rng, level, origin, trip, goal, kind="child", leader=lead))
        if rng.random() < 0.5:
            group.append(Walker(root, rng, level, origin, trip, goal, kind="woman" if lead.kind == "man" else "man", leader=lead))
    elif info.get("group") == "friends":
        group.append(Walker(root, rng, level, origin, trip, goal, kind="woman", leader=lead))
    elif rng.random() < CHILD_WITH_ADULT:
        group.append(Walker(root, rng, level, origin, trip, goal, kind="child", leader=lead))
    return group


class Walker(Traveller):
    """A person on foot with a trip to make. Walks out to the goal, lingers if the trip says so, then walks back
    and goes out of sight. A shop door takes them in, so they are gone at the door."""

    def __init__(self, root, rng, level, origin, trip, goal, kind="man", leader=None):
        self.level = level
        self.origin = origin
        self.goal = goal
        self.stay = TRIPS[trip]["stay"]
        self.sits = TRIPS[trip].get("sit", False)
        self.trip = trip
        self.kind = kind
        self.leader = leader  # The grown-up a child or friend goes with. A companion has no trip of its own
        self.rng = rng
        self.name, self.story = make_person(kind, rng)  # Who they are, and the story they tell when talked to
        self.beat = 0  # The part of the story the next talk gives
        self.talking = False  # Stopped to talk to the angler
        self.talk_clock = 0.0  # Runs while talking, to move the mouth
        self.events = []  # (speaker, text) pairs for the bubbles
        self.is_angler = False
        self.body = build_person(root, rng, kind)
        route = [] if leader else level.find_walk(origin, goal)
        speed = KID_SPEED if kind == "child" else RUN_SPEED if trip == "jog" else WALK_SPEED
        super().__init__(root, self.body.node, origin, route, speed)
        self.wait = rng.uniform(*self.stay) if self.stay else 0.0
        self.rest = 0.0  # Seconds left to stop for, while playing about
        self.chase = 0.0  # Seconds until a companion re-plans its way to the one it goes with
        self.dog = None
        if leader is None and (trip in DOG_TRIPS or (trip == "stroll" and kind == "woman" and rng.random() < 0.4)):
            self.dog = self.make_dog()
        self.stride = 0.0
        if not route and leader is None:
            self.stage = "gone"

    def base_passable(self, x, y):
        return self.level.pedestrian(x, y)

    def make_dog(self):
        """A small dog facing forward (+y): body, head with snout and ears, four legs that swing, and an upright tail."""
        mesh = MeshBuilder()
        mesh.ellipsoid(0, 0, 0.3, 0.14, 0.32, 0.14, DOG, steps=6)  # Body, long along the walk
        mesh.ellipsoid(0, 0.38, 0.4, 0.13, 0.14, 0.13, DOG, steps=6)  # Head
        mesh.box(-0.05, 0.44, 0.33, 0.1, 0.16, 0.08, DOG)  # Snout
        mesh.box(-0.03, 0.58, 0.38, 0.06, 0.04, 0.05, NOSE)  # Nose
        for x in (-0.12, 0.06):
            mesh.box(x, 0.3, 0.5, 0.06, 0.1, 0.1, DOG_DARK)  # Ears
        mesh.box(-0.03, -0.5, 0.36, 0.06, 0.18, 0.06, DOG)  # Tail, held up behind
        dog = mesh.build("dog")
        dog.reparentTo(self.node)
        dog.setPos(0, -0.7, 0)  # On a lead, trailing behind
        # Each leg hangs from its own hip, so it can swing as the dog trots
        self.dog_legs = []
        for x in (-0.12, 0.06):
            for y in (-0.2, 0.14):
                hip = dog.attachNewNode("hip")
                hip.setPos(x + 0.03, y + 0.03, 0.22)
                leg = MeshBuilder()
                leg.box(-0.03, -0.03, -0.22, 0.06, 0.06, 0.22, DOG_DARK)
                leg.build("dog_leg").reparentTo(hip)
                self.dog_legs.append(hip)
        return dog

    @property
    def tile(self):
        return self.tile_now

    def distance(self, x, y):
        return math.hypot(self.x - x, self.y - y)

    def face_point(self, x, y):
        """Turns to look at a point on the ground, for the talk."""
        self.node.setH(math.degrees(math.atan2(-(x - self.x), y - self.y)))

    def say(self, text, speaker=None):
        self.events.append((speaker or self, text))

    def lines(self, rng):
        """Three lines: a greeting, the next part of their story, and a bit of small talk. Once the story is told, they just chat."""
        pool = line_pool(self.kind)
        if self.beat < len(self.story):
            part = self.story[self.beat]
            self.beat += 1
        else:
            part = rng.choice(pool["chat"])
        return [rng.choice(pool["greet"]), part, rng.choice(pool["chat"])]

    def update(self, dt):
        if self.talking:
            # Stopped for a talk: they stand where they are, turned to the angler, and their mouth moves
            self.moving = False
            self.talk_clock += dt
            self.body.set_expression("talk" if int(self.talk_clock * 4) % 2 == 0 else "smile")
            self.animate(dt)
            return
        if self.body.expression in ("talk", "smile"):
            self.body.set_expression("neutral")
        if self.leader:
            self.follow(dt)
        else:
            self.go_on_trip(dt)
        self.animate(dt)

    def go_on_trip(self, dt):
        if self.stage == "out" and self.advance(dt):
            self.stage = "stay" if self.stay else "gone"
        elif self.stage == "stay":
            self.wait -= dt
            if self.wait <= 0:
                self.set_route(self.level.find_walk(self.goal, self.origin))
                self.stage = "back" if self.route else "gone"
        elif self.stage == "back" and self.advance(dt):
            self.stage = "gone"
        if self.stage not in ("out", "back"):
            self.moving = False  # Standing still at a goal, or about to go in

    def follow(self, dt):
        """A child or friend keeps by the grown-up they came with. A child runs about them while they stop, and a friend stands by.
        A companion leaves when the one it goes with has gone."""
        leader = self.leader
        if leader.done():
            self.stage = "gone"
            return
        if leader.stage == "stay" and self.kind == "child":
            self.roam(dt, leader.tile_now)
            return
        self.chase -= dt
        if self.near(leader.tile_now):
            self.set_route([])
        elif self.chase <= 0:
            self.set_route(self.level.find_walk(self.tile_now, leader.tile_now)[:-1])  # Stops beside them, not on them
            self.chase = CHASE_EVERY
        self.advance(dt)

    def near(self, tile):
        x, y = self.tile_now
        return abs(x - tile[0]) <= NEAR and abs(y - tile[1]) <= NEAR

    def roam(self, dt, centre):
        """Runs about near the centre: a run to a tile close by, a short stop, then another run."""
        if not self.route:
            self.rest -= dt
            if self.rest <= 0:
                target = self.roam_tile(centre)
                if target:
                    self.set_route(self.level.find_walk(self.tile_now, target))
                self.rest = self.rng.uniform(*ROAM_REST)
        self.advance(dt)

    def roam_tile(self, centre):
        cx, cy = centre
        for _ in range(8):
            tile = (cx + self.rng.randint(-ROAM_RADIUS, ROAM_RADIUS), cy + self.rng.randint(-ROAM_RADIUS, ROAM_RADIUS))
            if tile != centre and self.level.pedestrian(*tile):
                return tile
        return None

    def sitting(self):
        return self.sits and self.stage == "stay"

    def animate(self, dt):
        """The walk cycle swings the legs while walking, and the dog trots along behind."""
        if self.moving:
            self.stride = (self.stride + dt * 11) % (2 * math.pi)
        else:
            self.stride *= max(0.0, 1 - dt * 8)
        if self.sitting():
            self.body.pose("rest")
            self.body.sit(True)
            self.node.setZ(SIT_DROP)
        else:
            swing = math.sin(self.stride) * 35 if self.moving else 0.0
            self.body.swing(swing)
            self.node.setZ(abs(math.sin(self.stride)) * 0.05)
        if self.dog:
            self.animate_dog()
        self.body.set_expression(self.expression())

    def animate_dog(self):
        """Diagonal pairs of legs swing in step, and the dog's body stays level while the walker bobs."""
        for i, hip in enumerate(self.dog_legs):
            phase = 0.0 if i in (0, 3) else math.pi
            hip.setP(math.sin(self.stride + phase) * 28 if self.moving else 0.0)
        self.dog.setZ(-self.node.getZ())  # Cancel the walker's bob, which the dog inherits

    def expression(self):
        """What the face shows: a child is happy, walking on is neutral, looking at the water while they fish or read is focus,
        chatting is talk, and smiling is for a shop or a stroll."""
        if self.kind == "child":
            return "happy"
        if self.stage in ("out", "back") and not self.leader:
            return "neutral"
        if self.trip == "gossip":
            return "talk"
        if self.trip == "jog":
            return "strain"
        if self.trip in ("pond", "shore", "pier", "read"):
            return "focus"
        return "smile"


def car_mesh(colour):
    """A car built along +y, so it faces the way it drives, with lights at the front and their glow, which shows at night."""
    mesh = MeshBuilder()
    mesh.box(-0.5, -1.1, 0.2, 1.0, 2.2, 0.5, colour)
    mesh.box(-0.42, -0.6, 0.7, 0.84, 1.2, 0.4, (120, 160, 190))
    for x in (-0.55, 0.45):
        for y in (-0.8, 0.5):
            mesh.box(x, y, 0, 0.1, 0.4, 0.2, WHEEL)
    mesh.box(-0.4, 1.08, 0.45, 0.32, 0.06, 0.12, (255, 240, 170))
    mesh.box(0.08, 1.08, 0.45, 0.32, 0.06, 0.12, (255, 240, 170))
    root = mesh.build("car")
    glow = MeshBuilder()
    for x in (-0.24, 0.24):
        glow.ellipsoid(x, 1.2, 0.45, 0.22, 0.14, 0.16, (255, 240, 170, 170), steps=4)
    glow.build("car_glow", transparent=True).reparentTo(root)
    return root


class Car(Traveller):
    """A car that drives in along the road and parks in a free bay. Its passenger goes on their trip, and the car waits
    for them. Then it drives back out the way it came. A car that finds its bay taken takes another, or turns round."""

    diagonal = False  # Cars drive along the road and park square to the kerb
    vehicle = True

    def __init__(self, root, rng, level, lot, entry=ROAD_ENTRY):
        self.level = level
        self.lot = lot
        self.rng = rng
        self.entry = entry  # Where it came in, so it goes back out the same way
        self.passenger = None
        self.park_pending = False  # Set when parked, so the ambience sends out a passenger
        self.parked_total = 0.0
        self.stage = "in"  # Drives in along the route, then parks. Set first, as the lane a car may use depends on it
        self.bay = rng.choice(BAYS[lot])
        route = level.route(entry, self.bay, self.passable, diagonal=False)
        super().__init__(root, car_mesh(rng.choice(CAR_COLOURS)), entry, route, CAR_SPEED)
        self.glow = self.node.find("car_glow")  # Its headlight glow, shown at night
        self.stage = "in"  # The base setup resets the stage, so it is set again here
        if not route:
            self.stage = "gone"  # No way in from this entry, so it does not appear at all rather than parking on the spot
        self.parked_for = 0.0

    @staticmethod
    def covered(x, y, fx, fy):
        """The tiles under a car whose centre is at (x, y) and whose heading is (fx, fy). The body is about 2.2 long and
        1 wide, so the points are sampled along its length and across its width, and every tile they reach is covered."""
        sx, sy = fy, -fx  # Across the body
        out = []
        # Across the body the samples stay inside the car's own lane. A wider footprint would cover both lanes of the road,
        # so two cars passing each other would block one another.
        for d in (-1.1, -0.55, 0.0, 0.55, 1.1):
            for w in (-0.3, 0.0, 0.3):
                tile = (int(x + fx * d + sx * w), int(y + fy * d + sy * w))
                if tile not in out:
                    out.append(tile)
        return out

    def tiles(self):
        """Every tile the body covers where it is now, so nobody stands in the car."""
        h = math.radians(self.node.getH())
        return self.covered(self.x, self.y, -math.sin(h), math.cos(h))

    def ahead(self):
        """Before it moves on, the car needs every tile its body would cover once it reaches the next tile's centre clear.
        Then its front never reaches a tile that someone is standing on."""
        if not self.route:
            return []
        tx, ty = self.route[0]
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return []
        return self.covered(tx, ty, dx / dist, dy / dist)

    def drivable(self, x, y):
        return self.level.tile(x, y) in DRIVABLE and (x, y) not in self.level.blocked

    def passable(self, x, y):
        """Where this car may drive. Cars keep to the left, as the road rules say here: going east they use the north lane of a
        road, and going west the south lane, so cars pass each other rather than meeting head on. They change lanes only at
        the junctions, and at the entrance."""
        if not self.drivable(x, y):
            return False
        if self.level.tile(x, y) == "a" and x > 1 and x not in JUNCTIONS:
            if y in ROAD_ROWS:
                return y == (ROAD_ROWS[0] if self.stage == "in" else ROAD_ROWS[1])
            if y in SOUTH_ROWS:
                return y == (SOUTH_ROWS[0] if self.stage == "in" else SOUTH_ROWS[1])
        # Spurs and links are the rows between a road and a lot. Going south down a north spur the left is the east column;
        # going north up a link to the south lots the left is the west column
        for west, east in SPUR_LANES.values():
            if x in (west, east) and y > ROAD_ROWS[1] and y not in SOUTH_ROWS and self.level.tile(x, y) == "a":
                south_bound = y < MAIN_SPUR_END
                in_column, out_column = (east, west) if south_bound else (west, east)
                return x == (in_column if self.stage == "in" else out_column)
        return True

    def base_passable(self, x, y):
        return self.passable(x, y)

    def leave_route(self):
        """The way back out, from wherever the car is to the entrance, in the other lane."""
        self.stage = "out"
        return self.level.route(self.tile_now, self.entry, self.passable, diagonal=False)

    def arrive(self):
        """At the end of the drive. Parks if the bay is still free. Otherwise takes another free bay, or turns round
        when the lot is full. Returns True when it is parked."""
        if self.clear_ahead(self.bay):
            return True
        options = [bay for bay in BAYS[self.lot] if self.clear_ahead(bay)]
        if options:
            self.bay = self.rng.choice(options)
            self.set_route(self.level.route(self.tile_now, self.bay, self.passable, diagonal=False))
            return not self.route
        # This lot is full, so drive on to another lot that has a bay free, rather than queuing on the road
        elsewhere = [(lot, bay) for lot in sorted(BAYS) if lot != self.lot for bay in BAYS[lot] if self.clear_ahead(bay)]
        if elsewhere:
            lot, bay = self.rng.choice(elsewhere)
            route = self.level.route(self.tile_now, bay, self.passable, diagonal=False)
            if route:
                self.lot, self.bay = lot, bay
                self.set_route(route)
                return False
        self.set_route(self.leave_route())
        self.stage = "out" if self.route else "gone"
        return False

    def update(self, dt):
        if self.stage == "in" and self.advance(dt):
            if self.arrive():
                self.stage = "park"
                self.parked_for = self.rng.uniform(5, 9)
                self.park_pending = True
        elif self.stage == "park":
            self.parked_total += dt
            self.parked_for -= dt
            # Leaves once its passenger is back or gone, or after a while in case the passenger got lost
            if self.parked_for <= 0 and (self.passenger is None or self.passenger.done() or self.parked_total > 120):
                self.set_route(self.leave_route())
                self.stage = "out" if self.route else "gone"
        elif self.stage == "out" and self.advance(dt):
            self.stage = "gone"

    def leave(self):
        """Hands over the bay tile the passenger steps out at, and clears the request."""
        self.park_pending = False
        return self.bay


V_FORMATION = [(0.0, 0.0), (-0.6, 0.5), (-0.6, -0.5)]  # Where each bird sits in the V, with the leader in front


def bird_node(parent, colour, ox, oy):
    """A bird flying along +x: a small body, with a wing either side hinged at the body so it can flap. Returns the two wings."""
    root = parent.attachNewNode("bird")
    root.setPos(ox, oy, 0)
    mesh = MeshBuilder()
    mesh.ellipsoid(0, 0, 0, 0.16, 0.06, 0.05, colour, steps=4)
    mesh.build("body").reparentTo(root)
    wings = []
    for side in (1, -1):
        pivot = root.attachNewNode("wing")
        mesh = MeshBuilder()
        # A wing sweeps back from the shoulder to a tip out to the side
        mesh.triangle_both((0.1, 0.0, 0.0), (-0.16, side * 0.44, 0.0), (-0.2, 0.0, 0.0), colour)
        mesh.build("wing_part").reparentTo(pivot)
        wings.append(pivot)
    return wings


class Flock(Mover):
    """A few birds in a loose V, flapping as they go. Higher birds look further away."""

    def __init__(self, root, rng, right, colour, height):
        span = SKY_X
        group = NodePath("flock")
        count = rng.randint(2, 3)
        self.wings = []  # (left wing, right wing, phase) for each bird
        for ox, oy in V_FORMATION[:count]:
            left, right_wing = bird_node(group, colour, ox, oy + rng.uniform(-0.1, 0.1))
            self.wings.append((left, right_wing, rng.uniform(0, math.tau)))
        y = rng.uniform(4, HEIGHT_LIMIT)
        super().__init__(root, right, span, y, height, rng.uniform(0.03, 0.05), group)

    def update(self, dt):
        super().update(dt)
        for left, right_wing, phase in self.wings:
            flap = math.sin(self.frame * 0.3 + phase) * 35  # The wings beat together, one up as the other goes up
            left.setP(flap)
            right_wing.setP(-flap)


class Sailboat(Mover):
    """A sailing boat out on the open sea, moving slowly."""

    def __init__(self, root, rng, right):
        # Built along +x with the bow forward. A yacht is long and narrow, with a tall mast and a mainsail and jib.
        mesh = MeshBuilder()
        mesh.box(-1.1, -0.4, 0.0, 2.2, 0.8, 0.3, HULL)  # The hull
        mesh.triangle_both((1.1, -0.4, 0.0), (1.1, -0.4, 0.3), (1.8, 0.0, 0.0), HULL)  # The sharp bow, both sides
        mesh.triangle_both((1.1, 0.4, 0.0), (1.1, 0.4, 0.3), (1.8, 0.0, 0.0), HULL)
        mesh.triangle_both((1.1, -0.4, 0.3), (1.1, 0.4, 0.3), (1.8, 0.0, 0.0), HULL_DECK)
        mesh.box(-0.2, -0.05, -0.35, 0.4, 0.1, 0.35, KEEL)  # The keel under the water
        mesh.box(-0.05, -0.04, 0.3, 0.1, 0.08, 2.3, MAST)  # The mast
        mesh.triangle_both((0.0, 0.0, 0.45), (0.0, 0.0, 2.55), (-1.0, 0.0, 0.45), SAIL)  # The mainsail, behind the mast
        mesh.triangle_both((0.05, 0.0, 0.5), (0.05, 0.0, 2.3), (1.0, 0.0, 0.35), JIB)  # The jib, in front
        super().__init__(root, right, SAILBOAT_SPAN, SAILBOAT_LANE, 0.05, rng.uniform(0.008, 0.012), mesh.build("sailboat"), along_y=True)


class Ship(Mover):
    """A cargo ship crossing the open sea, slow and heavy."""

    def __init__(self, root, rng, right):
        # Built along +x with the bow forward. A cargo ship is about four times as long as it is wide,
        # with the accommodation block aft, a funnel, and containers stacked on the deck.
        mesh = MeshBuilder()
        mesh.box(-3.0, -0.9, 0.0, 6.0, 1.8, 0.9, SHIP_HULL)  # The hull, with the stern square
        mesh.triangle_both((3.0, -0.9, 0.0), (3.0, -0.9, 0.9), (4.0, 0.0, 0.0), SHIP_HULL)  # The bow tapers to a point
        mesh.triangle_both((3.0, 0.9, 0.0), (3.0, 0.9, 0.9), (4.0, 0.0, 0.0), SHIP_HULL)
        mesh.triangle_both((3.0, -0.9, 0.9), (3.0, 0.9, 0.9), (4.0, 0.0, 0.0), SHIP_DECK)
        mesh.box(-3.0, -0.92, 0.2, 6.0, 0.02, 0.12, SHIP_STRIPE)  # The stripe along each side
        mesh.box(-3.0, 0.9, 0.2, 6.0, 0.02, 0.12, SHIP_STRIPE)
        mesh.box(-2.6, -0.7, 0.9, 1.5, 1.4, 1.0, SHIP_CABIN)  # The accommodation block aft
        mesh.box(-1.7, -0.3, 1.9, 0.6, 0.6, 0.9, SHIP_FUNNEL)  # The funnel
        for i, x in enumerate((-1.0, -0.15, 0.7, 1.55)):
            for side in (-0.7, 0.1):
                colour = CONTAINERS[(i + int(side * 10)) % len(CONTAINERS)]
                mesh.box(x, side, 0.9, 0.8, 0.6, 0.5, colour)  # Containers, in two rows along the deck
        super().__init__(root, right, SHIP_SPAN, SHIP_LANE, 0, rng.uniform(0.01, 0.016), mesh.build("ship"), along_y=True)


class Dolphin:
    """Breaches out of the sea in an arc, then dives back under. It only appears out on the open sea."""

    def __init__(self, root, rng):
        self.life = rng.randint(55, 75)
        self.frame = 0
        self.x = rng.uniform(SEA_X[0] + 2, WIDTH - 8)
        self.y = rng.uniform(12, 34)
        self.direction = rng.choice((-1, 1))
        mesh = MeshBuilder()
        mesh.ellipsoid(0, 0, 0, 0.6, 0.22, 0.22, DOLPHIN, steps=5)
        mesh.ellipsoid(0.1, 0, -0.1, 0.4, 0.12, 0.1, DOLPHIN_BELLY, steps=4)
        self.node = mesh.build("dolphin")
        self.node.reparentTo(root)

    def update(self, dt):
        self.frame += 1
        t = min(1.0, self.frame / self.life)
        x = self.x + self.direction * 3.0 * (t - 0.5)
        z = math.sin(math.pi * t) * 1.4 - 0.2
        self.node.setPos(x, self.y, z)
        self.node.setH(0 if self.direction > 0 else 180)
        self.node.setP(math.cos(math.pi * t) * self.direction * -30)

    def done(self):
        return self.frame >= self.life

    def remove(self):
        self.node.removeNode()


class Ambience:
    """Keeps the place busy. Arrivals are random, but the same seed always gives the same mix to begin with."""

    def __init__(self, render, level):
        self.root = render.attachNewNode("ambience")
        self.level = level
        self.rng = random.Random("ambience")  # Its own stream, so the fish are not affected
        self.timers = [self.rng.randint(*gap) for _, gap in SCHEDULE]
        self.items = []
        self.signals = Signals(render, level)  # The traffic lights, which the cars and people obey at each crossing
        level.signals = self.signals
        for _ in range(WARM_UP_FRAMES):
            self.update(1 / 60)

    def update(self, dt, player_tiles=()):
        """player_tiles are the tiles the angler's body covers, which walkers and cars keep out of."""
        self.signals.update(dt)
        for i, (kind, gap) in enumerate(SCHEDULE):
            self.timers[i] -= 1
            if self.timers[i] <= 0:
                if self.arrival_blocked(kind):
                    self.timers[i] = ENTRY_RETRY  # Nobody arrives onto a tile that is already taken, and boats do not share the sea
                    continue
                self.spawn(kind)
                self.timers[i] = self.rng.randint(*gap)
        occupancy = {}
        for tile in player_tiles:
            occupancy.setdefault(tile, []).append(PLAYER)
        for item in self.items:
            if isinstance(item, Traveller):
                for tile in item.tiles():
                    occupancy.setdefault(tile, []).append(item)
        for item in self.items:
            if isinstance(item, Traveller):
                item.occupancy = occupancy
        for item in self.items:
            item.update(dt)
        for item in self.items:
            if isinstance(item, Car) and item.park_pending:
                self.send_passenger(item)
        for item in self.items:
            if item.done():
                item.remove()
        self.items = [item for item in self.items if not item.done()]

    def taken_tiles(self):
        """Every tile a walker or car is on, or has reserved, so the angler does not walk into them."""
        return {tile for item in self.items if isinstance(item, Traveller) for tile in item.tiles()}

    def arrival_blocked(self, kind):
        """Whether an arrival of this kind would land on someone. Cars may come in at either entry, so both must be clear."""
        if kind == "walker":
            return self.entry_taken(ROAD_ENTRY)
        if kind == "car":
            return any(self.entry_taken(entry) for entry in CAR_ENTRIES)
        return kind in ("sailboat", "ship") and self.boat_taken(kind)

    def entry_taken(self, entry=ROAD_ENTRY):
        """Whether someone is near an entry, where walkers and cars arrive. A car arriving covers the two tiles beyond the
        entry, and the lane beside it, so anyone standing there is in the way and nobody arrives on top of them."""
        ex, ey = entry
        return any(tx <= ex + 2 and ey - 1 <= ty <= ey + 2
                   for item in self.items if isinstance(item, Traveller) for tx, ty in item.tiles())

    def boat_taken(self, kind):
        """Whether a boat of this kind is already out on the sea. Each kind has its own row, and only one of each is out at once."""
        boat = Sailboat if kind == "sailboat" else Ship
        return any(isinstance(item, boat) for item in self.items)

    def spawn(self, kind):
        rng = self.rng
        if kind == "walker":
            trip = self.pick_trip()
            goal = trip_goal(self.level, trip, rng)
            self.items.extend(walker_group(self.root, rng, self.level, WALKER_ENTRY, trip, goal))
        elif kind == "car":
            entry = rng.choice(CAR_ENTRIES)
            lots = NORTH_CAR_LOTS if entry == ROAD_ENTRY else SOUTH_CAR_LOTS
            self.items.append(Car(self.root, rng, self.level, self.least_busy_lot(lots), entry))
        elif kind == "birds":
            self.items.append(Flock(self.root, rng, rng.random() < 0.5, BIRD, 6.5))
        elif kind == "gulls":
            self.items.append(Flock(self.root, rng, rng.random() < 0.5, GULL, 4.5))
        elif kind == "sailboat":
            self.items.append(Sailboat(self.root, rng, rng.random() < 0.5))
        elif kind == "ship":
            self.items.append(Ship(self.root, rng, rng.random() < 0.5))
        else:
            self.items.append(Dolphin(self.root, rng))

    def least_busy_lot(self, lots):
        """The car park, of those given, with the fewest cars in it or on their way, so new arrivals spread out over the lots."""
        busy = {lot: sum(1 for item in self.items if isinstance(item, Car) and item.lot == lot) for lot in lots}
        fewest = min(busy.values())
        return self.rng.choice([lot for lot, count in busy.items() if count == fewest])

    def pick_trip(self, solo=False):
        """A trip at random. solo leaves out the trips that take a group, for someone who comes out of a car on their own."""
        names = [name for name in TRIPS if not (solo and TRIPS[name].get("group"))]
        return self.rng.choices(names, weights=[TRIPS[name]["weight"] for name in names])[0]

    def send_passenger(self, car):
        """Someone gets out of the parked car and sets off on a trip."""
        trip = self.pick_trip(solo=True)
        kind = TRIPS[trip].get("lead") or random_adult(self.rng)
        walker = Walker(self.root, self.rng, self.level, car.leave(), trip, trip_goal(self.level, trip, self.rng), kind=kind)
        walker.ignore = (car,)  # Steps out of the car, so the car does not block them
        car.passenger = walker
        self.items.append(walker)
