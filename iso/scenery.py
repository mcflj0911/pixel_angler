"""Things that make the place feel lived in: lamps, benches and bins on the grass beside the pavements, flower beds, beach
umbrellas, boats moored off the pier, and the rowing boat the angler hires. The fixed pieces are built into one mesh.
The moored boats bob on the water. Scenery only decorates, so it never blocks anyone walking."""
import math
import random

from iso.level import CANOPIES, CROSSING_COLUMNS, HEIGHT, HOUSES, LINE, PLAYGROUND, ROAD_END, ROAD_ROWS, SOUTH_ROWS, TRUNK, WIDTH, coast
from iso.mesh import MeshBuilder

POST = (60, 60, 66)
LAMP = (255, 236, 170)
BENCH = (120, 84, 56)
BENCH_LEG = (70, 70, 76)
BIN = (46, 70, 60)
PETALS = [(230, 80, 120), (250, 200, 70), (240, 240, 245), (170, 110, 230)]
LEAF = (60, 110, 60)
UMBRELLA = [(230, 70, 60), (240, 240, 235), (60, 150, 200)]
PLAY = [(230, 80, 60), (250, 200, 70), (60, 150, 200)]  # Swing seats, and the platform
CHAIN = (150, 150, 160)
NORTH_TREES = [(39, 2), (43, 1), (47, 3), (51, 2), (41, 3)]  # Trees on the north lawn, east of the playground
WALLS = [(236, 224, 200), (222, 190, 160), (214, 226, 214)]  # Cream, brick and sage walls
ROOFS = [(150, 62, 50), (96, 92, 104), (146, 96, 60)]
BRICK = (170, 80, 64)
GLASS = (160, 200, 220)
DOOR = (104, 70, 48)
TRIM_WHITE = (240, 236, 224)
TENT = (196, 168, 96)
STONE = (120, 116, 110)
LOG = (100, 70, 44)
FLAME = (250, 150, 50)
WOOD = (150, 112, 74)
REED = (96, 120, 64)
REED_HEAD = (120, 80, 50)
HULL = (150, 100, 60)
TRIM = (240, 236, 224)
SEAT = (110, 74, 44)
MOORED = [(200, 60, 50), (60, 120, 190), (240, 240, 235)]
MOORING = (60.5, 26.5)  # Where the rowing boat lies moored, in the sea just off the pier's foot
MOORED_SPOTS = [(62, 20), (65, 36)]  # Fishing boats moored in the sea, as tiles


def build_rowboat(render):
    """A rowing boat, built along +x with the bow forward. Returns its node and the mooring spot it lies at until it is used."""
    mesh = MeshBuilder()
    mesh.box(-0.6, -0.32, 0.0, 1.2, 0.64, 0.12, HULL)  # The floor
    mesh.box(-0.6, -0.36, 0.0, 1.2, 0.04, 0.32, TRIM)  # The sides
    mesh.box(-0.6, 0.32, 0.0, 1.2, 0.04, 0.32, TRIM)
    mesh.triangle_both((0.6, -0.36, 0.32), (0.6, 0.36, 0.32), (1.0, 0.0, 0.2), TRIM)  # The pointed bow
    mesh.box(-0.2, -0.3, 0.12, 0.4, 0.6, 0.08, SEAT)  # The seat
    node = mesh.build("rowboat")
    node.reparentTo(render)
    return node, MOORING


def moored_boat(render, x, y, colour, rng):
    """A small fishing boat at anchor, with a cabin and a rail. It bobs, so it is returned as its own node."""
    mesh = MeshBuilder()
    mesh.box(-1.0, -0.45, 0.0, 2.0, 0.9, 0.28, colour)  # The hull
    mesh.box(-0.2, -0.3, 0.28, 0.8, 0.6, 0.45, TRIM)  # The cabin
    mesh.box(-1.0, -0.47, 0.28, 2.0, 0.04, 0.05, TRIM)  # The rail
    node = mesh.build("moored")
    node.reparentTo(render)
    node.setPos(x + 0.5, y + 0.5, -0.12)
    node.setH(rng.uniform(-20, 20))
    return node


class Scenery:
    """The static scenery, and the boats that bob at their moorings."""

    def __init__(self, render, level):
        self.bobbers = []  # (node, phase): the moored boats
        self.lamp_tiles = []  # Where the lamp posts stand, so their glow can be placed
        self.benches = []  # Where the benches are, as (x, y) centres, for the angler to sit on
        self.deckchairs = []  # Where the deckchairs are, as (x, y) centres, for anyone to sit on
        self.level = level
        rng = random.Random(21)  # Own RNG, so the flowers are always in the same places
        mesh = MeshBuilder()
        self.lamps(mesh, rng)
        self.build_glows(render)
        self.flowers(mesh, rng)
        self.umbrellas(mesh)
        self.playground(mesh)
        self.trees(mesh)
        self.crossings(mesh)
        self.houses(mesh)
        self.campsite(mesh)
        mesh.build("scenery").reparentTo(render)
        for (x, y), colour in zip(MOORED_SPOTS, MOORED):
            if level.tile(x, y) == "o":  # Only out on open water
                self.bobbers.append((moored_boat(render, x, y, colour, rng), rng.uniform(0, math.tau)))
                for dx in (-1, 0, 1):  # The hull is about three tiles long, so it takes up three
                    self.block(x + dx, y)

    def lamps(self, mesh, rng):
        """Lamp posts, benches and bins on the grass just beyond the pavements, so they never block the walk."""
        rows = (ROAD_ROWS[0] - 2, ROAD_ROWS[1] + 2, SOUTH_ROWS[0] - 2, SOUTH_ROWS[1] + 2)  # One row beyond each pavement, on the grass
        for y in rows:
            for x in range(4, ROAD_END - 2, 7):
                if self.level.tile(x, y) != "g":
                    continue
                self.lamp_tiles.append((x, y))
                mesh.box(x + 0.45, y + 0.45, 0, 0.1, 0.1, 2.0, POST)  # The post
                mesh.box(x + 0.3, y + 0.3, 2.0, 0.4, 0.4, 0.15, LAMP)  # The lamp
                self.block(x, y)
            for x in range(rng.randrange(3, 8), ROAD_END - 2, 11):
                if self.level.tile(x, y) == "g" and self.level.tile(x + 1, y) == "g":
                    self.bench(mesh, x, y, facing_north=self.road_is_north(y))
                if self.level.tile(x + 4, y) == "g":
                    mesh.box(x + 4.3, y + 0.3, 0, 0.3, 0.3, 0.5, BIN)  # A bin beside the bench
                    self.block(x + 4, y)

    def flowers(self, mesh, rng):
        """Flower beds scattered over the open grass, away from trees and the water."""
        placed = 0
        for _ in range(900):
            x, y = rng.randrange(2, WIDTH - 2), rng.randrange(2, HEIGHT - 2)
            if self.level.tile(x, y) != "g" or any(self.level.tile(x + dx, y + dy) in "t#" for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                continue
            # A clump of leaves with a few round flower heads on top
            cx, cy = x + 0.5, y + 0.5
            mesh.ellipsoid(cx, cy, 0.06, 0.34, 0.34, 0.08, LEAF, steps=3)
            for _ in range(3):
                mesh.ellipsoid(cx + rng.uniform(-0.25, 0.25), cy + rng.uniform(-0.25, 0.25), 0.16, 0.09, 0.09, 0.09,
                               rng.choice(PETALS), steps=3)
            placed += 1
            if placed >= 70:
                break

    def umbrellas(self, mesh):
        """Parasols on the beach: a pole, and a round canopy in stripes, with a point at the top."""
        for y in (18, 24, 30, 36, 42):  # Rows that are not sand are skipped, such as the pier's
            x = coast(y) - 2
            if self.level.tile(x, y) == "b":
                colour = UMBRELLA[y % len(UMBRELLA)]
                cx, cy = x + 0.5, y + 0.5
                mesh.box(cx - 0.025, cy - 0.025, 0, 0.05, 0.05, 1.4, POST)
                rim = [(cx + 0.85 * math.cos(i * math.tau / 8), cy + 0.85 * math.sin(i * math.tau / 8), 1.3) for i in range(8)]
                for i in range(8):
                    stripe = colour if i % 2 else TRIM_WHITE
                    mesh.triangle_both((cx, cy, 1.5), rim[i], rim[(i + 1) % 8], stripe)
                self.block(x, y)
                # A deckchair beside the parasol, with its back to the sea
                self.deckchairs.append((cx + 1.35, cy - 0.05))
                mesh.box(cx + 0.9, cy - 0.3, 0.12, 0.9, 0.5, 0.06, colour)
                mesh.box(cx + 0.9, cy - 0.32, 0.12, 0.06, 0.5, 0.4, TRIM_WHITE)

    def playground(self, mesh):
        """A small playground on the north lawn: a swing frame with two swings on chains, and a slide down from a platform.
        It is decoration only, and children play on it while their grown-up stands by."""
        x0, y0, _, _ = PLAYGROUND
        for x in (x0 + 0.6, x0 + 3.6):  # The swing frame's posts, and the bar between them
            mesh.box(x, y0 + 1.2, 0, 0.1, 0.1, 2.0, POST)
        mesh.box(x0 + 0.6, y0 + 1.2, 2.0, 3.1, 0.1, 0.1, POST)
        for i, x in enumerate((x0 + 1.2, x0 + 2.8)):
            mesh.box(x, y0 + 1.25, 1.0, 0.03, 0.03, 1.0, CHAIN)
            mesh.box(x - 0.15, y0 + 1.1, 0.85, 0.3, 0.2, 0.05, PLAY[i])
        # The platform, with its four posts, and the slide running down from its far edge to the grass
        mesh.box(x0 + 5.0, y0 + 0.6, 0.85, 1.2, 1.0, 0.08, PLAY[1])
        for px in (x0 + 5.0, x0 + 6.1):
            for py in (y0 + 0.6, y0 + 1.5):
                mesh.box(px, py, 0, 0.08, 0.08, 0.85, POST)
        mesh.quad([(x0 + 6.2, y0 + 0.7, 0.9), (x0 + 6.2, y0 + 1.5, 0.9), (x0 + 7.4, y0 + 1.5, 0.0), (x0 + 7.4, y0 + 0.7, 0.0)],
                  (0.6, 0, 0.8), PLAY[2])

    def trees(self, mesh):
        """A few trees on the north lawn, so the open grass has some shade and the walk has things to go round."""
        rng = random.Random(55)  # Own RNG, so the crowns are always the same
        for x, y in NORTH_TREES:
            if self.level.tile(x, y) != "g":
                continue
            cx, cy = x + 0.5, y + 0.5
            mesh.box(cx - 0.08, cy - 0.08, 0, 0.16, 0.16, 1.1, TRUNK)
            mesh.ellipsoid(cx, cy, 2.0, 0.85, 0.85, 0.9, rng.choice(CANOPIES), steps=5)
            self.block(x, y)

    def crossings(self, mesh):
        """White zebra stripes across each crossing. They run with the traffic, so people walk across the stripes, on the road only."""
        for x in CROSSING_COLUMNS:
            for y in ROAD_ROWS + SOUTH_ROWS:
                if self.level.tile(x, y) != "a":
                    continue
                for k in range(4):
                    mesh.box(x + 0.08, y + 0.08 + k * 0.22, 0.02, 0.84, 0.1, 0.02, LINE)

    def campsite(self, mesh):
        """A camping spot beyond the pond: a tent, a fire ring with its logs, a picnic table, and reeds along the pond's edge."""
        rng = random.Random(44)
        # The tent, a four-sided pyramid with its door facing the fire
        cx, cy = 5.5, 36.5
        base = [(cx - 0.45, cy - 0.45, 0), (cx + 0.45, cy - 0.45, 0), (cx + 0.45, cy + 0.45, 0), (cx - 0.45, cy + 0.45, 0)]
        apex = (cx, cy, 1.0)
        for i in range(4):
            mesh.triangle_both(apex, base[i], base[(i + 1) % 4], TENT)
        self.block(5, 36)
        # The fire ring of stones, the logs and the flames
        fx, fy = 7.5, 37.5
        for i in range(6):
            a = i * math.tau / 6
            mesh.ellipsoid(fx + 0.35 * math.cos(a), fy + 0.35 * math.sin(a), 0.07, 0.1, 0.1, 0.07, STONE, steps=3)
        mesh.box(fx - 0.2, fy - 0.05, 0.05, 0.4, 0.1, 0.08, LOG)
        mesh.box(fx - 0.05, fy - 0.2, 0.05, 0.1, 0.4, 0.08, LOG)
        mesh.ellipsoid(fx, fy, 0.22, 0.14, 0.14, 0.2, FLAME, steps=3)
        self.block(7, 37)
        # A picnic table on its legs
        tx, ty = 5.6, 38.5  # Off the car link at column 3, which runs through here
        mesh.box(tx - 0.5, ty - 0.3, 0.7, 1.0, 0.6, 0.06, WOOD)
        for lx in (-0.42, 0.36):
            for ly in (-0.2, 0.12):
                mesh.box(tx + lx, ty + ly, 0, 0.06, 0.06, 0.7, WOOD)
        self.block(5, 38)
        # Reeds standing in the grass at the pond's edge, with brown heads on them
        for y in range(19, 32):
            for x in range(4, 24):
                if self.level.tile(x, y) == "g" and any(self.level.tile(x + dx, y + dy) == "p" for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    if rng.random() < 0.35:
                        rx, ry = x + rng.uniform(0.2, 0.8), y + rng.uniform(0.2, 0.8)
                        mesh.box(rx, ry, 0, 0.04, 0.04, rng.uniform(0.8, 1.2), REED)
                        mesh.box(rx - 0.02, ry - 0.02, 0.9, 0.08, 0.08, 0.2, REED_HEAD)

    def houses(self, mesh):
        """Houses across the road from the pond, with pitched roofs, a chimney, windows and a door on the side that faces the camera.
        Each house is solid, so people walk round it."""
        for i, (x0, y0, w, d) in enumerate(HOUSES):
            wall, roof = WALLS[i % len(WALLS)], ROOFS[i % len(ROOFS)]
            mesh.box(x0 + 0.02, y0 + 0.02, 0, w - 0.04, d - 0.04, 1.5, wall)
            ridge_y, ridge_z = y0 + d / 2, 2.6
            # Two sloping roof planes, meeting at the ridge and overhanging the walls a little
            mesh.quad([(x0 - 0.2, ridge_y, ridge_z), (x0 + w + 0.2, ridge_y, ridge_z), (x0 + w + 0.2, y0 + d + 0.2, 1.5),
                       (x0 - 0.2, y0 + d + 0.2, 1.5)], (0, 0.6, 0.8), roof)
            mesh.quad([(x0 - 0.2, ridge_y, ridge_z), (x0 - 0.2, y0 - 0.2, 1.5), (x0 + w + 0.2, y0 - 0.2, 1.5),
                       (x0 + w + 0.2, ridge_y, ridge_z)], (0, -0.6, 0.8), roof)
            # Gable ends, filled in with the wall colour
            mesh.triangle_both((x0, y0, 1.5), (x0, y0 + d, 1.5), (x0, ridge_y, ridge_z), wall)
            mesh.triangle_both((x0 + w, y0, 1.5), (x0 + w, y0 + d, 1.5), (x0 + w, ridge_y, ridge_z), wall)
            mesh.box(x0 + w * 0.7, ridge_y - 0.25, 2.2, 0.3, 0.3, 0.9, BRICK)  # Chimney
            # The face that looks north-west to the camera: a door and a window on the west wall, and two windows on the north
            mesh.box(x0 - 0.03, y0 + d * 0.62, 0, 0.05, 0.6, 1.0, DOOR)
            mesh.box(x0 - 0.03, y0 + d * 0.2, 0.75, 0.05, 0.6, 0.5, GLASS)
            for frac in (0.25, 0.7):
                mesh.box(x0 + w * frac, y0 - 0.03, 0.75, 0.5, 0.05, 0.5, GLASS)
                mesh.box(x0 + w * frac - 0.03, y0 - 0.05, 0.7, 0.56, 0.02, 0.06, TRIM_WHITE)  # Sill

    def road_is_north(self, y):
        """Whether the road nearest to a bench at row y lies to its north (lower y), so the bench faces north."""
        nearest = min(ROAD_ROWS + SOUTH_ROWS, key=lambda row: abs(row - y))
        return nearest < y

    def bench(self, mesh, x, y, facing_north):
        """A bench with four legs, a seat and a back. The seat faces the road, so the back is on the side away from it."""
        mesh.box(x + 0.1, y + 0.3, 0.42, 0.8, 0.4, 0.06, BENCH)  # The seat
        for lx in (0.14, 0.84):
            for ly in (0.34, 0.62):
                mesh.box(x + lx - 0.03, y + ly - 0.03, 0, 0.06, 0.06, 0.42, BENCH_LEG)  # The legs
        back_y = y + 0.62 if facing_north else y + 0.22  # The back is on the far side from the road
        mesh.box(x + 0.1, back_y, 0.48, 0.8, 0.08, 0.5, BENCH)
        self.benches.append((x + 0.5, y + 0.5))
        self.block(x, y)

    def build_glows(self, render):
        """The light round each lamp: a soft glow up at the lamp, and a pool on the ground. It is see-through and faded out by day."""
        glows = MeshBuilder()
        for x, y in self.lamp_tiles:
            glows.ellipsoid(x + 0.5, y + 0.5, 2.1, 0.4, 0.4, 0.32, (255, 222, 150, 130), steps=5)
            glows.ellipsoid(x + 0.5, y + 0.5, 0.05, 0.95, 0.95, 0.03, (255, 210, 130, 70), steps=6)
        self.glow = glows.build("lamp_glow", transparent=True)
        self.glow.reparentTo(render)
        self.glow.setDepthWrite(False)
        self.glow.setAlphaScale(0.0)

    def set_night(self, amount):
        """Shows the lamps' light by the amount of night, from 0 in the day to 1 at full night."""
        self.glow.setAlphaScale(amount)

    def block(self, x, y):
        """Solid things block the tile they stand on, so people and boats go round them."""
        self.level.blocked.add((int(x), int(y)))

    def update(self, dt, frame):
        for node, phase in self.bobbers:
            node.setZ(-0.12 + math.sin(frame * 0.05 + phase) * 0.03)
            node.setR(math.sin(frame * 0.04 + phase) * 2.0)


def build_scenery(render, level):
    return Scenery(render, level)
