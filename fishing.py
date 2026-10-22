import math
import random

import pygame

from config import WIDTH, HEIGHT, WHITE, BLACK, GREY, GREEN, RED, GOLD
from draw import WATER_TOP, GROUND_HALF, THEMES, depth_t, ground_point, lerp_color, lerp_point, make_background, make_panel, draw_text, pixelate, water_color
from doodads import Ambience
from fish import spawn_random_fish, move_toward
from scene import Scene
from ui import draw_panel
from journal_scene import JournalScene
from setup_menu import SetupScene

# Hook states
IDLE = "IDLE"
CHARGING = "CHARGING"
CASTING = "CASTING"
IN_WATER = "IN_WATER"
HOOKSET = "HOOKSET"
FIGHTING = "FIGHTING"
RETRACTING = "RETRACTING"
SNAGGED = "SNAGGED"

AREA_INFO = {
    "pond": {"name": "Pond", "lure": "Worm", "size": (8, 12)},
    "shore": {"name": "Shore", "lure": "Paddletail", "size": (14, 20), "hold_depth": None},
    "boat": {"name": "Open Sea", "lure": "Metal Micro Jig", "size": (10, 20), "hold_depth": None},
}

# Casting power: the meter sweeps up and down, and releasing Space locks in the power
POWER_FRAMES = 60  # One full sweep of the meter
ACCURACY_TOLERANCE = 0.03  # How close the meter must be to the target power to land on it
MIN_CAST_DISTANCE = 60
MAX_CAST_DISTANCE = 320
CAST_FRAMES = 48  # Length of the whole cast, wind-up to landing
CAST_RELEASE = 0.6  # Fraction of the cast where the line leaves the rod
LANDING_Y = WATER_TOP + 30
POND_LAYERS = {"Top": 190, "Middle": 300, "Bottom": 420}  # Depths the pond bait can be held at
LURE_TOP = WATER_TOP + 4  # Reeling past this point brings the lure back to the bank
SPLASH_FRAMES = 28
NIBBLE_FRAMES = 30  # Pond: gap between the small nibbles before the big dip
RHYTHM_FRAMES = 40  # Open sea: how close taps of the rod must be to count as one rhythm
RUN_FRAMES = 20  # After a lunge, the fish is running hard for this many frames
SLACK_FRAMES = 150  # Frames of slack line, while the fish is calm, before the hook pulls free
TENSION_DECAY = 0.6
SNAG_CHANCE = 0.015  # Per frame the lure sits inside a snag's area, about 1 pass in 7 snags
SNAG_AREA = (44, 30)  # Width and height of the area around a snag that can catch the lure
SNAG_COUNT = 3  # Snags per area, placed at random each time the scene opens
SNAG_COOLDOWN = 90  # Once freed, the lure cannot snag again straight away
SNAG_PULL_PROGRESS = 0.7  # Holding Up pulls the lure free this much each frame...
SNAG_PULL_TENSION = 1.4  # ...and tightens the line this much
SNAG_WIGGLE_PROGRESS = 12  # Each Left/Right wiggle that alternates sides
SNAG_WIGGLE_TENSION = 2
SNAG_WRONG_TENSION = 4  # Pressing the same side twice in a row only tightens the line
SNAG_TENSION_SNAP = 100  # The line snaps at this tension, and the lure is lost
SURFACE_Y = 260  # Sea depth layers: above this is Surface, up to MID_Y is Mid, below is Deep
MID_Y = 400
DEPTH_PER_METRE = 11  # How many pixels of water make up one metre on the depth readout
ATTRACT_RANGE = 160  # Scent pulls in fish this close to the lure

# Angler hand positions, relative to the angler's left edge
HAND_IDLE = (42, 82)
HAND_BACK = (20, 94)  # Rod swung back during the wind-up
HAND_RELEASE = (58, 64)  # Rod swung forward at the release
ROD_VECTOR = (6, -50)  # From the hand up to the rod tip

# Hookset: a bite shows WAIT, then GO and the ring starts shrinking
HOOKSET_WAIT = 40
HOOKSET_FRAMES = 50
HOOKSET_RING_START = 60
HOOKSET_RING_TARGET = 20
HOOKSET_WINDOW = 4  # Radius pixels either side of the target that count as a good hookset

# Fight gauge (horizontal, along the bottom of the screen)
GAUGE_W = 360
GAUGE_THICK = 22
GAUGE_X = WIDTH // 2 - GAUGE_W // 2
GAUGE_Y = HEIGHT - 70
PROGRESS_Y = GAUGE_Y - 26
PROGRESS_THICK = 14
SAFE_ZONE_COLOR = (0, 255, 100, 150)  # Semi-transparent green

LINE_COLOR = (238, 238, 238)
HOOK_GREY = (176, 180, 190)
OUTLINE = (34, 24, 34)
SKIN = (236, 196, 156)
SHIRT_RED = (196, 58, 52)
HAT_GREEN = (58, 92, 60)
PANTS = (58, 58, 78)
ROD_BROWN = (96, 62, 36)
TEAR_BLUE = (100, 170, 255)
WORM_PINK = (240, 120, 140)
PADDLE_PINK = (244, 170, 200)
JIG_SILVER = (200, 205, 215)
BUBBLE_EVERY = 25  # Frames between bubbles
BUBBLE_FRAMES = 90


class FishingScene(Scene):
    full_width = True

    def __init__(self, app, area):
        super().__init__(app)
        self.area = area
        self.music = area  # Each area has its own background track
        self.info = AREA_INFO[area]
        self.theme = THEMES[area]
        self.background = make_background(area)
        self.world = pygame.Surface((WIDTH, HEIGHT))  # The pixel-scaled layer, drawn before the UI
        self.panel = make_panel(340, 30)
        self.font = app.font
        self.small_font = app.small_font
        self.large_font = app.large_font
        self.frame = 0

        # Visual-only effects use their own RNG so the game's random stream is untouched
        self.fx_rng = random.Random(11)
        self.snag_rng = random.Random()  # Unseeded, so the snags land somewhere new each time the scene opens
        self.shake = 0.0
        self.splashes = []  # Each splash is [x, y, age]
        self.bubbles = []  # Each bubble is [x, y, age]
        self.mood = "neutral"
        self.mood_ticks = 0
        self.blink_ticks = 0
        self.next_blink = 150
        self.message = ""
        self.message_ticks = 0
        self.session_value = 0

        self.fishes = [self.spawn() for _ in range(8)]
        self.caught_fish = None

        # Angler (stands on the bank; player_y is the shoreline)
        self.player_x = WIDTH // 2
        self.player_y = WATER_TOP
        self.player_width, self.player_height = 60, 25
        self.player_speed = 5
        self.facing = 1  # 1 faces right, -1 faces left. The angler turns to face the way he walks.
        self.angler_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)  # The angler is drawn here, then flipped if needed

        # Lure: lure_x is its centre, lure_y is its top
        self.state = IDLE
        self.charge_ticks = 0
        self.cast_power = 0.0
        self.cast_distance = MIN_CAST_DISTANCE
        self.cast_side = 1  # 1 casts right, -1 casts left
        self.full_cast = False
        self.cast_ticks = 0
        self.lure_w, self.lure_h = self.info["size"]
        self.lure_x = self.idle_lure_x()
        self.lure_y = self.idle_lure_y()
        self.max_depth = HEIGHT - 15
        self.base_reel_speed = 6
        self.up_was_held = False
        self.jig_vel = 0
        self.float_dip = 0.0
        self.aim = self.default_target()  # Where the cursor points, shown before a click
        self.target = self.aim  # The spot locked in by the click that starts the cast
        self.landing_y = LANDING_Y
        self.walking = False
        self.walk_amount = 0.0  # Eases up while walking, and back down when standing still
        self.walk_phase = 0.0
        self.stride = 0.0
        self.nibbles = 0  # Pond: nibbles left before the fish takes the bait
        self.nibble_timer = 0
        self.nibble_fish = None
        self.combo = 0  # Open sea: how many jerks in a row are in rhythm
        self.last_jerk = -999
        self.tension = 0.0  # Fight: how tight the line is, 100 snaps it
        self.slack_ticks = 0
        self.last_lunge = -999

        self.advantage = 0  # +1 after a good hookset, -1 after a bad one
        self.hookset_wait = 0
        self.hookset_go = False
        self.hookset_ticks = 0
        self.reset_fight()

        # Structure on the bottom that can catch the lure, and the state of a snag in progress
        self.snags = self.make_snags()
        self.snagged = None  # The snag holding the lure, while in the SNAGGED state
        self.snag_progress = 0.0  # Rises as the angler wiggles the lure free
        self.snag_tension = 0.0  # Rises while the line is pinned, and snaps the line at 100
        self.snag_side = 0  # Which side the last wiggle was on, so the next one must alternate
        self.snag_cooldown = 0
        self.jerks = 0  # Micro jig: how many jerks since the cast, to count down to a layer

        self.ambience = Ambience(area)  # Passers-by, cars, birds and boats in the background
        self.scented = False  # Whether this cast used an attractant

    def make_snags(self):
        """Snags are scattered through the water, away from the bank. They use their own RNG so fish are unaffected."""
        if self.area == "pond":
            return []  # The pond is clear of structure, so the bait is never snagged
        snags = []
        for _ in range(SNAG_COUNT):
            x = self.snag_rng.randint(60, WIDTH - 60)
            y = self.snag_rng.randint(WATER_TOP + 120, HEIGHT - 90)
            snags.append({"x": x, "y": y})
        return snags

    def idle_lure_x(self):
        return self.player_x + self.player_width // 2

    def idle_lure_y(self):
        return self.player_y + self.player_height

    def lure_rect(self):
        return pygame.Rect(int(self.lure_x - self.lure_w / 2), int(self.lure_y), self.lure_w, self.lure_h)

    def say(self, text, ticks=120):
        self.message = text
        self.message_ticks = ticks

    def reset_fight(self):
        self.fight_progress = 30 + 12 * self.advantage
        self.fight_ticks = 0
        self.tug = 0.0  # Decays after each lunge of the fish
        self.player_bar_x = 0
        self.player_bar_vel = 0
        self.fish_marker_x = GAUGE_W // 2
        self.fish_target_x = GAUGE_W // 2
        self.fish_timer = 0
        self.tension = 0.0
        self.slack_ticks = 0
        self.last_lunge = -999
        self.clutch = 1.0  # Drag setting: higher pulls the fish in faster, but spikes the line
        self.stamina = 100.0  # The fish tires as it runs, and lunges less once it is tired
        self.tired = False

    def stats(self):
        return self.app.economy.stats()

    def spawn(self):
        # Rarer species only swim in once the tackle is good enough to land them
        return spawn_random_fish(self.area, self.stats())

    def max_cast(self):
        # A longer rod reaches further
        return MAX_CAST_DISTANCE + self.stats()["reach"]

    def tolerance(self):
        # A scope widens the spot-on window, and bad weather narrows it
        return ACCURACY_TOLERANCE * self.stats()["tolerance"] * self.app.weather.mods["accuracy"]

    # --- Events ---
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.close()
            elif event.key == pygame.K_SPACE:
                if self.state == IDLE:
                    self.start_charge(self.default_target())
                elif self.state == HOOKSET:
                    self.set_hook()
            elif event.key == pygame.K_b and self.state == IDLE:
                self.open_shop()
            elif event.key == pygame.K_s and self.state == IDLE:
                self.app.open(SetupScene(self.app))
            elif event.key == pygame.K_j and self.state == IDLE:
                self.app.open(JournalScene(self.app))
            elif event.key == pygame.K_LEFTBRACKET:
                self.adjust_clutch(-1)
            elif event.key == pygame.K_RIGHTBRACKET:
                self.adjust_clutch(1)
            elif event.key == pygame.K_LEFT and self.state == SNAGGED:
                self.wiggle(-1)
            elif event.key == pygame.K_RIGHT and self.state == SNAGGED:
                self.wiggle(1)
        elif event.type == pygame.MOUSEWHEEL:
            self.adjust_clutch(event.y)
        elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE and self.state == CHARGING:
            self.release_cast()
        elif event.type == pygame.MOUSEMOTION and self.state == IDLE:
            self.aim = self.clamp_target(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Clicking locks in the target and starts the meter
            if self.state == IDLE:
                self.start_charge(self.clamp_target(event.pos))
            elif self.state == HOOKSET:
                self.set_hook()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.state == CHARGING:
            self.release_cast()

    def open_shop(self):
        from scenes import ShopScene  # Imported here, because scenes.py imports this module
        self.app.open(ShopScene(self.app))

    def start_charge(self, target):
        if self.app.economy.bait[self.area] <= 0:
            self.say("Out of bait! Buy some in the Shop.")
            self.app.sound.play("error")
            return
        self.target = target
        self.state = CHARGING
        self.charge_ticks = 0

    def release_cast(self):
        self.app.economy.bait[self.area] -= 1
        self.scented = self.app.economy.use_attractant(self.area)
        self.jerks = 0
        error = self.cast_power - self.needed_power()
        self.full_cast = abs(error) <= self.tolerance()
        # The meter sets the distance, so a spot-on meter lands exactly on the target
        reach = self.max_cast() - MIN_CAST_DISTANCE
        self.cast_distance = MIN_CAST_DISTANCE + self.cast_power * reach
        # The target can be left or right of the angler
        self.cast_side = 1 if self.target[0] >= self.idle_lure_x() else -1
        self.landing_y = self.target[1]
        if self.full_cast:
            self.say("Spot on!")
        else:
            missed = abs(error) * reach
            self.say(f"{'Short' if error < 0 else 'Long'} by {missed:.0f}px")
        self.state = CASTING
        self.cast_ticks = 0
        self.app.sound.play("cast")

    def default_target(self):
        return (self.idle_lure_x() + (MIN_CAST_DISTANCE + self.max_cast()) // 2, LANDING_Y)

    def clamp_target(self, pos):
        """Keeps the cast target inside the reach of the rod, on either side of the angler."""
        base = self.idle_lure_x()
        offset = pos[0] - base
        # Targets too close to the angler snap out to the shortest cast, on whichever side the cursor is
        if abs(offset) < MIN_CAST_DISTANCE:
            offset = MIN_CAST_DISTANCE if offset >= 0 else -MIN_CAST_DISTANCE
        offset = max(-self.max_cast(), min(self.max_cast(), offset))
        x = min(max(base + offset, 30), WIDTH - 30)
        y = min(max(pos[1], WATER_TOP + 20), HEIGHT - 40)
        return (x, y)

    def needed_power(self):
        """The meter power that lands the lure exactly on the target."""
        distance = abs(self.target[0] - self.idle_lure_x())
        reach = self.max_cast() - MIN_CAST_DISTANCE
        return min(1.0, max(0.0, (distance - MIN_CAST_DISTANCE) / reach))

    def set_hook(self):
        if not self.hookset_go:
            self.say("Too early! The fish has the upper hand!")
            self.app.sound.play("miss")
            self.start_fight(-1)
            return
        window = HOOKSET_WINDOW * self.stats()["window"]
        if abs(self.hookset_ring_radius() - HOOKSET_RING_TARGET) <= window:
            self.say("Hook set!")
            self.app.sound.play("hookset")
            self.start_fight(1)
        else:
            self.say("Late hookset... the fish has the upper hand!")
            self.app.sound.play("miss")
            self.start_fight(-1)

    # --- Logic ---
    def update(self):
        keys = pygame.key.get_pressed()

        self.walking = False
        if self.state == IDLE:
            self.move_angler(keys)
        self.update_walk()

        if self.state == CHARGING:
            self.update_charging()
        elif self.state == CASTING:
            self.update_casting()
        elif self.state == IN_WATER:
            self.update_in_water(keys)
        elif self.state == HOOKSET:
            self.update_hookset()
        elif self.state == FIGHTING:
            self.update_fight(keys)
        elif self.state == RETRACTING:
            self.update_retracting()
        elif self.state == SNAGGED:
            self.update_snagged(keys)
        if self.state in (IN_WATER, RETRACTING):
            self.check_snag()

        self.update_nibbles()
        self.update_fish()
        self.update_effects()
        self.ambience.update()
        self.up_was_held = keys[pygame.K_UP]

    def update_effects(self):
        # Shake and lunge fade out
        self.shake *= 0.8 if self.shake >= 0.5 else 0
        self.tug *= 0.9
        self.float_dip *= 0.8

        # Angler's expression times out back to neutral (or straining, while fighting)
        if self.mood_ticks:
            self.mood_ticks -= 1

        # Blink every so often
        if self.blink_ticks:
            self.blink_ticks -= 1
        else:
            self.next_blink -= 1
            if self.next_blink <= 0:
                self.blink_ticks = 6
                self.next_blink = self.fx_rng.randint(120, 260)

        # Splashes spread out and fade
        for splash in self.splashes:
            splash[2] += 1
        self.splashes = [s for s in self.splashes if s[2] < SPLASH_FRAMES]

        # Bubbles rise from fish, so you can see where they are gathering
        if self.frame % BUBBLE_EVERY == 0 and self.fishes:
            fish = self.fx_rng.choice(self.fishes)
            self.bubbles.append([fish.rect.centerx, fish.rect.top, 0])
        for bubble in self.bubbles:
            bubble[1] -= 0.6
            bubble[2] += 1
        self.bubbles = [b for b in self.bubbles if b[2] < BUBBLE_FRAMES]

        if self.message_ticks:
            self.message_ticks -= 1

    def set_mood(self, mood, ticks):
        self.mood = mood
        self.mood_ticks = ticks

    def current_mood(self):
        if self.mood_ticks:
            return self.mood
        if self.state == FIGHTING:
            return "strain"
        return "neutral"

    def move_angler(self, keys):
        if keys[pygame.K_LEFT] and self.player_x > 0:
            self.player_x -= self.player_speed
            self.walking = True
            self.facing = -1
        if keys[pygame.K_RIGHT] and self.player_x < WIDTH - self.player_width:
            self.player_x += self.player_speed
            self.walking = True
            self.facing = 1
        self.lure_x = self.idle_lure_x()
        self.lure_y = self.idle_lure_y()

    def update_walk(self):
        # The stride builds up while walking, and eases out when the angler stops
        self.walk_amount += ((1.0 if self.walking else 0.0) - self.walk_amount) * 0.2
        if self.walking:
            self.walk_phase += 0.3
        self.stride = math.sin(self.walk_phase) * self.walk_amount

    def update_charging(self):
        # Charging is driven by the frame count, so the meter sweeps the same way each time
        self.charge_ticks += 1
        # The meter sweeps 0 -> 1 -> 0 over POWER_FRAMES
        self.cast_power = 1 - abs((self.charge_ticks % POWER_FRAMES) / (POWER_FRAMES / 2) - 1)

    def hand_offset(self):
        """Where the hand is, relative to the angler's left edge, for the current point in a cast."""
        if self.state != CASTING:
            # The arm swings with the stride while walking
            return (HAND_IDLE[0] - self.stride * 3, HAND_IDLE[1] + abs(self.stride))
        c = self.cast_ticks / CAST_FRAMES
        if c < 0.4:
            return lerp_point(HAND_IDLE, HAND_BACK, c / 0.4)
        if c < CAST_RELEASE:
            return lerp_point(HAND_BACK, HAND_RELEASE, (c - 0.4) / (CAST_RELEASE - 0.4))
        return lerp_point(HAND_RELEASE, HAND_IDLE, (c - CAST_RELEASE) / (1 - CAST_RELEASE))

    def mirror(self, x):
        """Flips an x position across the angler's middle when he faces left."""
        if self.facing > 0:
            return x
        return 2 * (self.player_x + self.player_width / 2) - x

    def local_rod_tip(self):
        """The rod tip before the angler is turned, as it is drawn."""
        hx, hy = self.hand_offset()
        return (self.player_x + hx + ROD_VECTOR[0], hy + ROD_VECTOR[1])

    def rod_tip(self):
        """Where the line leaves the rod, on screen."""
        x, y = self.local_rod_tip()
        return (self.mirror(x), y)

    def release_tip(self):
        return (self.mirror(self.player_x + HAND_RELEASE[0] + ROD_VECTOR[0]), HAND_RELEASE[1] + ROD_VECTOR[1])

    def cast_landing_x(self):
        x = self.idle_lure_x() + self.cast_side * self.cast_distance
        return min(WIDTH - 30, max(30, x))

    def update_casting(self):
        self.cast_ticks += 1
        c = self.cast_ticks / CAST_FRAMES

        if c < CAST_RELEASE:
            # Wind-up: the lure hangs from the rod tip
            self.lure_x, self.lure_y = self.rod_tip()
        else:
            # Released: the lure flies in an arc out to the landing spot
            u = (c - CAST_RELEASE) / (1 - CAST_RELEASE)
            start_x, start_y = self.release_tip()
            end_x = self.cast_landing_x()
            self.lure_x = start_x + (end_x - start_x) * u
            self.lure_y = start_y + (self.landing_y - start_y) * u - 50 * math.sin(math.pi * u)

        if self.cast_ticks >= CAST_FRAMES:
            self.state = IN_WATER
            self.lure_x = self.cast_landing_x()
            self.lure_y = self.landing_y
            self.jig_vel = 0
            self.splashes.append([self.lure_x, self.landing_y, 0])
            self.app.sound.play("splash")

    def update_in_water(self, keys):
        up = keys[pygame.K_UP]
        down = keys[pygame.K_DOWN]
        jerk = up and not self.up_was_held

        if self.area == "pond":
            # Up lifts the bait towards the float, Down lets it sink. Let go and it hangs where it is,
            # so you can hold it at the top, middle or bottom layer.
            if up:
                self.lure_y -= 3
            elif down:
                self.lure_y += 3
            else:
                self.lure_y += math.sin(self.frame * 0.08) * 0.4 + 0.1  # Drifts gently down, and sways
        elif self.area == "shore":
            # Paddletail sinks slowly and Up reels it in. Tapping Up twitches it sideways through the surf.
            self.lure_y += -3 if up else 2.5
            if jerk:
                self.lure_y -= 8
                self.lure_x += 10 if (self.frame // 20) % 2 else -10
                self.app.sound.play("twitch")
            self.lure_x += math.sin(self.frame * 0.04) * 0.5  # Current in the surf
        else:
            # Metal jig: falls fast, Up jerks it up, Down reels in quickly
            if down:
                self.lure_y -= 4
                self.jig_vel = 0
            else:
                if jerk:
                    self.jig_vel = -8
                    self.count_jerk()
                self.jig_vel = min(self.jig_vel + 0.25, 4.5)
                self.lure_y += self.jig_vel

        # Wind pushes the lure about in the water
        self.lure_x += self.app.weather.mods["wind"] * math.sin(self.frame * 0.07) * 0.6

        if self.lure_y <= LURE_TOP:
            self.state = IDLE
            self.lure_x = self.idle_lure_x()
            self.lure_y = self.idle_lure_y()
        elif self.lure_y >= self.max_depth:
            self.state = RETRACTING

    def hookset_ring_radius(self):
        progress = min(1, self.hookset_ticks / HOOKSET_FRAMES)
        return HOOKSET_RING_START - (HOOKSET_RING_START - HOOKSET_RING_TARGET) * progress

    def update_hookset(self):
        self.pin_caught_fish(self.swim_offset(10))
        if not self.hookset_go:
            # WAIT phase: the fish is mouthing the lure, the ring hasn't started yet
            self.hookset_wait -= 1
            if self.hookset_wait <= 0:
                self.hookset_go = True
                self.hookset_ticks = 0
            return
        self.hookset_ticks += 1
        if self.hookset_ticks >= HOOKSET_FRAMES:
            self.say("Too slow! It's still on, but the fish has the upper hand!")
            self.app.sound.play("miss")
            self.start_fight(-1)

    def update_fight(self, keys):
        fish = self.caught_fish
        self.pin_caught_fish(self.swim_offset(40 + self.tug * 4))
        self.fight_ticks += 1
        if self.update_tension(keys, fish):
            return

        # Left and right push the safe zone along the gauge, with a little momentum
        push = 0
        if keys[pygame.K_LEFT]:
            push -= 1
        if keys[pygame.K_RIGHT]:
            push += 1
        self.player_bar_vel += 1.2 * push
        self.player_bar_vel *= 0.85  # Friction
        self.player_bar_x += self.player_bar_vel
        self.player_bar_x = max(0, min(GAUGE_W - fish.zone_size, self.player_bar_x))

        # Fish marker AI: pick a new target every so often, then glide towards it
        self.fish_timer -= 1
        if self.fish_timer <= 0:
            self.fish_target_x = random.randint(0, GAUGE_W)
            self.fish_timer = random.randint(*fish.aggression)
        self.fish_marker_x = move_toward(self.fish_marker_x, self.fish_target_x, fish.fish_speed * (0.5 if self.tired else 1))

        # Every so often the fish lunges, which shakes the rod. A bad hookset means harder lunges.
        if self.fight_ticks % 40 == 0:
            stats = self.stats()
            # A fish heavier than the rod's rating strains it, and reel drag softens each lunge
            strain = 1 + 0.25 * max(0.0, fish.weight - stats["rating"])
            self.tug = (1 + fish.weight) * strain / stats["drag"] * (1.3 if self.advantage < 0 else 1) * (0.5 if self.tired else 1)
            self.shake = max(self.shake, self.tug * 0.8)
            self.last_lunge = self.fight_ticks
            # Each lunge wears the line, and a fish heavier than the rod's rating wears the rod too
            self.app.economy.wear_part("line", 0.1 * fish.weight)
            self.app.economy.wear_part("rod", 0.8 if strain > 1 else 0.1)
            self.app.sound.play("drag")  # The reel screams as the fish takes line

        # Progress: gain while the marker is in the safe zone, lose otherwise
        if self.player_bar_x <= self.fish_marker_x <= self.player_bar_x + fish.zone_size:
            gain = 0.35 * self.stats()["power"] * self.clutch
            self.fight_progress += gain * (1 + 0.15 * self.advantage)
        else:
            self.fight_progress -= 0.25 * (1 - 0.15 * self.advantage)

        if self.fight_progress >= 100:
            self.say(f"Landed the {fish.name}!")
            self.state = RETRACTING  # Won the fight!
        elif self.fight_progress <= 0:
            self.lose_fish("The fish got away!")
            self.state = RETRACTING

    def check_snag(self):
        """A lure that drifts into a snag's area can catch on it. A hooked fish is always clear of the snags."""
        if self.snag_cooldown:
            self.snag_cooldown -= 1
            return
        if self.caught_fish or self.area == "pond":
            return
        for snag in self.snags:
            if abs(self.lure_x - snag["x"]) < SNAG_AREA[0] / 2 and abs(self.lure_y - snag["y"]) < SNAG_AREA[1] / 2:
                if self.fx_rng.random() < SNAG_CHANCE:
                    self.start_snag(snag)
                return

    def start_snag(self, snag):
        self.snagged = snag
        self.state = SNAGGED
        self.snag_progress = 0.0
        self.snag_tension = 0.0
        self.snag_side = 0
        self.say("Snagged! Wiggle Left and Right to free it", 180)
        self.app.sound.play("miss")
        self.set_mood("strain", 60)
        self.shake = 6

    def wiggle(self, side):
        """Alternating sides frees the lure. Pressing the same side twice in a row only tightens the line."""
        if side != self.snag_side:
            self.snag_progress += SNAG_WIGGLE_PROGRESS
            self.snag_tension += SNAG_WIGGLE_TENSION
            self.app.sound.play("twitch")
        else:
            self.snag_tension += SNAG_WRONG_TENSION
        self.snag_side = side

    def update_snagged(self, keys):
        # Holding Up pulls hard: it frees the lure faster, but tightens the line a lot
        if keys[pygame.K_UP]:
            self.snag_progress += SNAG_PULL_PROGRESS * self.stats()["power"]
            self.snag_tension += SNAG_PULL_TENSION
        else:
            # Letting go lets the line slacken and the lure settle back a little
            self.snag_progress = max(0.0, self.snag_progress - 0.2)
            self.snag_tension = max(0.0, self.snag_tension - 0.5)
        self.app.economy.wear_part("line", 0.005)  # Rubbing on the snag frays the line
        self.snag_tension = min(100.0, self.snag_tension)
        if self.snag_tension > 70:
            self.shake = max(self.shake, (self.snag_tension - 70) / 8)

        if self.snag_progress >= 100:
            self.say("Freed the lure!", 90)
            self.app.sound.play("hookset")
            self.app.economy.wear_part("line", 4)
            self.app.economy.wear_part("hook", 2)
            self.snag_cooldown = SNAG_COOLDOWN
            self.snagged = None
            self.state = RETRACTING
        elif self.snag_tension >= SNAG_TENSION_SNAP:
            self.lose_snagged_lure()

    def lose_snagged_lure(self):
        """The line snapped on the snag. The lure is gone, so the line goes back to the bank empty."""
        self.say("Line snapped on the snag! The lure is gone.")
        self.app.sound.play("snap")
        self.app.economy.bait[self.area] = max(0, self.app.economy.bait[self.area] - 1)
        self.snagged = None
        self.snag_cooldown = SNAG_COOLDOWN
        self.shake = 12
        self.set_mood("sad", 120)
        self.state = IDLE
        self.lure_x = self.idle_lure_x()
        self.lure_y = self.idle_lure_y()

    def update_retracting(self):
        speed = self.base_reel_speed
        fish = self.caught_fish
        self.app.economy.wear_part("reel", 0.004)  # Every turn of the reel wears the gears a little
        if fish:
            # Heavier fish slow the reel down. A good hookset makes the retrieve easier.
            speed = max(1.0, self.base_reel_speed - fish.weight)
            speed *= 1.25 if self.advantage > 0 else 0.8
            self.pin_caught_fish(self.swim_offset(10))

        self.lure_y -= speed * self.stats()["speed"]
        if fish and self.frame % 12 == 0:
            self.app.sound.play("reel")  # Clicks as the reel turns
        # The lure slides back in towards the angler as it comes up
        self.lure_x += max(-4, min(4, self.idle_lure_x() - self.lure_x))

        if self.lure_y <= self.idle_lure_y():  # Back at the bank
            self.lure_y = self.idle_lure_y()
            self.lure_x = self.idle_lure_x()
            self.state = IDLE
            if fish:
                # A fish heavier than the line can hold may snap it right at the bank
                snap = max(0.0, fish.weight - self.stats()["strength"]) * 0.15
                if random.random() < snap:
                    self.lose_fish("Line snapped! The lure is gone.", snapped=True)
                else:
                    self.land_fish(fish)

    def land_fish(self, fish):
        self.caught_fish = None
        self.session_value += fish.price
        self.shake = 6
        self.splashes.append([self.lure_x, self.lure_y, 0])
        self.set_mood("happy", 150)
        if self.app.economy.record_catch(fish):
            self.app.sound.play("catch")
            self.say(f"Caught a {fish.name}! Worth ${fish.price}")
            if self.app.economy.new_rewards:
                self.say("Journal: " + "; ".join(self.app.economy.new_rewards), 240)
                self.app.economy.new_rewards.clear()
        else:
            self.say(f"Creel full, so the {fish.name} went back")
        self.fishes.append(self.spawn())

    def pin_caught_fish(self, swing=0.0):
        fish = self.caught_fish
        fish.x = self.lure_x - fish.width // 2 + swing
        fish.y = self.lure_y + self.lure_h
        fish.sync_rect()

    def swim_offset(self, amplitude):
        """The hooked fish swims side to side, and turns around at each end of its swing."""
        phase = self.frame * 0.05
        self.caught_fish.facing = 1 if math.cos(phase) >= 0 else -1
        return math.sin(phase) * amplitude

    def is_near(self, fish):
        return abs(fish.rect.centerx - self.lure_x) < 40 and abs(fish.rect.centery - self.lure_y) < 30

    def scent_mult(self):
        """A scented lure is about half again as likely to get a bite or a strike."""
        return 1.5 if self.scented else 1.0

    def attract(self, fish):
        """Scent draws nearby fish towards the lure, so they come to it instead of drifting past."""
        dx = self.lure_x - fish.x
        dy = self.lure_y - fish.y
        if abs(dx) > ATTRACT_RANGE or abs(dy) > ATTRACT_RANGE:
            return
        fish.x += max(-1.0, min(1.0, dx * 0.03))
        fish.y += max(-0.6, min(0.6, dy * 0.02))
        fish.sync_rect()

    def is_biting(self, fish):
        # A full cast doubles the chance of a bite in the pond
        chance = 0.03 * (2 if self.full_cast else 1) * self.stats()["stealth"] * self.app.weather.mods["bite"] * self.scent_mult()
        chance *= self.app.weather.activity(fish.active)
        if self.app.weather.frenzy():
            chance *= 3  # Feeding frenzy
        return self.is_near(fish) and random.random() < chance

    def start_nibbling(self, fish):
        if self.nibbles:
            return
        self.nibbles = self.fx_rng.randint(2, 3)
        self.nibble_fish = fish
        self.nibble_timer = NIBBLE_FRAMES

    def update_nibbles(self):
        """Pond float: the fish nibble a couple of times before the big dip, so you can wait for the cue."""
        if not self.nibbles:
            return
        fish = self.nibble_fish
        if self.state != IN_WATER or fish not in self.fishes or not self.is_near(fish):
            self.nibbles = 0  # The fish swam off, or the line was reeled in
            return
        self.nibble_timer -= 1
        if self.nibble_timer > 0:
            return
        self.nibbles -= 1
        self.nibble_timer = NIBBLE_FRAMES
        if self.nibbles:
            self.float_dip = 4  # A minor nibble, the float dips a little
            self.app.sound.play("plop")
        else:
            self.float_dip = 12  # The big dip, the fish has taken the bait
            self.start_strike(fish)

    def strike_chance(self, fish):
        """Per frame the lure is in a fish's mouth. Fish feed by time of day, and the tide changes how often they strike."""
        weather = self.app.weather
        frenzy = 3 if weather.frenzy() else 1
        return frenzy * 0.05 * weather.activity(fish.active) * weather.strike_mult() * weather.mods["bite"] * self.depth_factor(fish) * self.scent_mult()

    def depth_factor(self, fish):
        """Sea fish only strike near their own depth. Lure in their water and they strike far more often."""
        if self.area == "pond":
            return 1.0
        lo, hi = fish.depth_range
        return 1.6 if lo - 30 <= self.lure_y <= hi + 30 else 0.35

    def depth_layer(self):
        if self.lure_y < SURFACE_Y:
            return "Surface"
        return "Mid" if self.lure_y < MID_Y else "Deep"

    def adjust_clutch(self, step):
        self.clutch = round(min(2.0, max(0.4, self.clutch + 0.2 * step)), 1)
        self.say(f"Drag {self.clutch:.1f}x", 60)

    def pond_layer(self):
        """The layer the bait is nearest to: Top, Middle or Bottom."""
        return min(POND_LAYERS, key=lambda name: abs(POND_LAYERS[name] - self.lure_y))

    def rhythm(self):
        """How many taps in a row are still in rhythm with the jig."""
        return self.combo if self.frame - self.last_jerk < RHYTHM_FRAMES else 0

    def count_jerk(self):
        self.combo = min(5, self.combo + 1 if self.frame - self.last_jerk < RHYTHM_FRAMES else 1)
        self.last_jerk = self.frame
        self.jerks += 1  # Counting jerks tells you how far down the jig has gone
        self.app.sound.play("jig")
        if self.combo >= 3:
            self.say(f"Rhythm x{self.combo}", 40)

    def is_chasing(self, fish):
        return self.rhythm() >= 3 and abs(fish.rect.centerx - self.lure_x) < 90 and abs(fish.rect.centery - self.lure_y) < 60

    def chase(self, fish):
        """Fish that see the jig in rhythm come up to it, which is when the predators strike."""
        fish.x += 2 if fish.rect.centerx < self.lure_x else -2
        fish.y += 1 if fish.rect.centery < self.lure_y else -1
        fish.sync_rect()

    def update_fish(self):
        lure = self.lure_rect()
        for fish in self.fishes[:]:
            if fish is not self.caught_fish:
                fish.update(self.app.weather.mods_for_fish())

            if self.state == IN_WATER:
                if self.scented and fish is not self.caught_fish:
                    self.attract(fish)
                if self.area == "pond" and self.is_biting(fish):
                    self.start_nibbling(fish)
                elif self.area == "boat" and self.is_chasing(fish):
                    self.chase(fish)
                elif self.area != "pond" and lure.colliderect(fish.rect) and random.random() < self.strike_chance(fish):
                    self.start_strike(fish)

            if fish.is_off_screen() and fish is not self.caught_fish:
                self.fishes.remove(fish)
                self.fishes.append(self.spawn())

    def update_tension(self, keys, fish):
        """Reeling while the fish runs spikes the line. Going slack for too long lets the hook pull free."""
        load = fish.weight / self.stats()["strength"]
        running = self.fight_ticks - self.last_lunge < RUN_FRAMES
        if running:
            self.stamina = max(0.0, self.stamina - 0.5 * fish.weight / 3)
        else:
            self.stamina = min(100.0, self.stamina + 0.2)
        if self.stamina < 30 and not self.tired:
            self.say("The fish is tiring!", 120)
        self.tired = self.stamina < 30
        if keys[pygame.K_UP]:
            self.tension += load * (1.6 if running else 0.5) * self.clutch ** 1.2
            self.slack_ticks = 0
            if not running:
                self.fight_progress += 0.08 * self.stats()["speed"] * self.clutch  # Winding in while the fish rests gains line
        elif running:
            self.tension += load * 0.6 * (0.5 if self.tired else 1)  # The fish pulls the line tight, less when tired
        else:
            self.tension = max(0.0, self.tension - TENSION_DECAY)  # Letting go slackens the line
            self.slack_ticks = self.slack_ticks + 1 if self.tension < 20 else 0
        self.tension = min(100.0, self.tension)

        if self.tension > 75:
            self.shake = max(self.shake, (self.tension - 75) / 8)  # The rod trembles near the snapping point
        if self.tension >= 100:
            self.lose_fish("Line snapped! The lure is gone.", snapped=True)
            self.state = RETRACTING
            return True
        if self.slack_ticks > SLACK_FRAMES:
            self.lose_fish("The hook pulled free!")
            self.state = RETRACTING
            return True
        return False

    def lose_fish(self, message, snapped=False):
        self.say(message)
        self.app.sound.play("snap" if snapped else "escape")
        if snapped:
            # The lure goes with the line
            self.app.economy.bait[self.area] = max(0, self.app.economy.bait[self.area] - 1)
        self.caught_fish = None
        self.fishes.append(self.spawn())  # It got away, so another swims in
        self.shake = 12
        self.set_mood("sad", 120)
        self.tension = 0.0
        self.slack_ticks = 0

    def start_strike(self, fish):
        self.caught_fish = fish
        self.fishes.remove(fish)
        self.state = HOOKSET
        self.hookset_wait = HOOKSET_WAIT
        self.hookset_go = False
        self.hookset_ticks = 0
        fish.speed = 0  # Freeze the fish
        self.app.economy.wear_part("hook", 0.3)
        self.shake = 8 + fish.weight * 2  # Heavier fish hit harder
        self.splashes.append([self.lure_x, self.lure_y, 0])
        self.app.sound.play("bite")
        self.set_mood("surprised", 40)
        self.pin_caught_fish()

    def start_fight(self, advantage):
        self.advantage = advantage
        self.state = FIGHTING
        self.shake = 10  # The fish is on, so the rod jolts
        self.reset_fight()

    # --- Drawing ---
    def draw(self, screen):
        self.frame += 1

        # The world is drawn at half resolution, then scaled up for chunky pixels
        world = self.world
        world.blit(self.background, (0, 0))
        self.draw_waves(world)
        self.draw_sparkles(world)
        self.draw_bubbles(world)
        self.draw_splashes(world)
        self.draw_snags(world)
        self.draw_scent(world)
        self.ambience.draw(world)
        self.app.weather.draw_sky(world)
        self.draw_line_and_lure(world)
        self.draw_angler(world)
        for fish in sorted(self.fishes, key=lambda f: f.rect.centery, reverse=True):
            fish.draw(world, self.theme)
        if self.caught_fish:
            self.caught_fish.draw(world, self.theme, self.fish_thrash(), self.frame)
        pixelate(world, screen)
        self.app.weather.draw_tint(screen)

        # UI is drawn sharp on top of the pixel layer
        if self.state in (IDLE, CHARGING):
            self.draw_target(screen, self.aim if self.state == IDLE else self.target)
        if self.state == FIGHTING:
            self.draw_fight_ui(screen)
        elif self.state == SNAGGED:
            self.draw_snag_ui(screen)
        elif self.state == HOOKSET:
            self.draw_hookset_ui(screen)
        elif self.state == CHARGING:
            self.draw_power_meter(screen)

        self.draw_hud(screen)
        self.apply_shake(screen)

    def fish_thrash(self):
        if self.state == FIGHTING:
            return 0.5 + 0.5 * abs(math.sin(self.frame * 0.25)) + 0.2 * self.tug
        if self.state == HOOKSET:
            return 0.3
        return 0.25  # Dangling while it is reeled in

    def apply_shake(self, screen):
        if not self.shake:
            return
        amount = round(self.shake)
        frame = screen.copy()
        screen.blit(self.background, (0, 0))
        screen.blit(frame, (self.fx_rng.randint(-amount, amount), self.fx_rng.randint(-amount, amount)))

    def draw_waves(self, screen):
        wave = self.theme["wave"]
        # Foam along the shoreline, wobbling over time
        foam = []
        for X in range(-GROUND_HALF, GROUND_HALF + 1, 16):
            x, y = ground_point(X, 0)
            foam.append((x, y + 2 * wave * math.sin(X * 0.05 + self.frame * 0.08)))
        pygame.draw.lines(screen, self.theme["foam"], False, foam, 2)

        # Ripples drifting across the water, fainter in deeper rows. They run along the ground, so they narrow with distance.
        span = 2 * GROUND_HALF
        for row in range(WATER_TOP + 14, HEIGHT, 28):
            z = depth_t(row)
            color = lerp_color(water_color(self.theme, row), WHITE, 0.25)
            for i in range(0, span, 60):
                X = (i + self.frame * 0.6 + row * 7) % span - GROUND_HALF
                x0, y0 = ground_point(X, z)
                x1, _ = ground_point(X + 18 * wave, z)
                x2, _ = ground_point(X + 36 * wave, z)
                pygame.draw.lines(screen, color, False, [(x0, y0), (x1, y0 - 2 * wave), (x2, y0)], 1)

    def draw_sparkles(self, screen):
        # Light glinting on the surface
        for i in range(30):
            if (self.frame + i * 5) % 9 == 0:
                X = (i * 97 + self.frame * 2) % (2 * GROUND_HALF) - GROUND_HALF
                y = WATER_TOP + 4 + (i * 53) % (HEIGHT - WATER_TOP - 8)
                x = ground_point(X, depth_t(y))[0]
                if 0 <= x < WIDTH:
                    screen.set_at((int(x), y), lerp_color(water_color(self.theme, y), WHITE, 0.6))

    def draw_bubbles(self, screen):
        for x, y, age in self.bubbles:
            color = lerp_color(water_color(self.theme, y), WHITE, 0.5)
            pygame.draw.circle(screen, color, (int(x), int(y)), 2, 1)

    def draw_splashes(self, screen):
        for x, y, age in self.splashes:
            radius = 4 + age * 1.2
            color = lerp_color(self.theme["foam"], self.theme["shallow"], age / SPLASH_FRAMES)
            pygame.draw.circle(screen, color, (int(x), int(y)), int(radius), 2)

    def draw_line_and_lure(self, screen):
        tip = self.rod_tip()
        lx, ly = int(self.lure_x), int(self.lure_y)

        if self.area == "pond" and self.state in (IN_WATER, HOOKSET):
            # The float sits on the surface, and the line runs from it down to the bait
            # The float bobs erratically on the surface, and dips on each nibble
            bob = math.sin(self.frame * 0.23) * 1.2 + math.sin(self.frame * 0.61) * 0.8
            fx, fy = lx, WATER_TOP + 4 + int(self.float_dip + bob)
            pygame.draw.line(screen, LINE_COLOR, tip, (fx, fy), 1)
            pygame.draw.line(screen, LINE_COLOR, (fx, fy), (lx, ly), 1)
            pygame.draw.circle(screen, BLACK, (fx, fy - 2), 5)
            pygame.draw.circle(screen, RED, (fx, fy - 2), 4)
            pygame.draw.circle(screen, WHITE, (fx, fy + 2), 3)
        else:
            pygame.draw.line(screen, LINE_COLOR, tip, (lx, ly), 1)

        self.draw_lure(screen)

    def draw_lure(self, screen):
        lx, ly = self.lure_x, self.lure_y
        w, h = self.lure_w, self.lure_h

        if self.area == "pond":
            # Worm hanging off the hook
            self.draw_hook(screen, lx, ly, w, h)
            wiggle = math.sin(self.frame * 0.3) * 3
            pygame.draw.lines(screen, WORM_PINK, False, [(lx, ly + h), (lx + wiggle, ly + h + 5), (lx - 2, ly + h + 10)], 2)
        elif self.area == "shore":
            # Paddletail on a jighead, the tail wiggling as it moves
            tail_wiggle = math.sin(self.frame * 0.5) * 3
            pygame.draw.polygon(screen, PADDLE_PINK, [(lx - 3, ly + 12), (lx + 3, ly + 12), (lx + tail_wiggle, ly + 20)])
            pygame.draw.ellipse(screen, PADDLE_PINK, (lx - 6, ly + 4, 12, 10))
            pygame.draw.circle(screen, JIG_SILVER, (int(lx), int(ly + 3)), 5)
            pygame.draw.circle(screen, BLACK, (int(lx), int(ly + 3)), 5, 1)
        else:
            # Metal jig with a flash every few frames
            self.draw_hook(screen, lx, ly, w, h)
            pygame.draw.polygon(screen, OUTLINE, [(lx, ly), (lx + 6, ly + 8), (lx, ly + 19), (lx - 6, ly + 8)])
            pygame.draw.polygon(screen, JIG_SILVER, [(lx, ly), (lx + 5, ly + 8), (lx, ly + 18), (lx - 5, ly + 8)])
            if (self.frame // 8) % 3 == 0:
                pygame.draw.line(screen, WHITE, (lx - 2, ly + 4), (lx + 2, ly + 10), 2)

    def draw_hook(self, screen, lx, ly, w, h):
        x, y = lx - w / 2, ly
        hook_points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h),
                       (x, y + h - 4), (x - 4, y + h - 4),
                       (x - 4, y + h + 4), (x + w + 4, y + h + 4)]
        pygame.draw.polygon(screen, HOOK_GREY, hook_points)

    def draw_angler(self, screen):
        """Draws the angler facing the way he is walking, by flipping his picture when he faces left."""
        centre = int(self.player_x + self.player_width / 2)
        region = pygame.Rect(centre - 70, 0, 141, 140)  # Symmetrical about the middle, so flipping keeps him in place
        self.angler_layer.fill((0, 0, 0, 0), region)
        self.draw_angler_figure(self.angler_layer)
        sprite = pygame.Surface(region.size, pygame.SRCALPHA)
        sprite.blit(self.angler_layer, (0, 0), region)
        if self.facing < 0:
            sprite = pygame.transform.flip(sprite, True, False)
        screen.blit(sprite, region.topleft)

    def draw_angler_figure(self, screen):
        x = self.player_x
        mood = self.current_mood()
        stride = self.stride

        # Shadow on the bank
        pygame.draw.ellipse(screen, self.theme["edge"], (x + 6, 110, 48, 10))
        # Legs swing in opposite directions, and each foot lifts as it steps
        shift = int(round(stride * 2))
        for leg_x, sign, lift in ((x + 16, 1, int(round(max(0.0, stride) * 3))),
                                  (x + 34, -1, int(round(max(0.0, -stride) * 3)))):
            lx = leg_x + sign * shift
            pygame.draw.rect(screen, OUTLINE, (lx - 1, 99 - lift, 10, 22))
            pygame.draw.rect(screen, PANTS, (lx, 100 - lift, 8, 20))
            pygame.draw.rect(screen, OUTLINE, (lx - 2, 117 - lift, 12, 5))
            pygame.draw.rect(screen, (40, 30, 30), (lx - 1, 118 - lift, 10, 3))
        # Body, head and hat, with a dark outline
        pygame.draw.rect(screen, OUTLINE, (x + 11, 65, 38, 40), border_radius=9)
        pygame.draw.rect(screen, SHIRT_RED, (x + 12, 66, 36, 38), border_radius=8)
        pygame.draw.rect(screen, lerp_color(SHIRT_RED, BLACK, 0.3), (x + 12, 92, 36, 4))  # Belt shadow
        pygame.draw.circle(screen, OUTLINE, (x + 30, 58), 11)
        pygame.draw.circle(screen, SKIN, (x + 30, 58), 10)
        pygame.draw.rect(screen, OUTLINE, (x + 17, 45, 28, 10), border_radius=4)
        pygame.draw.rect(screen, HAT_GREEN, (x + 18, 46, 26, 8), border_radius=3)
        self.draw_face(screen, x, mood)

        # Arm and rod
        hand_x, hand_y = self.hand_offset()
        hand = (x + hand_x, hand_y)
        pygame.draw.line(screen, OUTLINE, (x + 40, 74), hand, 6)
        pygame.draw.line(screen, SKIN, (x + 40, 74), hand, 4)
        pygame.draw.line(screen, ROD_BROWN, hand, self.local_rod_tip(), 3)
        pygame.draw.circle(screen, SKIN, hand, 4)

    def draw_face(self, screen, x, mood):
        left, right = (x + 26, 58), (x + 34, 58)
        blinking = self.blink_ticks > 0

        if mood == "surprised":
            for eye in (left, right):
                pygame.draw.circle(screen, WHITE, eye, 3)
                pygame.draw.circle(screen, BLACK, eye, 1)
            pygame.draw.circle(screen, BLACK, (x + 30, 66), 3)  # Open mouth
        elif mood == "happy":
            for ex, ey in (left, right):
                pygame.draw.lines(screen, BLACK, False, [(ex - 3, ey + 1), (ex, ey - 2), (ex + 3, ey + 1)], 2)
            pygame.draw.lines(screen, BLACK, False, [(x + 24, 63), (x + 30, 68), (x + 36, 63)], 2)
        elif mood == "sad":
            pygame.draw.lines(screen, BLACK, False, [(left[0] - 3, left[1] - 2), (left[0] + 3, left[1])], 2)
            pygame.draw.lines(screen, BLACK, False, [(right[0] - 3, right[1]), (right[0] + 3, right[1] - 2)], 2)
            pygame.draw.lines(screen, BLACK, False, [(x + 24, 68), (x + 30, 63), (x + 36, 68)], 2)
            pygame.draw.circle(screen, TEAR_BLUE, (left[0] - 1, left[1] + 6), 2)  # A tear
        elif mood == "strain":
            # Narrowed eyes, clenched teeth and a sweat drop
            pygame.draw.lines(screen, BLACK, False, [(left[0] - 3, left[1] - 2), (left[0] + 3, left[1])], 2)
            pygame.draw.lines(screen, BLACK, False, [(right[0] - 3, right[1]), (right[0] + 3, right[1] - 2)], 2)
            pygame.draw.rect(screen, WHITE, (x + 25, 63, 10, 4))
            pygame.draw.rect(screen, BLACK, (x + 25, 63, 10, 4), 1)
            pygame.draw.polygon(screen, TEAR_BLUE, [(x + 42, 46), (x + 40, 51), (x + 44, 51)])
            pygame.draw.circle(screen, TEAR_BLUE, (x + 42, 52), 2)
        else:  # Neutral, blinking now and then
            for ex, ey in (left, right):
                if blinking:
                    pygame.draw.line(screen, BLACK, (ex - 2, ey), (ex + 2, ey), 1)
                else:
                    pygame.draw.circle(screen, BLACK, (ex, ey), 1)
            pygame.draw.line(screen, BLACK, (x + 26, 64), (x + 34, 64), 1)

    def draw_target(self, screen, point):
        x, y = int(point[0]), int(point[1])
        on_target = self.state == CHARGING and abs(self.cast_power - self.needed_power()) <= self.tolerance()
        colour = GREEN if on_target else (GOLD if self.state == CHARGING else WHITE)
        radius = 10 + int(math.sin(self.frame * 0.2) * 2)
        pygame.draw.circle(screen, BLACK, (x, y), radius + 1, 3)
        pygame.draw.circle(screen, colour, (x, y), radius, 2)
        for dx, dy in ((-14, 0), (14, 0), (0, -14), (0, 14)):
            pygame.draw.line(screen, colour, (x + dx // 2, y + dy // 2), (x + dx, y + dy), 2)

    def draw_power_meter(self, screen):
        # Shown above the angler while the button is held. The white tick marks the power that hits the target.
        x, y, w, h = self.player_x - 5, 22, 70, 10
        needed = self.needed_power()
        pygame.draw.rect(screen, BLACK, (x - 2, y - 2, w + 4, h + 4), border_radius=3)
        pygame.draw.rect(screen, (60, 60, 70), (x, y, w, h))
        tolerance = self.tolerance()
        band_x = x + int(w * max(0.0, needed - tolerance))
        pygame.draw.rect(screen, (60, 160, 60), (band_x, y, max(2, int(w * 2 * tolerance)), h))
        fill = lerp_color((230, 200, 60), (90, 230, 90), self.cast_power)
        pygame.draw.rect(screen, fill, (x, y, int(w * self.cast_power), h))
        pygame.draw.line(screen, WHITE, (x + int(w * needed), y - 3), (x + int(w * needed), y + h + 3), 2)
        spot_on = abs(self.cast_power - needed) <= self.tolerance()
        draw_text(screen, self.small_font, "SPOT ON" if spot_on else "CAST", GOLD if spot_on else WHITE, (x + w // 2, y - 12), center=True)

    def draw_hookset_ui(self, screen):
        centre = (int(self.lure_x), int(self.lure_y) + self.lure_h // 2)
        if not self.hookset_go:
            if (self.frame // 8) % 2 == 0:
                draw_text(screen, self.large_font, "WAIT...", WHITE, (centre[0], centre[1] - 40), center=True)
            return
        pygame.draw.circle(screen, GREEN, centre, HOOKSET_RING_TARGET, 2)  # Target
        pygame.draw.circle(screen, WHITE, centre, int(self.hookset_ring_radius()), 2)  # Shrinking ring
        go_colour = RED if (self.frame // 6) % 2 == 0 else GOLD
        draw_text(screen, self.large_font, "GO!", go_colour, (centre[0], centre[1] - HOOKSET_RING_START - 20), center=True)

    def draw_fight_ui(self, screen):
        fish = self.caught_fish

        # "FISH ON!" with a drop shadow
        draw_text(screen, self.large_font, "FISH ON!", RED, (WIDTH // 2, HEIGHT // 2 - 50), center=True)

        # Progress bar above the gauge
        pygame.draw.rect(screen, (100, 20, 20), (GAUGE_X, PROGRESS_Y, GAUGE_W, PROGRESS_THICK), border_radius=4)
        prog = min(100, max(0, self.fight_progress))
        prog_w = (prog / 100.0) * GAUGE_W
        if prog_w > 0:
            pygame.draw.rect(screen, (90, 230, 90), (GAUGE_X, PROGRESS_Y, prog_w, PROGRESS_THICK), border_radius=4)

        # Gauge background
        pygame.draw.rect(screen, (50, 52, 66), (GAUGE_X, GAUGE_Y, GAUGE_W, GAUGE_THICK), border_radius=6)

        # Player safe zone
        zone_x = GAUGE_X + self.player_bar_x
        zone = pygame.Surface((fish.zone_size, GAUGE_THICK), pygame.SRCALPHA)  # Needs a surface for alpha
        zone.fill(SAFE_ZONE_COLOR)
        screen.blit(zone, (zone_x, GAUGE_Y))
        pygame.draw.rect(screen, (0, 255, 0), (zone_x, GAUGE_Y, fish.zone_size, GAUGE_THICK), 2, border_radius=4)

        # Fish marker
        marker = (int(GAUGE_X + self.fish_marker_x), GAUGE_Y + GAUGE_THICK // 2)
        pygame.draw.circle(screen, fish.color, marker, 10)
        pygame.draw.circle(screen, WHITE, marker, 10, 2)

        # Line tension on the right. It turns red as the line nears its snapping point.
        bar = pygame.Rect(WIDTH - 40, 150, 14, 300)
        pygame.draw.rect(screen, (50, 52, 66), bar, border_radius=6)
        fill_h = int(bar.height * self.tension / 100)
        colour = RED if self.tension > 75 else GOLD if self.tension > 40 else (90, 230, 90)
        pygame.draw.rect(screen, colour, (bar.left, bar.bottom - fill_h, bar.width, fill_h), border_radius=6)
        draw_text(screen, self.small_font, "LINE", WHITE, (bar.centerx, bar.top - 14), center=True)

        # Stamina, next to the line bar. It drains while the fish runs.
        stamina_bar = pygame.Rect(WIDTH - 70, 150, 14, 300)
        pygame.draw.rect(screen, (50, 52, 66), stamina_bar, border_radius=6)
        fill_h = int(stamina_bar.height * self.stamina / 100)
        pygame.draw.rect(screen, (90, 160, 255), (stamina_bar.left, stamina_bar.bottom - fill_h, stamina_bar.width, fill_h), border_radius=6)
        draw_text(screen, self.small_font, "TIRED" if self.tired else "FIGHT", WHITE, (stamina_bar.centerx, stamina_bar.top - 14), center=True)

    def draw_hud(self, screen):
        economy = self.app.economy
        screen.blit(self.panel, (10, HEIGHT - 40))
        status = f"${economy.money}   Bait {economy.bait[self.area]}   Scent {economy.attractant[self.area]}   Creel {len(economy.creel)}/{economy.creel_limit}"
        draw_text(screen, self.small_font, status, WHITE, (20, HEIGHT - 33))
        label = f"{AREA_INFO[self.area]['name']}  -  Esc: back"
        draw_text(screen, self.small_font, label, WHITE, (WIDTH - 10 - self.small_font.size(label)[0], 15))
        draw_text(screen, self.small_font, f"Drag {self.clutch:.1f}x   [ ] or wheel", WHITE, (WIDTH // 2, 14), center=True)
        if self.area == "pond" and self.state == IN_WATER:
            draw_text(screen, self.small_font, self.pond_layer(), GOLD, (int(self.lure_x) + 14, int(self.lure_y) - 8))
        if self.area != "pond":
            self.draw_depth(screen)
        self.draw_status(screen)

    def draw_depth(self, screen):
        """Sea areas: how deep the lure is, which layer that is, and the jerk count for the micro jig."""
        metres = max(0, self.lure_y - WATER_TOP) / DEPTH_PER_METRE
        text = f"Depth {metres:.0f}m  {self.depth_layer()}"
        if self.area == "boat":
            text += f"  Jerks {self.jerks}"
        draw_text(screen, self.small_font, text, WHITE, (WIDTH - 10 - self.small_font.size(text)[0], 40))

    def draw_scent(self, screen):
        """Scent ripples spread out from a scented lure while it is in the water."""
        if not (self.scented and self.state == IN_WATER):
            return
        for ring in range(2):
            radius = (self.frame * 1.2 + ring * 30) % 60
            colour = lerp_color((230, 190, 70), water_color(self.theme, self.lure_y), radius / 60)
            pygame.draw.circle(screen, colour, (int(self.lure_x), int(self.lure_y)), int(radius) + 2, 1)

    def draw_snags(self, screen):
        """Snags are dark stumps on the bottom, so you can see which spots to steer clear of."""
        for snag in self.snags:
            x, y = snag["x"], snag["y"]
            pygame.draw.ellipse(screen, (60, 44, 30), (x - 22, y - 6, 44, 12))
            pygame.draw.ellipse(screen, (110, 80, 50), (x - 18, y - 8, 36, 8))
            pygame.draw.line(screen, (60, 44, 30), (x - 12, y - 6), (x - 18, y - 16), 3)
            pygame.draw.line(screen, (60, 44, 30), (x + 8, y - 6), (x + 14, y - 14), 3)

    def draw_snag_ui(self, screen):
        """The snag mini-game: progress to free the lure on the left, and line tension on the right."""
        draw_text(screen, self.font, "SNAGGED!", RED, (WIDTH // 2, GAUGE_Y - 60), center=True)
        draw_text(screen, self.small_font, "Left / Right alternately to wiggle free. Hold Up to pull.", WHITE, (WIDTH // 2, GAUGE_Y - 36), center=True)

        progress = pygame.Rect(GAUGE_X, GAUGE_Y, GAUGE_W, GAUGE_THICK)
        pygame.draw.rect(screen, (50, 52, 66), progress, border_radius=6)
        fill_w = int(GAUGE_W * min(100.0, self.snag_progress) / 100)
        pygame.draw.rect(screen, (90, 230, 90), (progress.left, progress.top, fill_w, progress.height), border_radius=6)
        draw_text(screen, self.small_font, "FREE", WHITE, (progress.centerx, progress.top - 14), center=True)

        bar = pygame.Rect(WIDTH - 40, 150, 14, 300)
        pygame.draw.rect(screen, (50, 52, 66), bar, border_radius=6)
        fill_h = int(bar.height * self.snag_tension / 100)
        colour = RED if self.snag_tension > 75 else GOLD if self.snag_tension > 40 else (90, 230, 90)
        pygame.draw.rect(screen, colour, (bar.left, bar.bottom - fill_h, bar.width, fill_h), border_radius=6)
        draw_text(screen, self.small_font, "LINE", WHITE, (bar.centerx, bar.top - 14), center=True)

    def draw_status(self, screen):
        """Top left: the weather, the clock, and the tide."""
        weather = self.app.weather
        panel = pygame.Rect(10, 8, 340, 44)
        draw_panel(screen, panel)
        weather.draw_icon(screen, (panel.left + 26, panel.centery))
        draw_text(screen, self.small_font, weather.name, WHITE, (panel.left + 50, panel.top + 4))
        draw_text(screen, self.small_font, weather.moon() + " moon", GREY, (panel.left + 50, panel.top + 24))

        # The clock shows the time, and a feeding frenzy takes over the phase label
        frenzy = weather.frenzy()
        hour = weather.hour()
        draw_text(screen, self.small_font, f"{int(hour):02d}:{int(hour % 1 * 60):02d}", RED if frenzy else GOLD, (panel.left + 150, panel.top + 4))
        draw_text(screen, self.small_font, "FRENZY" if frenzy else weather.phase(), RED if frenzy else WHITE, (panel.left + 150, panel.top + 24))

        # Tide gauge: the water level rises and falls, and the arrow shows which way it is going
        bar = pygame.Rect(panel.left + 220, panel.top + 8, 10, 28)
        pygame.draw.rect(screen, (50, 52, 66), bar, border_radius=4)
        level = int(bar.height * (weather.tide() + 1) / 2)
        pygame.draw.rect(screen, (90, 170, 230), (bar.left, bar.bottom - level, bar.width, level), border_radius=4)
        arrow = "^" if weather.tide_name() == "rising" else "v"
        draw_text(screen, self.small_font, f"{arrow} tide {weather.tide_name()}", WHITE, (panel.left + 238, panel.top + 13))
        if self.message_ticks:
            draw_text(screen, self.small_font, self.message, GOLD, (WIDTH // 2, 60), center=True)
