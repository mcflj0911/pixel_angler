import heapq
import math
import random

from iso.mesh import MeshBuilder

WIDTH, HEIGHT = 84, 48  # Size of the level in tiles. The land is bigger, and the open sea is out past the beach
START = (15, 15)  # Where the angler starts, on the grass between the car park and the pond
WALKABLE = set("gbdakw")  # Grass, sand, planks, asphalt, car parks and pavements. Everything else blocks movement, kiosks and houses included
SOFT = set("gbh")  # Grass, sand and the house plots, which fade into one another rather than meeting in hard tile edges
CROSSING_COLUMNS = (1, 2, 8, 9, 35, 36, 46)  # Where people may cross the road, on the zebra crossings and the spurs into the car parks
WATER_ZONE = {"p": "pond", "r": "pond", "s": "shore", "o": "boat"}  # Water tile to the area it belongs to
SNAG_PER_ZONE = 5  # Hidden stumps in each salt water area, which can catch the lure
WATER_ALPHA = 150  # The water is see-through, so fish swimming under the surface can be seen

COLOURS = {
    "g": (50, 68, 44), "b": (104, 92, 64), "d": (84, 58, 38),
    "p": (24, 62, 58), "r": (34, 80, 96), "s": (32, 78, 96), "o": (12, 28, 60),
    "#": (66, 66, 74), "t": (46, 36, 28), "a": (70, 72, 78), "k": (60, 62, 68), "C": (96, 78, 60), "K": (90, 84, 78),
    "w": (126, 122, 114),  # Pavement, paved in slabs beside the road
}
FOAM = (58, 84, 88)  # Water along the edge of the land
TRUNK = (62, 42, 28)
CANOPIES = [(34, 74, 40), (44, 88, 48), (28, 62, 42)]  # Tree crowns, in several greens
TUFTS = [(70, 100, 56), (40, 60, 38), (92, 122, 62)]  # Blades of grass
ROCK_SHADES = [(92, 92, 100), (78, 78, 86), (104, 98, 92)]
CLIFF = (34, 34, 40)
STUMP = (38, 30, 24)
POST = (56, 40, 28)  # Dock and pier posts
LINE = (226, 226, 214)  # Road and car park markings
WALL_HEIGHT = 1.8  # Shops are two storeys' worth of blocks, with a roof on top
ROOF_HEIGHT = 0.3

POND_CENTRE = (13, 25)
POND_RADIUS = (7, 5)
RIVER_X = 20  # The river leaves the pond at this column and runs east to the surf
PIER_ROWS = (24, 25)  # The long pier runs out to sea along these two rows
PIER_FROM, PIER_TO = 34, 64  # The pier runs out over the beach and the surf, and ends out on the open sea
BRIDGE_COLUMNS = (27, 28)  # Where a footpath crosses the river
ROAD_ROWS = (6, 7)  # The main road runs along these two rows, from the map's west edge
SOUTH_ROWS = (42, 43)  # A second road runs parallel across the south of the map, on the far side from the houses
ROAD_END = 51  # The main road runs east to the seafront, where it bends south into the seafront car park, rather than dead-ending
ROAD_ENTRY = (0, 6)  # Cars and walkers come in from the west edge, through the gap in the wall
SOUTH_ENTRY = (0, SOUTH_ROWS[0])  # Cars come in from the west edge on the south road too, on the far side of the road
PLAYGROUND = (28, 1, 36, 3)  # x0, y0, x1, y1 of the north lawn where the playground stands
CAR_PARKS = {"A": (7, 16, 10, 13), "B": (32, 40, 10, 13), "C": (42, 51, 13, 17), "D": (16, 27, 35, 39)}
SOUTH_LOTS = {"D"}  # Car parks entered from the south road, below them, rather than from the main road above  # x0, x1, y0, y1 of each car park, inclusive
SPURS = {"A": (8, 9), "B": (35, 36), "C": (50, 51), "D": (22, 23)}  # The columns of the roads from the main road into each car park. C is the bend.
HOUSES = [(4, 1, 4, 3), (11, 1, 5, 3), (19, 1, 4, 3)]
JETTY_COLUMNS = (12, 13)  # A wooden jetty runs out from the south shore of the pond, over these columns
JETTY_ROWS = range(27, 32)
CAMPSITE = (3, 34, 9, 40)  # x0, y0, x1, y1 of the camping spot beyond the pond, kept clear of trees  # Houses across the road from the pond: x0, y0, width and depth, in tiles
# Kiosks: a counter two tiles wide on the row (x, y), with the shopkeeper's back on the row behind it.
# Customers queue on the grass in front of the counter, and the name is on the awning.
KIOSKS = {
    "bait": {"x": 19, "y": 9, "name": "Bait & Tackle"},
    "food": {"x": 26, "y": 9, "name": "Food Store"},
    "boats": {"x": 36, "y": 20, "name": "Boat Hire"},  # Hire a rowing boat to fish the open sea
    # Stalls on the far side of the south road. They are for looking at, and do not open a shop screen.
    "icecream": {"x": 14, "y": 45, "name": "Ice Cream", "shop": False},
    "souvenirs": {"x": 30, "y": 45, "name": "Souvenirs", "shop": False},
}
# Spots where anglers fish, and where the NPC anglers stand to talk. The boat spot is out at the end of the pier, over the sea.
SPOTS = {"pond": (13, 20), "shore": (55, 27), "boat": (62, 24)}
NPC_TILES = {"pond": (16, 17), "shore": (53, 30), "boat": (33, 26), "jetty": (12, 32), "camp": (11, 38)}


def coast(y):
    """The shoreline's x at this row. It wiggles, so the coast is not a straight wall."""
    return 56 + round(1.5 * math.sin(y * 0.3))


def river_y(x):
    """The middle of the river at this column. It drifts down a little and wiggles, so it meanders."""
    return 25 - (x - RIVER_X) * 0.12 + 2.2 * math.sin((x - RIVER_X) * 0.5)


def river_half_width(x):
    """Half the river's width here, which swells and narrows, from about one tile to two."""
    return 0.9 + 0.5 * (1 + math.sin(x * 0.45 + 1))


def generate(seed):
    """Lays out the pond, the river to the surf, the beach, the open sea, the pier, the roads, the car parks and the shops,
    with trees and rocks on the grass."""
    rng = random.Random(seed)
    grid = [["g"] * WIDTH for _ in range(HEIGHT)]

    for y in range(HEIGHT):
        c = coast(y)
        for x in range(WIDTH):
            if x in (0, WIDTH - 1) or y in (0, HEIGHT - 1):
                grid[y][x] = "#"
            elif x >= c + 2:
                grid[y][x] = "o"  # Open sea
            elif x >= c:
                grid[y][x] = "s"  # Surf, the shallow water along the beach
            elif x >= c - 2:
                grid[y][x] = "b"  # Beach
    grid[ROAD_ENTRY[1]][0] = "a"  # The road comes in through the wall
    grid[ROAD_ENTRY[1] + 1][0] = "a"
    grid[SOUTH_ENTRY[1]][0] = grid[SOUTH_ENTRY[1] + 1][0] = "a"  # The south road comes in through the wall too

    # The pond, set in the grass on the west side
    px, py = POND_CENTRE
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if ((x - px) / POND_RADIUS[0]) ** 2 + ((y - py) / POND_RADIUS[1]) ** 2 < 1 and grid[y][x] == "g":
                grid[y][x] = "p"

    # The river: from the pond, meandering east across the grass, with its width swelling and narrowing, into the surf
    for x in range(RIVER_X - 2, coast(20) + 1):
        middle, half = river_y(x), river_half_width(x)
        for y in range(int(middle - half - 1), int(middle + half + 2)):
            if abs(y + 0.5 - middle) <= half and grid[y][x] in "gb":
                grid[y][x] = "r"
    # The banks: grass beside the river turns to sand, so the water has a shore
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if grid[y][x] == "g" and any(0 <= x + dx < WIDTH and 0 <= y + dy < HEIGHT and grid[y + dy][x + dx] == "r"
                                         for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                grid[y][x] = "b"

    # The footpath bridge: the river tiles in the bridge columns are planks, so people can cross
    for x in BRIDGE_COLUMNS:
        for y in range(HEIGHT):
            if grid[y][x] == "r":
                grid[y][x] = "d"

    # The pier: a long boardwalk from the grass, out over the surf and the sea
    for y in PIER_ROWS:
        for x in range(PIER_FROM, PIER_TO):
            if grid[y][x] != "#":
                grid[y][x] = "d"

    # The road, the spurs down into the car parks, and the car parks themselves
    for x in range(1, ROAD_END + 1):
        for y in ROAD_ROWS:
            grid[y][x] = "a"
    # Pavements run along both kerbs, where people walk. Only the road's crossings take them onto the tarmac.
    for x in range(1, ROAD_END + 1):
        for y in (ROAD_ROWS[0] - 1, ROAD_ROWS[1] + 1):
            if grid[y][x] in "gb":
                grid[y][x] = "w"
    for key, (x0, x1, y0, y1) in CAR_PARKS.items():
        # A lot is entered by its spur, from the main road above it, or from the south road below it for the south lots.
        # The common driveway runs along the edge where the spur comes in, so a parked car never blocks it.
        if key in SOUTH_LOTS:
            driveway, spur_rows = y1, range(y1 + 1, SOUTH_ROWS[0])
        else:
            driveway, spur_rows = y0, range(ROAD_ROWS[1] + 1, y0)
        for y in spur_rows:
            for x in SPURS[key]:
                grid[y][x] = "a"
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                grid[y][x] = "k"
        for x in range(x0, x1 + 1):
            grid[driveway][x] = "a"

    # The jetty out into the pond, from its southern shore
    for y in JETTY_ROWS:
        for x in JETTY_COLUMNS:
            grid[y][x] = "d"

    # The houses, on the grass across the road from the pond. Their models are built by the scenery module.
    for x0, y0, w, d in HOUSES:
        for y in range(y0, y0 + d):
            for x in range(x0, x0 + w):
                grid[y][x] = "h"

    # The shops: solid blocks with a door on the side that faces the road
    for kiosk in KIOSKS.values():
        x, y = kiosk["x"], kiosk["y"]
        grid[y][x] = grid[y][x + 1] = "C"  # The counter
        grid[y + 1][x] = grid[y + 1][x + 1] = "K"  # The kiosk's back, where the shopkeeper stands

    # The south road: a parallel road with its pavements, out of the cars' way and for people to walk along
    for x in range(1, ROAD_END + 1):
        for y in SOUTH_ROWS:
            grid[y][x] = "a"
        for y in (SOUTH_ROWS[0] - 1, SOUTH_ROWS[1] + 1):
            if grid[y][x] in "gb":
                grid[y][x] = "w"
    # The loop: a west link joins the south road to the main road, with a pavement for people beside the lane for cars,
    # and an east link runs up from the south road into the seafront car park
    for y in range(ROAD_ROWS[1] + 1, SOUTH_ROWS[0]):
        grid[y][2] = "w"
        grid[y][3] = "a"
    for y in range(18, SOUTH_ROWS[0]):
        grid[y][50] = grid[y][51] = "a"

    # Scatter trees and rocks on grass that is well clear of the paths, the water and the north part of the map
    for _ in range(420):
        x, y = rng.randrange(2, WIDTH - 2), rng.randrange(2, HEIGHT - 2)
        if grid[y][x] != "g" or (y <= ROAD_ROWS[1] + 13 and x < ROAD_END + 2):
            continue
        if CAMPSITE[0] <= x <= CAMPSITE[2] and CAMPSITE[1] <= y <= CAMPSITE[3]:
            continue
        if any(grid[y + dy][x + dx] != "g" for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            continue
        if any(abs(x - sx) < 3 and abs(y - sy) < 3 for sx, sy in list(SPOTS.values()) + list(NPC_TILES.values())):
            continue
        grid[y][x] = "t" if rng.random() < 0.6 else "#"
    return grid


class Level:
    def __init__(self, seed=7):
        self.grid = generate(seed)
        self.render = None
        self.stump_root = None
        self.blocked = set()  # Tiles people stand on, such as the NPC anglers, which walkers and the angler go round
        self.signals = None  # The traffic lights, set by the ambience. Without them every crossing is open
        self.snags = {"shore": set(), "boat": set()}  # Hidden stumps by zone, as tile coordinates
        self.roll_snags(random.Random(seed + 1))

    def roll_snags(self, rng):
        """Scatters the hidden stumps again, so each visit to the sea holds them in new places."""
        for zone in self.snags:
            tiles = [(x, y) for y in range(HEIGHT) for x in range(WIDTH) if WATER_ZONE.get(self.grid[y][x]) == zone]
            # Stumps sit in open water, away from the edge and the pier
            tiles = [t for t in tiles if all(self.tile(t[0] + dx, t[1] + dy) in WATER_ZONE for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
            self.snags[zone] = set(rng.sample(tiles, SNAG_PER_ZONE))
        self.place_stumps()

    def place_stumps(self):
        if self.render is None:
            return
        if self.stump_root:
            self.stump_root.removeNode()
        mesh = MeshBuilder()
        for tiles in self.snags.values():
            for x, y in tiles:
                mesh.box(x + 0.32, y + 0.32, -0.12, 0.36, 0.36, 0.62, STUMP)
        self.stump_root = mesh.build("stumps")
        self.stump_root.reparentTo(self.render)

    def tile(self, x, y):
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            return self.grid[y][x]
        return "#"

    def walkable(self, x, y):
        return self.tile(x, y) in WALKABLE and (x, y) not in self.blocked

    def water_zone(self, x, y):
        return WATER_ZONE.get(self.tile(x, y))

    def water_tiles(self, zone):
        return [(x, y) for y in range(HEIGHT) for x in range(WIDTH) if WATER_ZONE.get(self.grid[y][x]) == zone]

    def counters(self):
        """Each kiosk's counter, as the centre of its two tiles, with the tile in front of it where customers stand."""
        return {name: ((k["x"] + 1.0, k["y"] + 0.5), (k["x"], k["y"] - 1)) for name, k in KIOSKS.items()}

    def stand_beside(self, tile):
        """A walkable tile next to this one, for people who come over to talk to whoever stands on it. None if there is none."""
        x, y = tile
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            if self.walkable(x + dx, y + dy):
                return x + dx, y + dy
        return None

    def find_path(self, start, goal):
        """The walk for the angler. Returns the tiles after start."""
        return self.route(start, goal, self.walkable)

    def pedestrian(self, x, y):
        """Where people on foot may walk: pavements, grass, sand and the planks. The road is only for crossing at the crossings,
        and the spurs into the car parks are not for walking at all."""
        if self.tile(x, y) == "a":
            return x in CROSSING_COLUMNS and y in ROAD_ROWS + SOUTH_ROWS and self.walkable(x, y)
        return self.walkable(x, y)

    def is_crossing(self, tile):
        """A tile of road that people cross on: the road itself, in a crossing column."""
        x, y = tile
        return x in CROSSING_COLUMNS and y in ROAD_ROWS + SOUTH_ROWS and self.tile(x, y) == "a"

    def may_enter(self, who, tile):
        """Whether a traveller may step onto this tile now. A crossing is open to cars on green and to people on the walk light.
        Someone already on the crossing finishes crossing, so a light never stops them halfway over."""
        if self.signals is None or not self.is_crossing(tile) or self.is_crossing(who.tile_now):
            return True
        return self.signals.allows(who.vehicle)

    def find_walk(self, start, goal):
        """The walk for people on foot, who keep to the pavements. Returns the tiles after start."""
        return self.route(start, goal, self.pedestrian)

    def route(self, start, goal, passable, diagonal=True):
        """A* over the tiles that pass, moving in eight directions (or four, when not diagonal) but never cutting a corner.
        Returns the tiles after start."""
        start, goal = (int(start[0]), int(start[1])), (int(goal[0]), int(goal[1]))
        if start == goal or not passable(*goal):
            return []
        steps = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
        if not diagonal:
            steps = [(dx, dy) for dx, dy in steps if dx == 0 or dy == 0]  # Cars drive along the road, never diagonally
        best = {start: 0.0}
        came_from = {}
        heap = [(0.0, start)]
        while heap:
            _, node = heapq.heappop(heap)
            if node == goal:
                path = [node]
                while path[-1] in came_from:
                    path.append(came_from[path[-1]])
                return path[-2::-1]
            x, y = node
            for dx, dy in steps:
                nx, ny = x + dx, y + dy
                if not passable(nx, ny):
                    continue
                if dx and dy and not (passable(x + dx, y) and passable(x, y + dy)):
                    continue
                cost = best[node] + (math.sqrt(2) if dx and dy else 1.0)
                if cost < best.get((nx, ny), math.inf):
                    best[(nx, ny)] = cost
                    came_from[(nx, ny)] = node
                    dist_x, dist_y = abs(nx - goal[0]), abs(ny - goal[1])
                    estimate = max(dist_x, dist_y) + (math.sqrt(2) - 1) * min(dist_x, dist_y)
                    heapq.heappush(heap, (cost + estimate, (nx, ny)))
        return []

    def build(self, render):
        """The land, beach, roads, shops, pier and sea as lit meshes, with the posts. Grass, sand and the house plots fade into
        one another, the grass has tufts, and trees and rocks are rounded, so the place looks natural rather than blocky.
        The water is a separate see-through mesh."""
        self.render = render
        rng = random.Random(3)  # Own RNG so the colour variation is always the same
        tints = [[rng.uniform(0.92, 1.08) for _ in range(WIDTH)] for _ in range(HEIGHT)]
        mesh = MeshBuilder()
        water = MeshBuilder()

        def tint(x, y, tile=None):
            base = COLOURS.get(tile or self.grid[y][x], COLOURS["g"])
            return tuple(min(255, int(c * tints[y][x])) for c in base)

        def corner(cx, cy):
            """The colour at a grid corner: the average of the soft tiles that meet there, so the ground blends."""
            cols = [tint(x, y) for x in (cx - 1, cx) for y in (cy - 1, cy) if 0 <= x < WIDTH and 0 <= y < HEIGHT and self.grid[y][x] in SOFT]
            return tuple(sum(c[i] for c in cols) // len(cols) for i in range(3))

        for y in range(HEIGHT):
            for x in range(WIDTH):
                tile = self.grid[y][x]
                colour = tint(x, y)
                ground = [(x, y, 0), (x + 1, y, 0), (x + 1, y + 1, 0), (x, y + 1, 0)]

                if tile in SOFT:
                    mesh.quad(ground, (0, 0, 1), [corner(x, y), corner(x + 1, y), corner(x + 1, y + 1), corner(x, y + 1)])
                    if tile == "g":
                        self.grass_tufts(mesh, rng, x, y)
                elif tile == "#":
                    border = x in (0, WIDTH - 1) or y in (0, HEIGHT - 1)
                    mesh.quad(ground, (0, 0, 1), COLOURS["g"])
                    if border:
                        mesh.box(x + 0.1, y + 0.1, 0, 0.8, 0.8, 1.8, CLIFF)
                    else:
                        self.rock(mesh, rng, x, y)
                elif tile == "t":
                    mesh.quad(ground, (0, 0, 1), tint(x, y, "g"))
                    self.tree(mesh, rng, x, y)
                elif tile in WATER_ZONE:
                    water.quad([(x, y, -0.12), (x + 1, y, -0.12), (x + 1, y + 1, -0.12), (x, y + 1, -0.12)], (0, 0, 1), colour + (WATER_ALPHA,))
                    if any(self.tile(x + dx, y + dy) in WALKABLE for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        water.quad([(x + 0.08, y + 0.08, -0.1), (x + 0.92, y + 0.08, -0.1), (x + 0.92, y + 0.92, -0.1), (x + 0.08, y + 0.92, -0.1)], (0, 0, 1), FOAM + (255,))
                elif tile == "d":
                    shade = colour if x % 2 else tuple(int(c * 0.82) for c in colour)
                    mesh.quad([(x, y, 0.06), (x + 1, y, 0.06), (x + 1, y + 1, 0.06), (x, y + 1, 0.06)], (0, 0, 1), shade)
                    # Posts stand in the water at the corners of boards that have water beside them
                    if any(self.tile(x + dx, y + dy) in WATER_ZONE for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        for px, py in ((x + 0.1, y + 0.1), (x + 0.8, y + 0.8)):
                            mesh.box(px, py, -1.2, 0.14, 0.14, 1.3, POST)
                elif tile == "a":
                    mesh.quad(ground, (0, 0, 1), colour)
                    # Over the sea, the causeway stands on posts at its corners
                    if any(self.tile(x + dx, y + dy) in WATER_ZONE for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                        for px, py in ((x + 0.1, y + 0.1), (x + 0.8, y + 0.8)):
                            mesh.box(px, py, -1.2, 0.14, 0.14, 1.3, POST)
                    # A dashed centre line along the top row of the road
                    if y in (ROAD_ROWS[0], SOUTH_ROWS[0]) and x % 4 < 2:
                        mesh.quad([(x + 0.05, y + 0.9, 0.01), (x + 0.6, y + 0.9, 0.01), (x + 0.6, y + 1.0, 0.01), (x + 0.05, y + 1.0, 0.01)], (0, 0, 1), LINE)
                elif tile == "w":
                    mesh.quad(ground, (0, 0, 1), colour)
                    # Joints between the paving slabs
                    mesh.quad([(x + 0.97, y, 0.005), (x + 1.0, y, 0.005), (x + 1.0, y + 1, 0.005), (x + 0.97, y + 1, 0.005)], (0, 0, 1), (96, 92, 86))
                elif tile == "k":
                    mesh.quad(ground, (0, 0, 1), colour)
                    # Bay lines, one at each bay's edge
                    if x % 3 == 0:
                        mesh.quad([(x + 0.02, y + 0.02, 0.01), (x + 0.08, y + 0.02, 0.01), (x + 0.08, y + 0.98, 0.01), (x + 0.02, y + 0.98, 0.01)], (0, 0, 1), LINE)
                elif tile in ("C", "K"):
                    # Kiosk counters and backs block movement. Their models are built by the kiosks module.
                    mesh.quad(ground, (0, 0, 1), COLOURS["g"])
                else:
                    mesh.quad(ground, (0, 0, 1), colour)

        land = mesh.build("level")
        land.reparentTo(render)
        water_node = water.build("water", transparent=True)
        water_node.reparentTo(render)
        water_node.setDepthWrite(False)  # Water does not hide what is under it
        self.place_stumps()
        return water_node

    def grass_tufts(self, mesh, rng, x, y):
        """A few blades of grass on a grass tile, so the lawn is not a flat sheet."""
        for _ in range(2):
            if rng.random() < 0.4:
                u, v = rng.uniform(0.15, 0.85), rng.uniform(0.15, 0.85)
                lean = rng.uniform(-0.07, 0.07)
                mesh.triangle_both((x + u - 0.03, y + v, 0), (x + u + 0.03, y + v, 0), (x + u + lean, y + v, rng.uniform(0.12, 0.22)),
                                   rng.choice(TUFTS))

    def rock(self, mesh, rng, x, y):
        """A rounded boulder, with a smaller stone beside it."""
        mesh.ellipsoid(x + 0.5, y + 0.5, 0.3, 0.42, 0.36, 0.3, rng.choice(ROCK_SHADES), steps=5)
        mesh.ellipsoid(x + 0.22, y + 0.7, 0.18, 0.2, 0.18, 0.16, rng.choice(ROCK_SHADES), steps=4)

    def tree(self, mesh, rng, x, y):
        """A slim trunk under a rounded crown made of two overlapping ellipsoids, so it does not read as a box."""
        canopy = rng.choice(CANOPIES)
        mesh.box(x + 0.44, y + 0.44, 0, 0.12, 0.12, 1.1, TRUNK)
        mesh.ellipsoid(x + 0.5, y + 0.5, 1.5, 0.5, 0.48, 0.55, canopy, steps=6)
        lighter = tuple(min(255, c + 14) for c in canopy)
        mesh.ellipsoid(x + 0.5 + rng.uniform(-0.2, 0.2), y + 0.5 + rng.uniform(-0.2, 0.2), 1.15, 0.34, 0.32, 0.36, lighter, steps=4)
