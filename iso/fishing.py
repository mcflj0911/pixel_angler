import math
import random

from panda3d.core import LineSegs

from iso.fight import SNAG_COOLDOWN, Fight, Snag
from iso.fish_model import TILE_PX
from iso.mesh import MeshBuilder
from iso.school import WATER_TOP, WATER_Z, School

# Hook states, as in the side-view game
IDLE = "IDLE"
CHARGING = "CHARGING"
CASTING = "CASTING"
IN_WATER = "IN_WATER"
HOOKSET = "HOOKSET"
FIGHTING = "FIGHTING"
RETRACTING = "RETRACTING"
SNAGGED = "SNAGGED"

AREA_INFO = {
    "pond": {"name": "Pond", "lure": "Worm"},
    "shore": {"name": "Shore", "lure": "Paddletail"},
    "boat": {"name": "Open Sea", "lure": "Metal Micro Jig"},
}
ZONE_NAMES = {"pond": "pond", "shore": "beach", "boat": "open sea"}

# Casting power: the meter sweeps up and down, and releasing locks in the power. Distances are in pixels, 40 to a tile.
POWER_FRAMES = 60  # One full sweep of the meter
ACCURACY_TOLERANCE = 0.03  # How close the meter must be to the target power to land on it
MIN_CAST_DISTANCE = 60
MAX_CAST_DISTANCE = 320
CAST_FRAMES = 48  # Length of the whole cast, wind-up to landing
CAST_RELEASE = 0.6  # Fraction of the cast where the line leaves the rod
LANDING_DEPTH = WATER_TOP + 30  # Depth the lure lands at, as an absolute reading
LURE_TOP = WATER_TOP + 4  # Reeling past this brings the lure back to the bank
BANK_DEPTH = WATER_TOP + 25  # The lure is back at the rod at this depth
MAX_DEPTH = 600 - 15  # The lure cannot sink below this
POND_LAYERS = {"Top": 190, "Middle": 300, "Bottom": 420}  # Depths the pond bait can be held at
NIBBLE_FRAMES = 30  # Pond: gap between the small nibbles before the big dip
RHYTHM_FRAMES = 40  # Open sea: how close taps of the rod must be to count as one rhythm
SURFACE_Y = 260  # Sea depth layers: above this is Surface, up to MID_Y is Mid, below is Deep
MID_Y = 400
DEPTH_PER_METRE = 11  # How many pixels of water make up one metre on the depth readout
ATTRACT_RANGE = 160  # Scent pulls in fish this close to the lure
SNAG_CHANCE = 0.015  # Per frame the lure sits over a stump, about 1 pass in 7 snags
SNAG_RANGE_X, SNAG_RANGE_Y = 22, 15  # Pixels either side of a stump that can catch the lure

# Hookset: a bite shows WAIT, then GO and the ring starts shrinking
HOOKSET_WAIT = 40
HOOKSET_FRAMES = 80  # The ring takes this long to shrink onto its target, so there is time to see it and click
HOOKSET_RING_START = 60
HOOKSET_RING_TARGET = 20
HOOKSET_WINDOW = 7  # Radius pixels either side of the target that count as a good hookset

LINE_COLOUR = (0.93, 0.93, 0.92, 1)
RING_FRAMES = 28  # How long a splash ripple lasts


def clamp(value, low, high):
    return max(low, min(high, value))


def frames(dt):
    return dt * 60


def lure_models(render):
    """One lure model per area: a worm, a paddletail, or a metal jig. Only the current area's is shown."""
    lures = {}
    worm = MeshBuilder()
    worm.ellipsoid(0, 0, -0.5, 0.06, 0.06, 0.25, (240, 120, 140), steps=5)
    worm.box(-0.02, -0.02, 0.08, 0.04, 0.04, 0.2, (176, 180, 190))  # Hook
    lures["pond"] = worm.build("worm")
    lures["pond"].reparentTo(render)

    tail = MeshBuilder()
    tail.ellipsoid(0, 0, -0.1, 0.12, 0.12, 0.12, (244, 170, 200), steps=5)
    tail.triangle((0, 0, -0.1), (-0.12, 0, -0.45), (0.12, 0, -0.45), (244, 170, 200))
    tail.ellipsoid(0, 0, 0.1, 0.1, 0.1, 0.1, (200, 205, 215), steps=5)
    lures["shore"] = tail.build("paddletail")
    lures["shore"].reparentTo(render)

    jig = MeshBuilder()
    jig.box(-0.1, -0.1, -0.35, 0.2, 0.2, 0.5, (200, 205, 215))
    jig.box(-0.05, -0.05, -0.55, 0.1, 0.1, 0.2, (210, 60, 50))
    lures["boat"] = jig.build("jig")
    lures["boat"].reparentTo(render)
    for node in lures.values():
        node.hide()
    return lures


def float_model(render):
    """The float for the pond: a round bobber, red on top and white underneath. It is a plain ball with no stalk, so it reads as a float."""
    mesh = MeshBuilder()
    mesh.ellipsoid(0, 0, -0.02, 0.12, 0.12, 0.1, (240, 240, 240), steps=6)  # The white underside, sitting in the water
    mesh.ellipsoid(0, 0, 0.04, 0.12, 0.12, 0.09, (220, 60, 60), steps=6)  # The red top, a rounded ball on the white
    node = mesh.build("float")
    node.reparentTo(render)
    node.hide()
    return node


class Fishing:
    """The fishing side of the game: the cast meter, each area's lure and strikes, the hookset, the fight, snags and the retrieve.
    The rules are the side-view game's. Depth is kept in the same absolute pixels (40 to a tile), so the numbers carry over."""

    def __init__(self, render, level, economy, weather, audio):
        self.render = render
        self.level = level
        self.economy = economy
        self.weather = weather
        self.audio = audio
        self.school = School(render, level, economy, weather)
        self.area = "pond"
        self.state = IDLE
        self.frame = 0.0  # Frames since the game started, which drives the float's bob and the animations
        self.events = []  # Messages for the HUD, cleared each frame by the game
        self.line_hp = 100.0  # The line's condition, 0 snaps it. Frays in fights and snags, mended by restringing
        self.scent_next = False  # Set by the F key, so the next cast uses a scent
        self.scented = False  # Whether this cast used an attractant
        self.clutch = 1.0  # Drag setting, from 0.4 to 2.0
        self.cooldown = 0.0  # Seconds left before the lure can snag again
        self.splash = 0.0  # Frames left on the ripple from a cast
        self.session_value = 0  # What the angler has landed this visit, in dollars
        self.reel_clicks = 0

        # The lure: its tile position and absolute depth. origin is where the angler stands, in tiles.
        self.lure = {"x": 0.0, "y": 0.0, "depth": BANK_DEPTH}
        self.origin = (0.0, 0.0)
        self.target = (0.0, 0.0)  # The water point locked in by the click that starts a cast
        self.charge_ticks = 0.0
        self.cast_power = 0.0
        self.cast_distance = MIN_CAST_DISTANCE
        self.full_cast = False
        self.cast_ticks = 0.0
        self.landing = (0.0, 0.0)
        self.arc = 0.0  # How high the cast lure is in the air, from 0 to 1
        self.up_was_held = False
        self.jig_vel = 0.0
        self.jerks = 0
        self.combo = 0
        self.last_jerk = -999.0
        self.float_dip = 0.0
        self.nibbles = 0
        self.nibble_timer = 0.0
        self.nibble_swimmer = None

        self.caught = None  # Swimmer on the line: a hooked fish, or the one that just took the bait
        self.fight = None
        self.snag = None
        self.snags = []  # Stumps in the current area, as (x, y) tiles
        self.shake = 0.0
        self.advantage = 0
        self.hookset_wait = 0.0
        self.hookset_go = False
        self.hookset_ticks = 0.0
        self.mood = "neutral"
        self.mood_ticks = 0.0

        self.lures = lure_models(render)
        self.float = float_model(render)
        self.line_node = None
        self.rod_out = True  # False while the rod is carried on the back, when there is no float or line out in the water
        self.tip_of = None  # Gives the world position of the rod's tip, from the game's angler
        self.ring_node = None
        self.scent_node = None
        self.set_area("pond")

    # Area

    def set_area(self, area):
        """Opens a fishing area: the stumps are scattered again, and the lure goes back in hand."""
        self.area = area
        self.state = IDLE
        self.level.roll_snags(random.Random())
        self.snags = list(self.level.snags.get(area, ())) if area != "pond" else []
        for key, node in self.lures.items():
            node.show() if key == area else node.hide()
        self.float.hide()
        self.caught = None
        self.fight = None
        self.snag = None
        self.cooldown = 0.0

    # Measures

    def stats(self):
        return self.economy.stats()

    def max_cast(self):
        return MAX_CAST_DISTANCE + self.stats()["reach"]

    def reach_range(self):
        return self.max_cast() - MIN_CAST_DISTANCE

    def tolerance(self):
        return ACCURACY_TOLERANCE * self.stats()["tolerance"] * self.weather.mods["accuracy"]

    def target_distance(self):
        return math.hypot(self.target[0] - self.origin[0], self.target[1] - self.origin[1]) * TILE_PX

    def needed_power(self):
        """The meter power that lands the lure exactly on the target."""
        return clamp((self.target_distance() - MIN_CAST_DISTANCE) / self.reach_range(), 0.0, 1.0)

    def clamp_target(self, tile):
        """Keeps a cast target inside the rod's reach along the line from the angler. Too close snaps out to the shortest cast."""
        dx, dy = tile[0] + 0.5 - self.origin[0], tile[1] + 0.5 - self.origin[1]
        dist = math.hypot(dx, dy) or 1e-6
        px = clamp(dist * TILE_PX, MIN_CAST_DISTANCE, self.max_cast())
        return (self.origin[0] + dx / dist * px / TILE_PX, self.origin[1] + dy / dist * px / TILE_PX)

    def landing_on(self, point):
        """The water the lure lands in: the furthest water of this area along the cast, stopping at the first land. None if the first step is land."""
        dx, dy = point[0] - self.origin[0], point[1] - self.origin[1]
        steps = max(1, int(math.hypot(dx, dy) * 20))
        best = None
        in_water = False
        for i in range(1, steps + 1):
            x = self.origin[0] + dx * i / steps
            y = self.origin[1] + dy * i / steps
            zone = self.level.water_zone(int(x), int(y))
            if zone is None:
                if in_water:
                    break  # Out of the water again: the lure lands at the last water it passed
                continue  # Still on the bank, before the water starts
            in_water = True
            if zone == self.area:
                best = (x, y)
        return best

    # Events and mood

    def say(self, text):
        self.events.append(text)

    def set_mood(self, mood, ticks):
        self.mood = mood
        self.mood_ticks = ticks

    def current_mood(self):
        if self.mood_ticks > 0:
            return self.mood
        if self.state == FIGHTING:
            return "strain"
        return "neutral"

    # Casting

    def start_charge(self, tile):
        """Locks the target and starts the meter. Needs bait for this area, and the lure out of the water."""
        if self.state != IDLE:
            return False
        if self.line_hp <= 0:
            self.say("Your line is shredded. Press R to restring")
            return False
        if not self.economy.can_cast(self.area):
            self.say(f"Out of bait for the {ZONE_NAMES[self.area]}. Press B to buy some")
            self.audio.play("error")
            return False
        self.target = self.clamp_target(tile)
        self.state = CHARGING
        self.charge_ticks = 0.0
        return True

    def release_cast(self):
        if self.state != CHARGING:
            return False
        error = self.cast_power - self.needed_power()
        self.full_cast = abs(error) <= self.tolerance()
        # The meter sets the distance along the line to the target, so a spot-on meter lands exactly on it
        self.cast_distance = MIN_CAST_DISTANCE + self.cast_power * self.reach_range()
        scale = self.cast_distance / max(1e-6, self.target_distance())
        point = (self.origin[0] + (self.target[0] - self.origin[0]) * scale, self.origin[1] + (self.target[1] - self.origin[1]) * scale)
        landing = self.landing_on(point)
        if landing is None:
            self.say("Splash on the bank! Aim further out over the water")
            self.audio.play("error")
            self.state = IDLE
            return False

        self.scented = self.economy.use_attractant(self.area) if self.scent_next else False
        self.scent_next = False
        self.jerks = 0
        self.landing = landing
        if self.full_cast:
            self.say("Spot on!")
        else:
            missed = abs(error) * self.reach_range()
            self.say(f"{'Short' if error < 0 else 'Long'} by {missed:.0f}px")
        self.state = CASTING
        self.cast_ticks = 0.0
        self.audio.play("cast")
        return True

    def update_charging(self, dt):
        self.charge_ticks += frames(dt)
        # The meter sweeps 0 -> 1 -> 0 over POWER_FRAMES
        self.cast_power = 1 - abs((self.charge_ticks % POWER_FRAMES) / (POWER_FRAMES / 2) - 1)

    def update_casting(self, dt):
        self.cast_ticks += frames(dt)
        c = self.cast_ticks / CAST_FRAMES
        if c < CAST_RELEASE:
            self.lure["x"], self.lure["y"] = self.origin  # The lure hangs from the rod tip
            self.arc = 0.0
        else:
            u = (c - CAST_RELEASE) / (1 - CAST_RELEASE)
            self.lure["x"] = self.origin[0] + (self.landing[0] - self.origin[0]) * u
            self.lure["y"] = self.origin[1] + (self.landing[1] - self.origin[1]) * u
            self.arc = math.sin(math.pi * u)  # The lure flies up and over, then drops into the water
        if self.cast_ticks >= CAST_FRAMES:
            self.state = IN_WATER
            self.lure["x"], self.lure["y"] = self.landing
            self.lure["depth"] = LANDING_DEPTH
            self.jig_vel = 0.0
            self.splash = RING_FRAMES
            self.audio.play("splash")

    # In the water: each area has its own lure

    def update_in_water(self, dt, keys):
        f = frames(dt)
        up, down = keys["up"], keys["down"]
        jerk = up and not self.up_was_held
        lure = self.lure

        if self.area == "pond":
            # Up lifts the bait towards the float, Down lets it sink. Let go and it hangs where it is.
            if up:
                lure["depth"] -= 3 * f
            elif down:
                lure["depth"] += 3 * f
            else:
                # The sway averages to nothing, so the bait does not sink on its own and run out to the bottom
                lure["depth"] += math.sin(self.frame * 0.08) * 0.4 * f
        elif self.area == "shore":
            # Paddletail sinks slowly and Up reels it in. Tapping Up twitches it sideways through the surf.
            lure["depth"] += (-3 if up else 2.5) * f
            if jerk:
                lure["depth"] -= 8
                lure["x"] += (10 if (int(self.frame) // 20) % 2 else -10) / TILE_PX
                self.audio.play("twitch")
            lure["x"] += math.sin(self.frame * 0.04) * 0.5 / TILE_PX * f  # Current in the surf
        else:
            # Metal jig: falls fast, Up jerks it up, Down reels in quickly
            if down:
                lure["depth"] -= 4 * f
                self.jig_vel = 0.0
            else:
                if jerk:
                    self.jig_vel = -8
                    self.count_jerk()
                self.jig_vel = min(self.jig_vel + 0.25 * f, 4.5)
                lure["depth"] += self.jig_vel * f

        # Wind pushes the lure about in the water
        lure["x"] += self.weather.mods["wind"] * math.sin(self.frame * 0.07) * 0.6 / TILE_PX * f

        if lure["depth"] <= LURE_TOP:
            self.state = IDLE
        elif lure["depth"] >= MAX_DEPTH:
            self.state = RETRACTING

    def count_jerk(self):
        self.combo = min(5, self.combo + 1 if self.frame - self.last_jerk < RHYTHM_FRAMES else 1)
        self.last_jerk = self.frame
        self.jerks += 1  # Counting jerks tells you how far down the jig has gone
        self.audio.play("jig")
        if self.combo >= 3:
            self.say(f"Rhythm x{self.combo}")

    def rhythm(self):
        """How many taps in a row are still in rhythm with the jig."""
        return self.combo if self.frame - self.last_jerk < RHYTHM_FRAMES else 0

    def depth_layer(self):
        if self.lure["depth"] < SURFACE_Y:
            return "Surface"
        return "Mid" if self.lure["depth"] < MID_Y else "Deep"

    def pond_layer(self):
        """The layer the bait is nearest to: Top, Middle or Bottom."""
        return min(POND_LAYERS, key=lambda name: abs(POND_LAYERS[name] - self.lure["depth"]))

    # Strikes: each area works differently

    def swimmers_here(self):
        return [s for s in self.school.swimmers if s["zone"] == self.area and s is not self.caught]

    def scent_mult(self):
        """A scented lure is about half again as likely to get a bite or a strike."""
        return 1.5 if self.scented else 1.0

    def attract(self, s, f):
        """Scent draws nearby fish towards the lure, so they come to it instead of drifting past."""
        dx = (self.lure["x"] - s["x"]) * TILE_PX
        dy = self.lure["depth"] - s["depth"]
        if abs(dx) > ATTRACT_RANGE or abs(dy) > ATTRACT_RANGE:
            return
        s["x"] += clamp(dx * 0.03, -1.0, 1.0) / TILE_PX * f
        s["depth"] += clamp(dy * 0.02, -0.6, 0.6) * f

    def pond_bite_chance(self, s):
        """A full cast doubles the chance of a bite in the pond."""
        chance = 0.06 * (2 if self.full_cast else 1) * self.stats()["stealth"] * self.weather.mods["bite"] * self.scent_mult()
        chance *= self.weather.activity(s["fish"].active)
        if self.weather.frenzy():
            chance *= 3
        return chance

    def strike_chance(self, s):
        """Per frame the lure is in a fish's mouth. Fish feed by time of day, and the tide changes how often they strike."""
        frenzy = 3 if self.weather.frenzy() else 1
        return frenzy * 0.05 * self.weather.activity(s["fish"].active) * self.weather.strike_mult() * self.weather.mods["bite"] * self.depth_factor(s) * self.scent_mult()

    def depth_factor(self, s):
        """Sea fish only strike near their own depth. Lure in their water and they strike far more often."""
        lo, hi = s["fish"].depth_range
        return 1.6 if lo - 30 <= self.lure["depth"] <= hi + 30 else 0.35

    def touching(self, s):
        """Whether the lure is in a fish's mouth: close in tiles, and at its depth."""
        fish = s["fish"]
        return abs(s["x"] - self.lure["x"]) * TILE_PX < fish.width / 2 + 4 and abs(s["depth"] - self.lure["depth"]) < fish.height / 2 + 6

    def is_chasing(self, s):
        return abs(s["x"] - self.lure["x"]) * TILE_PX < 90 and abs(s["depth"] - self.lure["depth"]) < 60

    def update_strikes(self, dt):
        f = frames(dt)
        for s in self.swimmers_here():
            if self.scented:
                self.attract(s, f)
            if self.area == "pond":
                if self.school.near(s, self.lure) and random.random() < self.pond_bite_chance(s) * f:
                    self.start_nibbling(s)
            elif self.area == "boat" and self.rhythm() >= 3 and self.is_chasing(s):
                # Fish that see the jig in rhythm come up to it, which is when the predators strike
                s["x"] += (2 if s["x"] < self.lure["x"] else -2) / TILE_PX * f
                s["depth"] += (1 if s["depth"] < self.lure["depth"] else -1) * f
            elif self.touching(s) and random.random() < self.strike_chance(s) * f:
                self.start_strike(s)

    def start_nibbling(self, s):
        if self.nibbles:
            return
        self.nibbles = random.randint(2, 3)
        self.nibble_swimmer = s
        self.nibble_timer = NIBBLE_FRAMES

    def update_nibbles(self, dt):
        """Pond float: the fish nibble a couple of times before the big dip, so you can wait for the cue."""
        if not self.nibbles:
            return
        s = self.nibble_swimmer
        if self.state != IN_WATER or s not in self.school.swimmers or not self.school.near(s, self.lure):
            self.nibbles = 0  # The fish swam off, or the line was reeled in
            return
        self.nibble_timer -= frames(dt)
        if self.nibble_timer > 0:
            return
        self.nibbles -= 1
        self.nibble_timer = NIBBLE_FRAMES
        if self.nibbles:
            self.float_dip = 4  # A minor nibble, the float dips a little
            self.audio.play("plop")
        else:
            self.float_dip = 12  # The big dip, the fish has taken the bait
            self.start_strike(s)

    def start_strike(self, s):
        """A fish has taken the bait. It is pinned to the lure until the hookset."""
        self.caught = s
        self.school.swimmers.remove(s)
        # The bite wears the lure down. Only a worn out lure is replaced from the stock
        if self.economy.lure_bitten(self.area) == "none":
            self.say(f"Out of bait for the {ZONE_NAMES[self.area]}. The lure is gone")
        self.state = HOOKSET
        self.hookset_wait = HOOKSET_WAIT
        self.hookset_go = False
        self.hookset_ticks = 0.0
        s["fish"].speed = 0  # Freeze the fish
        self.economy.wear_part("hook", 0.3)
        self.shake = 8 + s["fish"].weight * 2  # Heavier fish hit harder
        self.splash = RING_FRAMES
        self.audio.play("bite")
        self.set_mood("surprised", 40)
        self.pin_caught()

    def pin_caught(self, swing=0.0):
        """The caught fish moves with the lure, swinging side to side by swing pixels."""
        s = self.caught
        s["x"] = self.lure["x"] + swing / TILE_PX
        s["y"] = self.lure["y"]
        s["depth"] = self.lure["depth"]
        self.school.place(s)

    def swim_offset(self, amplitude):
        """The hooked fish swims side to side, and turns round at each end of its swing."""
        phase = self.frame * 0.05
        self.caught["dir"] = 1 if math.cos(phase) >= 0 else -1
        return math.sin(phase) * amplitude

    # Hookset

    def hookset_ring_radius(self):
        progress = min(1, self.hookset_ticks / HOOKSET_FRAMES)
        return HOOKSET_RING_START - (HOOKSET_RING_START - HOOKSET_RING_TARGET) * progress

    def update_hookset(self, dt):
        f = frames(dt)
        self.pin_caught(self.swim_offset(10))
        if not self.hookset_go:
            # WAIT phase: the fish is mouthing the lure, the ring hasn't started yet
            self.hookset_wait -= f
            if self.hookset_wait <= 0:
                self.hookset_go = True
                self.hookset_ticks = 0.0
            return
        self.hookset_ticks += f
        if self.hookset_ticks >= HOOKSET_FRAMES:
            self.say("Too slow! It's still on, but the fish has the upper hand!")
            self.audio.play("miss")
            self.start_fight(-1)

    def set_hook(self):
        """A click or Space in the hookset. Only the GO ring, shrunk onto its target, sets the hook."""
        if self.state != HOOKSET:
            return False
        if not self.hookset_go:
            self.say("Too early! The fish has the upper hand!")
            self.audio.play("miss")
            self.start_fight(-1)
            return True
        window = HOOKSET_WINDOW * self.stats()["window"]
        if abs(self.hookset_ring_radius() - HOOKSET_RING_TARGET) <= window:
            self.say("Hook set!")
            self.audio.play("hookset")
            self.start_fight(1)
        else:
            self.say("Late hookset... the fish has the upper hand!")
            self.audio.play("miss")
            self.start_fight(-1)
        return True

    # Fight

    def start_fight(self, advantage):
        self.advantage = advantage
        self.state = FIGHTING
        self.shake = 10  # The fish is on, so the rod jolts
        self.fight = Fight(self.caught, advantage, self.stats())

    def update_fight(self, dt, keys):
        fight = self.fight
        fight.clutch = self.clutch
        self.pin_caught(self.swim_offset(40 + fight.tug * 4))
        result = fight.update(dt, keys, self.economy)
        self.shake = max(self.shake, fight.shake)
        if fight.lunge_sound:
            self.audio.play("drag")  # The reel screams as the fish takes line
            self.set_mood("strain", 2)
        if result == "land":
            self.say(f"Landed the {self.caught['fish'].name}!")
            self.state = RETRACTING
        elif result is not None:
            if fight.tension >= 100:
                self.lose_fish("Line snapped! The lure is gone.", snapped=True)
            elif fight.progress <= 0:
                self.lose_fish("The fish got away!")
            else:
                self.lose_fish("The hook pulled free!")
            self.state = RETRACTING

    def adjust_clutch(self, step):
        self.clutch = round(min(2.0, max(0.4, self.clutch + 0.2 * step)), 1)
        self.say(f"Drag {self.clutch:.1f}x")

    # Snags

    def check_snag(self, dt):
        if self.cooldown > 0:
            self.cooldown -= dt * 60 / 60
            return
        if self.caught or self.area == "pond":
            return
        for x, y in self.snags:
            near = abs(self.lure["x"] - (x + 0.5)) * TILE_PX < SNAG_RANGE_X and abs(self.lure["y"] - (y + 0.5)) * TILE_PX < SNAG_RANGE_Y
            if near:
                if random.random() < SNAG_CHANCE * frames(dt):
                    self.start_snag(x, y)
                return

    def start_snag(self, x, y):
        self.snag = Snag(x, y)
        self.state = SNAGGED
        self.economy.lose_lure(self.area)  # Snagged on a stump, so the lure stays behind whether or not the line holds
        self.say("Snagged! Wiggle Left and Right to free it")
        self.audio.play("miss")
        self.set_mood("strain", 60)
        self.shake = 6

    def wiggle(self, side):
        if self.state == SNAGGED:
            self.snag.wiggle(side, self.audio.play)

    def update_snagged(self, dt, keys):
        result = self.snag.update(dt, keys["up"], self.stats()["power"], self.economy)
        self.shake = max(self.shake, (self.snag.tension - 70) / 8 if self.snag.tension > 70 else 0)
        if result == "freed":
            self.say("Freed the lure!")
            self.audio.play("hookset")
            self.cooldown = SNAG_COOLDOWN
            self.snag = None
            self.state = RETRACTING
        elif result == "snapped":
            self.lose_snagged_lure()

    def lose_snagged_lure(self):
        """The line snapped on the snag. The lure is gone, so the line goes back to the bank empty."""
        self.say("Line snapped on the snag! The lure is gone.")
        self.audio.play("snap")
        self.snag = None
        self.cooldown = SNAG_COOLDOWN
        self.shake = 12
        self.set_mood("sad", 120)
        self.state = IDLE

    # Retrieve

    def update_retracting(self, dt, origin):
        f = frames(dt)
        fish = self.caught
        self.economy.wear_part("reel", 0.004 * f)  # Every turn of the reel wears the gears a little
        speed = 6  # The base reel speed
        if fish:
            # Heavier fish slow the reel down. A good hookset makes the retrieve easier.
            speed = max(1.0, 6 - fish["fish"].weight)
            speed *= 1.25 if self.advantage > 0 else 0.8
            self.pin_caught(self.swim_offset(10))
        self.lure["depth"] -= speed * self.stats()["speed"] * f
        if fish:
            self.reel_clicks += f
            if self.reel_clicks >= 12:
                self.reel_clicks = 0
                self.audio.play("reel")  # Clicks as the reel turns
        # The lure slides back in towards the angler as it comes up
        self.lure["x"] += clamp((origin[0] - self.lure["x"]) * TILE_PX, -4, 4) / TILE_PX * f
        self.lure["y"] += clamp((origin[1] - self.lure["y"]) * TILE_PX, -4, 4) / TILE_PX * f

        if self.lure["depth"] <= BANK_DEPTH:  # Back at the bank
            self.lure["depth"] = BANK_DEPTH
            self.state = IDLE
            if fish:
                # A fish heavier than the line can hold may snap it right at the bank
                snap = max(0.0, fish["fish"].weight - self.stats()["strength"]) * 0.15
                if random.random() < snap:
                    self.lose_fish("Line snapped! The lure is gone.", snapped=True)
                else:
                    self.land_fish()

    def land_fish(self):
        s = self.caught
        fish = s["fish"]
        self.caught = None
        self.fight = None
        self.session_value += fish.price
        self.shake = 6
        self.splash = RING_FRAMES
        self.set_mood("happy", 150)
        if self.economy.record_catch(fish):
            self.economy.advance_story("catch", self.area)
            self.audio.play("catch")
            self.say(f"Caught a {fish.name}! Worth ${fish.price}")
            for reward in self.economy.new_rewards:
                self.say("Journal: " + reward)
            self.economy.new_rewards.clear()
        else:
            self.say(f"Creel full, so the {fish.name} went back")
        self.school.release(s)
        self.school.add(self.area)

    def lose_fish(self, message, snapped=False):
        self.say(message)
        self.audio.play("snap" if snapped else "escape")
        if snapped:
            # The lure goes with the line
            self.economy.lose_lure(self.area)
        s = self.caught
        self.caught = None
        self.fight = None
        self.school.release(s)
        self.school.add(self.area)  # It got away, so another swims in
        self.shake = 12
        self.set_mood("sad", 120)

    # Keeping the line

    def reel_in(self, silent=False):
        """Brings the lure back to the rod. Not possible while a fish is on the line."""
        if self.state == FIGHTING:
            if not silent:
                self.say("Fight the fish first")
            return False
        if self.state == IDLE:
            return False
        if self.state == HOOKSET and self.caught:
            self.school.swimmers.append(self.caught)  # It had not been hooked yet, so it swims off again
            self.caught = None
        self.state = IDLE
        if not silent:
            self.say("Reeled in")
        return True

    def restring(self):
        if self.line_hp >= 100:
            return False
        if self.economy.money < 20:
            self.say("Not enough money to restring ($20)")
            return False
        self.economy.money -= 20
        self.line_hp = 100.0
        self.say("Restrung the line ($20)")
        return True

    def toggle_scent(self):
        self.scent_next = not self.scent_next
        return self.scent_next

    # Each frame

    def update(self, dt, origin, keys):
        """Runs the whole fishing side for one frame. keys holds up, down, left and right as booleans."""
        f = frames(dt)
        self.origin = origin
        self.frame += f
        self.cooldown = max(0.0, self.cooldown - dt)
        self.splash = max(0.0, self.splash - f)
        self.mood_ticks = max(0.0, self.mood_ticks - f)
        self.float_dip *= 0.8 ** f
        self.shake = self.shake * 0.8 ** f if self.shake >= 0.5 else 0.0

        self.school.swim(dt, skip=self.caught)
        if self.caught:
            self.caught["thrash"] = 1.0 if self.state == FIGHTING else 0.3 if self.state == HOOKSET else 0.0

        if self.state == IDLE:
            self.lure["x"], self.lure["y"] = origin
            self.lure["depth"] = BANK_DEPTH
        elif self.state == CHARGING:
            self.update_charging(dt)
        elif self.state == CASTING:
            self.update_casting(dt)
        elif self.state == IN_WATER:
            self.update_in_water(dt, keys)
            if self.state == IN_WATER:
                self.update_strikes(dt)
            if self.state == IN_WATER:
                self.check_snag(dt)
        elif self.state == HOOKSET:
            self.update_hookset(dt)
        elif self.state == FIGHTING:
            self.update_fight(dt, keys)
        elif self.state == RETRACTING:
            self.update_retracting(dt, origin)
            self.check_snag(dt)
        elif self.state == SNAGGED:
            self.update_snagged(dt, keys)

        self.update_nibbles(dt)
        self.up_was_held = keys["up"]
        self.refresh(origin)

    def lure_height(self):
        """Above the water while in hand and while cast, and just under the surface once it is in the water."""
        if self.state in (IDLE, CHARGING):
            return 1.2
        if self.state == CASTING:
            return 1.2 + self.arc * 2.5
        return WATER_Z - (self.lure["depth"] - WATER_TOP) * 0.25 / TILE_PX

    def strike_point(self):
        """Where the strike ring belongs: on the water over the lure, where the float sits, not down at the bait."""
        return (self.lure["x"], self.lure["y"], WATER_Z + 0.02)

    def refresh(self, origin):
        """Places the lure, float, line and ripples in the world for this frame."""
        lure = self.lure
        tip = self.rod_tip(origin)
        lure_node = self.lures[self.area]
        lure_node.setPos(lure["x"], lure["y"], self.lure_height())
        # Nothing is cast while the angler is idle or still choosing a cast, so the lure is not drawn: it would hang between the
        # angler's legs, whether the rod is out or on the back
        resting = self.state in (IDLE, CHARGING)
        lure_node.hide() if resting else lure_node.show()
        in_water = self.state not in (IDLE, CHARGING, CASTING)

        self.float.hide()
        if self.rod_out and self.area == "pond" and self.state in (IN_WATER, HOOKSET):  # No float while the rod is on the back
            self.float.show()
            bob = math.sin(self.frame * 0.23) * 1.2 + math.sin(self.frame * 0.61) * 0.8
            self.float.setPos(lure["x"], lure["y"], WATER_Z + 0.02 + (self.float_dip + bob) * 0.01)

        if self.line_node:
            self.line_node.removeNode()
            self.line_node = None
        if self.rod_out and not resting:  # With nothing cast there is no string out, and none from the back either
            lines = LineSegs()
            lines.setColor(*LINE_COLOUR)
            lines.setThickness(1.5)
            lines.moveTo(*tip)
            if self.float.isHidden():
                lines.drawTo(lure["x"], lure["y"], lure_node.getZ())
            else:
                lines.drawTo(lure["x"], lure["y"], WATER_Z + 0.02)
            self.line_node = self.render.attachNewNode(lines.create())

        self.refresh_ring(lure)
        self.refresh_scent(lure, in_water)

    def refresh_ring(self, lure):
        """The splash ripple that spreads out from a cast or a strike."""
        if self.ring_node:
            self.ring_node.removeNode()
            self.ring_node = None
        if self.splash <= 0:
            return
        lines = LineSegs()
        lines.setColor(0.8, 0.9, 0.95, self.splash / RING_FRAMES)
        radius = 0.2 + (RING_FRAMES - self.splash) / RING_FRAMES * 0.8
        self.ring_node = self.render.attachNewNode(self.circle(lines, lure["x"], lure["y"], radius))

    def refresh_scent(self, lure, in_water):
        """Scent ripples spread out from a scented lure while it is in the water."""
        if self.scent_node:
            self.scent_node.removeNode()
            self.scent_node = None
        if not (self.scented and self.state == IN_WATER and in_water):
            return
        lines = LineSegs()
        lines.setColor(0.9, 0.75, 0.3, 1)
        for ring in range(2):
            radius = ((self.frame * 1.2 + ring * 30) % 60) / TILE_PX
            self.circle(lines, lure["x"], lure["y"], radius)
        self.scent_node = self.render.attachNewNode(lines.create())

    @staticmethod
    def circle(lines, x, y, radius, steps=16):
        """Draws a flat ring at the water surface onto a LineSegs and returns it."""
        for i in range(steps + 1):
            angle = 2 * math.pi * i / steps
            point = (x + radius * math.cos(angle), y + radius * math.sin(angle), WATER_Z + 0.01)
            if i == 0:
                lines.moveTo(*point)
            else:
                lines.drawTo(*point)
        return lines.create()

    def rod_tip(self, origin):
        """Where the line leaves the rod, over the angler's shoulder."""
        if self.tip_of:
            return tuple(self.tip_of())
        return (origin[0], origin[1], 1.2)
