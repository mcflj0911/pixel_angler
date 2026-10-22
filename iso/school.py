import math
import random

from fish import spawn_random_fish
from iso.fish_model import TILE_PX, build_fish

FISH_PER_ZONE = 4  # Fish swimming in each water area at once
WATER_TOP = 120  # Depths are absolute, as they were on the side-view screen, so the numbers carry over
HEIGHT = 600
WATER_Z = -0.12  # Height of the water surface in the world
DEPTH_SCALE = 0.25 / TILE_PX  # World units of height per pixel of depth below the surface
TURN = 0.04  # How quickly a fish eases from one speed to another, per frame. Small, so turns look graceful
WANDER_FRAMES = (240, 720)  # Frames a fish swims to one spot before it picks another: 4 to 12 seconds
SPOT_RANGE = 10  # Tiles a fish looks within for its next spot, so it explores its own corner of the water before moving on
PLAY_RANGE = 6  # Tiles within which a fish of its own kind is close enough to play with
PLAY_CHANCE = 0.35  # Chance that a fish picking its next spot plays chase with a close fish of its kind instead
PLAY_FRAMES = (60, 180)  # How long a game of chase lasts, in frames
TAIL_RATE = 0.2  # Radians of tail wag per frame, before the speed of the fish


def frames(dt):
    """Seconds as frames at 60 a second, so the numbers from the side-view game still apply."""
    return dt * 60


class School:
    """The fish swimming in each water area.
    A swimmer is a dict: its fish, zone, tile position x and y, depth (pixels below the surface, as the side view had it),
    direction along x, its speed along x, the depth it is easing towards, and its model parts.
    Fish wander about their own water, choosing spots to swim to, and play chase with their own kind. They rise and dive
    smoothly, and wag their tails and flap their fins as they go."""

    def __init__(self, render, level, economy, weather):
        self.render = render
        self.level = level
        self.economy = economy
        self.weather = weather
        self.water = {zone: level.water_tiles(zone) for zone in ("pond", "shore", "boat")}
        self.swimmers = []
        for zone in self.water:
            for _ in range(FISH_PER_ZONE):
                self.add(zone)

    def add(self, zone):
        fish = spawn_random_fish(zone, self.economy.stats())  # Rarer species only swim in once the tackle can land them
        x, y = random.choice(self.water[zone])
        root, tail, fins, sail = build_fish(self.render, fish)
        swimmer = {
            "zone": zone, "fish": fish, "x": x + 0.5, "y": y + 0.5, "depth": random.randint(*fish.depth_range),
            "dir": 1 if fish.speed >= 0 else -1, "vx": 0.0, "goal": None, "phase": random.uniform(0, math.tau),
            "node": root, "tail": tail, "fins": fins, "sail": sail, "thrash": 0.0,
            "vy": 0.0, "goal_x": x + 0.5, "goal_y": y + 0.5, "wander": 0.0,
        }
        swimmer["goal"] = swimmer["depth"]
        self.swimmers.append(swimmer)
        self.place(swimmer)

    def release(self, swimmer):
        swimmer["node"].removeNode()
        if swimmer in self.swimmers:
            self.swimmers.remove(swimmer)

    def swim(self, dt, skip=None):
        """Every fish swims in its own area. The swimmer in skip is pinned to the lure, so it only wags its tail."""
        step = frames(dt)
        mods = self.weather.mods_for_fish()
        for s in self.swimmers:
            s["phase"] += step * TAIL_RATE
            if s is skip:
                s["vx"] *= 0.9 ** step
                self.place(s)
                continue
            fish = s["fish"]
            pace = fish.pace()
            self.explore(s, step, pace, mods)
            self.dive(s, step, pace, mods)
            self.place(s)

    def explore(self, s, step, pace, mods):
        """Swims to a spot in its own water, eases up to speed on the way, and settles into a new swim when it arrives.
        Over time a fish covers its whole area: round the reeds, out to the middle and back to the edge."""
        s["wander"] -= step
        if s["wander"] <= 0 or math.hypot(s["goal_x"] - s["x"], s["goal_y"] - s["y"]) < 0.3:
            self.pick_spot(s)
        speed = abs(s["fish"].speed) * mods["speed"] * pace / TILE_PX  # Tiles a frame
        dx, dy = s["goal_x"] - s["x"], s["goal_y"] - s["y"]
        dist = math.hypot(dx, dy)
        want_x, want_y = (dx / dist * speed, dy / dist * speed) if dist > 1e-6 else (0.0, 0.0)
        s["vx"] += (want_x - s["vx"]) * min(1.0, TURN * step)
        s["vy"] += (want_y - s["vy"]) * min(1.0, TURN * step)
        nx, ny = s["x"] + s["vx"] * step, s["y"] + s["vy"] * step
        if self.level.water_zone(int(nx), int(ny)) == s["zone"]:
            s["x"], s["y"] = nx, ny
        else:
            # At the edge of the water the fish stops and picks a spot back out in the open
            s["vx"] = s["vy"] = 0.0
            self.pick_spot(s)
        if abs(s["vx"]) > 1e-4:
            s["dir"] = 1 if s["vx"] > 0 else -1

    def pick_spot(self, s):
        """Chooses where to swim next: a game of chase with a fish of its own kind close by, now and then, or a spot a few
        tiles away in its own area."""
        s["wander"] = random.uniform(*WANDER_FRAMES)
        mates = [o for o in self.swimmers if o is not s and o["zone"] == s["zone"] and o["fish"].name == s["fish"].name
                 and math.hypot(o["x"] - s["x"], o["y"] - s["y"]) < PLAY_RANGE]
        if mates and random.random() < PLAY_CHANCE:
            mate = random.choice(mates)
            x, y = mate["x"] + random.uniform(-1.5, 1.5), mate["y"] + random.uniform(-1.5, 1.5)
            if self.level.water_zone(int(x), int(y)) == s["zone"]:
                s["goal_x"], s["goal_y"] = x, y
                s["wander"] = random.uniform(*PLAY_FRAMES)  # A short game, not a long swim
                return
        candidates = random.sample(self.water[s["zone"]], min(80, len(self.water[s["zone"]])))
        near = [(x, y) for x, y in candidates if math.hypot(x + 0.5 - s["x"], y + 0.5 - s["y"]) <= SPOT_RANGE]
        tx, ty = random.choice(near or candidates)
        s["goal_x"], s["goal_y"] = tx + 0.5, ty + 0.5

    def dive(self, s, step, pace, mods):
        """Picks a new depth to swim at now and then, within the layer this fish likes, and eases towards it."""
        fish = s["fish"]
        fish.zig_timer -= step
        top, bottom = fish.depth_range
        top, bottom = max(WATER_TOP + 20, top + mods["depth"]), min(HEIGHT - 40, bottom + mods["depth"])
        if fish.zig_timer <= 0:
            s["goal"] = random.uniform(top, bottom)
            fish.zig_timer = random.randint(*fish.zig_frames)
        move = fish.zig_speed * mods["speed"] * pace * step
        delta = s["goal"] - s["depth"]
        if abs(delta) <= move:
            s["depth"] = s["goal"]
        else:
            s["depth"] += math.copysign(move, delta)
        s["depth"] = min(bottom, max(top, s["depth"]))

    def place(self, s):
        """Puts the model at its tile, facing the way it swims. Its depth sets how far below the surface it sits.
        The body sways a little, the tail wags harder the faster the fish moves, and the fins flap."""
        depth = max(0.0, s["depth"] - WATER_TOP)
        s["node"].setPos(s["x"], s["y"], WATER_Z - depth * DEPTH_SCALE)
        # Light fades with depth: a fish near the top shows its true colours, and a deep one turns darker and bluer
        t = min(1.0, depth / (HEIGHT - WATER_TOP))
        s["node"].setColorScale(1 - 0.5 * t, 1 - 0.35 * t, 1 - 0.12 * t, 1)
        sway = math.sin(s["phase"]) * 4
        s["node"].setH((0 if s["dir"] > 0 else 180) + sway)
        speed = min(1.0, abs(s["vx"]) * TILE_PX / 4)
        thrash = s["thrash"]  # A hooked fish thrashes: its tail beats hard, and its body rolls as it fights
        s["tail"].setH(math.sin(s["phase"] * 2) * (12 + 20 * speed + 40 * thrash))
        s["node"].setR(math.sin(s["phase"] * 2.5) * 10 * thrash)
        for i, pivot in enumerate(s["fins"]):
            pivot.setP(math.sin(s["phase"] * 1.5 + i * math.pi) * 14)
        if s["sail"] is not None:
            s["sail"].setScale(1, 1, 1.5 if s["fish"].dash_ticks else 1)  # The sailfish raises its sail when it bursts

    def near(self, swimmer, lure):
        """Whether a swimmer is close enough to the lure to be tempted: within a tile across, and near its depth."""
        return abs(swimmer["x"] - lure["x"]) * TILE_PX < 40 and abs(swimmer["y"] - lure["y"]) < 1 and abs(swimmer["depth"] - lure["depth"]) < 30
