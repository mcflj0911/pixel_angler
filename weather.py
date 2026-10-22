import math
import random

import pygame

from config import WIDTH, HEIGHT

# What each weather does to the fish and to the cast.
#   speed: how fast fish swim and zig-zag   depth: how far the fish shift (negative is up, towards the surface)
#   bite: how often fish take the bait      accuracy: how forgiving a cast is (1 is normal)
#   wind: how hard the lure is pushed about in the water
STATES = {
    "Clear": {"speed": 1.0, "depth": 0, "bite": 1.0, "accuracy": 1.0, "wind": 0.0},
    "Cloudy": {"speed": 1.1, "depth": -20, "bite": 1.2, "accuracy": 1.0, "wind": 0.0},
    "Windy": {"speed": 1.25, "depth": 0, "bite": 0.9, "accuracy": 0.8, "wind": 1.0},
    "Rain": {"speed": 1.0, "depth": -60, "bite": 1.35, "accuracy": 0.9, "wind": 0.3},
    "Storm": {"speed": 0.6, "depth": 50, "bite": 0.5, "accuracy": 0.6, "wind": 1.0},
}

CHANGE_MIN, CHANGE_MAX = 1500, 3000  # Frames between changes, 25 to 50 seconds at 60 FPS
FORECAST_FRAMES = 900  # The last 15 seconds before a change, when the next weather can be forecast
BLEND = 0.01  # How quickly the conditions drift from one weather to the next
RAIN_DROPS = {"Rain": 50, "Storm": 110}
CLOUDY = ("Cloudy", "Rain", "Storm")
TINT = {"Cloudy": 18, "Rain": 40, "Storm": 85}  # How dark the sky goes
DAY_FRAMES = 28800  # A full day lasts 8 minutes, so the dusk and the night last longer
MOON_NAMES = ["New", "Waxing C.", "1st Qtr", "Waxing G.", "Full", "Waning G.", "3rd Qtr", "Waning C."]
TIDE_FRAMES = 10800  # One tide cycle lasts 3 minutes
PHASE_TINT = {"Dawn": (255, 150, 90, 40), "Day": None, "Dusk": (255, 110, 60, 50), "Night": (10, 20, 70, 120)}
CLOUD = (226, 232, 240)
RAIN = (170, 196, 230)
WIND = (214, 226, 236)


class Weather:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)  # Its own random stream, so the fish are not affected
        self.name = "Clear"
        self.mods = dict(STATES["Clear"])  # Blends smoothly towards the current weather's values
        self.timer = self.rng.randint(CHANGE_MIN, CHANGE_MAX)
        self.next_name = self.pick_next()  # The weather coming after this one, chosen early so it can be forecast
        self.frame = 0
        self.flash = 0  # Frames of lightning left
        self.clock = 0  # Frames since the game started, which drives the day and the tides
        self.overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    def pick_next(self):
        return self.rng.choice([name for name in STATES if name != self.name])

    def forecast(self):
        """The weather coming next, once it is near enough to be forecast (FORECAST_FRAMES before the change). Otherwise None."""
        return self.next_name if self.timer <= FORECAST_FRAMES else None

    def update(self):
        self.frame += 1
        self.clock += 1
        self.timer -= 1
        if self.timer <= 0:
            self.name = self.next_name
            self.timer = self.rng.randint(CHANGE_MIN, CHANGE_MAX)
            self.next_name = self.pick_next()
        for key, value in STATES[self.name].items():
            self.mods[key] += (value - self.mods[key]) * BLEND
        if self.name == "Storm" and self.rng.random() < 0.004:
            self.flash = 10

    def phase(self):
        """Dawn, Day, Dusk or Night. Dawn and dusk are the golden hours."""
        t = (self.clock % DAY_FRAMES) / DAY_FRAMES
        if t < 0.12:
            return "Dawn"
        if t < 0.5:
            return "Day"
        if t < 0.62:
            return "Dusk"
        return "Night"

    def activity(self, kind):
        """How active a species is now. Fish feed in their own part of the day, and rest at other times."""
        phase = self.phase()
        active = {"golden": phase in ("Dawn", "Dusk"), "day": phase == "Day", "night": phase == "Night"}[kind]
        return 1.5 if active else 0.5

    def hour(self):
        """The time of day as a 24 hour clock. Dawn is 6 o'clock, so the day runs from dawn to dawn."""
        t = (self.clock % DAY_FRAMES) / DAY_FRAMES
        return (6 + t * 24) % 24

    def draw_icon(self, surface, center):
        """A small picture of the current weather, for the status panel."""
        x, y = center
        if self.name == "Clear":
            pygame.draw.circle(surface, (255, 220, 90), (x, y), 8)
            return
        if self.name == "Windy":
            for dy, length in ((-5, 18), (0, 14), (5, 18)):
                pygame.draw.line(surface, WIND, (x - 10, y + dy), (x - 10 + length, y + dy), 2)
            return
        cloud = (120, 128, 140) if self.name == "Storm" else CLOUD
        for dx, r in ((-5, 5), (2, 7), (8, 4)):
            pygame.draw.circle(surface, cloud, (x + dx, y - 2), r)
        pygame.draw.rect(surface, cloud, (x - 9, y - 2, 20, 6))
        if self.name == "Rain":
            for dx in (-5, 3):
                pygame.draw.line(surface, RAIN, (x + dx, y + 7), (x + dx - 2, y + 11), 2)
        if self.name == "Storm":
            pygame.draw.polygon(surface, (255, 230, 60), [(x + 1, y + 4), (x - 3, y + 10), (x, y + 10), (x - 2, y + 15), (x + 4, y + 8), (x + 1, y + 8)])

    def moon(self):
        """The lunar phase. Each game day is one moon day, so the moon goes round in 8 game days."""
        return MOON_NAMES[(self.clock // DAY_FRAMES) % 8]

    def frenzy(self):
        """Solunar peaks: dawn and dusk always, and midday too on new and full moons. Fish feed hard."""
        t = (self.clock % DAY_FRAMES) / DAY_FRAMES
        if 0.02 <= t < 0.10 or 0.50 <= t < 0.58:
            return True
        major = (self.clock // DAY_FRAMES) % 8 in (0, 4)
        return major and 0.30 <= t < 0.36

    def mods_for_fish(self):
        """The weather modifiers as the fish feel them. Frenzying fish rise towards the surface."""
        mods = dict(self.mods)
        if self.frenzy():
            mods["depth"] -= 40
        return mods

    def tide(self):
        return math.sin(2 * math.pi * self.clock / TIDE_FRAMES)

    def tide_name(self):
        return "rising" if math.cos(2 * math.pi * self.clock / TIDE_FRAMES) > 0 else "falling"

    def strike_mult(self):
        """Moving water sweeps baitfish past the structure, so strikes come more often while the tide runs hard."""
        return 0.7 + 0.6 * abs(self.tide())

    def draw_sky(self, surface):
        """Clouds, rain and wind streaks, drawn on the pixel layer."""
        frame = self.frame
        if self.name in CLOUDY:
            for i in range(4):
                x = (i * 210 + frame * 0.3) % (WIDTH + 140) - 70
                pygame.draw.ellipse(surface, CLOUD, (x, 18 + (i % 2) * 16, 110, 26))
        for i in range(RAIN_DROPS.get(self.name, 0)):
            x = (i * 97 + frame * 3) % WIDTH
            y = (i * 53 + frame * 9) % HEIGHT
            pygame.draw.line(surface, RAIN, (x, y), (x - 3, y + 8))
        if self.name == "Windy":
            for i in range(14):
                x = (i * 71 - frame * 14) % (WIDTH + 80) - 40
                y = 140 + (i * 37) % (HEIGHT - 160)
                pygame.draw.line(surface, WIND, (x, y), (x + 26, y), 1)

    def draw_tint(self, screen):
        """Darkens the sky in bad weather, and flashes with lightning in a storm."""
        alpha = TINT.get(self.name, 0)
        self.overlay.fill((10, 16, 40, alpha))
        screen.blit(self.overlay, (0, 0))
        tint = PHASE_TINT[self.phase()]
        if tint:
            self.overlay.fill(tint)
            screen.blit(self.overlay, (0, 0))
        if self.flash:
            self.flash -= 1
            self.overlay.fill((255, 255, 255, 14 * self.flash))
            screen.blit(self.overlay, (0, 0))
