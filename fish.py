import math
import random

import pygame

from config import WIDTH, HEIGHT, WHITE, BLACK
from draw import WATER_TOP, depth_t, lerp_color, perspective_scale, water_color

# Species for each area. Bigger fish sit deeper, pay more and fight harder.
# zone: length of the safe zone on the fight gauge. zig_*: how the fish zig-zags through the water.
# belly: underside colour. look: tail shape, dorsal fin, markings and extras (see Fish.draw).
# pause: (chance per frame to stop, frames stopped). dash: (chance per frame to burst, speed multiplier, frames).
SPECIES = {
    "pond": [
        {"name": "Bluegill", "active": "day","size": (26, 14), "color": (70, 130, 200), "speed_range": [-3, -2, 2, 3],
         "price": 18, "weight": 0.5, "depth": (150, 260), "zone": 170, "fish_speed": 2, "aggression": (40, 80),
         "zig_speed": 0.4, "zig_frames": (40, 90), "rarity": 60,
         "belly": (236, 150, 70), "look": {"tail": "round", "dorsal": "spiny", "marks": "bars", "extras": ["gill"]},
         "pause": (0.006, (40, 120))},
        {"name": "Carp", "active": "night","size": (50, 24), "color": (196, 140, 60), "speed_range": [-2, -1, 1, 2],
         "price": 55, "weight": 2, "depth": (220, 430), "zone": 120, "fish_speed": 3, "aggression": (20, 50),
         "zig_speed": 0.5, "zig_frames": (50, 100), "rarity": 30,
         "belly": (232, 200, 120), "look": {"tail": "fork", "dorsal": "long", "marks": "scales", "extras": ["barbels"]},
         "pause": (0.01, (90, 240))},
        # Hidden: only comes to an angler who has finished a townsfolk's job, and only bites at night
        {"name": "Moonlit Bream", "active": "night", "requires": {"jobs_done": 1}, "size": (34, 16), "color": (150, 200, 230),
         "speed_range": [-3, -2, 2, 3], "price": 140, "weight": 1.5, "depth": (200, 360), "zone": 140, "fish_speed": 3,
         "aggression": (30, 60), "zig_speed": 0.5, "zig_frames": (50, 100), "rarity": 8,
         "belly": (230, 240, 250), "look": {"tail": "fork", "dorsal": "long", "marks": "bars", "extras": []},
         "pause": (0.01, (90, 240))},
        {"name": "Largemouth Bass", "active": "golden", "requires": {"rating": 4},"size": (58, 26), "color": (70, 110, 60), "speed_range": [-3, -2, 2, 3],
         "price": 160, "weight": 3.5, "depth": (260, 380), "zone": 80, "fish_speed": 6, "aggression": (10, 30),
         "zig_speed": 1.0, "zig_frames": (20, 40), "rarity": 10,
         "belly": (215, 215, 165), "look": {"tail": "round", "dorsal": "split", "marks": "blotches", "extras": ["big_mouth"]},
         "pause": (0.02, (80, 220)), "dash": (0.01, 3.0, (10, 18))},
        {"name": "Perch", "active": "day", "size": (32, 18), "color": (200, 160, 60), "speed_range": [-3, -2, 2, 3],
         "price": 24, "weight": 0.4, "depth": (120, 220), "zone": 160, "fish_speed": 2, "aggression": (40, 80),
         "zig_speed": 0.5, "zig_frames": (40, 90), "rarity": 50,
         "belly": (240, 230, 200), "look": {"tail": "fork", "dorsal": "spiny", "marks": "bars", "extras": ["gill"]},
         "pause": (0.008, (40, 120))},
        {"name": "Pike", "active": "night", "requires": {"strength": 4}, "size": (72, 22), "color": (90, 120, 70), "speed_range": [-3, 3],
         "price": 120, "weight": 3, "depth": (180, 300), "zone": 90, "fish_speed": 6, "aggression": (10, 25),
         "zig_speed": 0.8, "zig_frames": (20, 40), "rarity": 12,
         "belly": (220, 220, 170), "look": {"tail": "fork", "dorsal": "small", "marks": "spots", "extras": ["big_mouth"]},
         "dash": (0.02, 3.0, (8, 16))},
        {"name": "Catfish", "active": "night", "size": (50, 20), "color": (80, 80, 90), "speed_range": [-1, 1],
         "price": 65, "weight": 2, "depth": (300, 460), "zone": 110, "fish_speed": 2, "aggression": (20, 40),
         "zig_speed": 0.4, "zig_frames": (60, 120), "rarity": 25,
         "belly": (200, 200, 200), "look": {"tail": "round", "dorsal": "small", "marks": "none", "extras": ["barbels"]},
         "pause": (0.012, (120, 260))},
    ],
    "shore": [
        {"name": "Mullet", "active": "night","size": (25, 12), "color": (120, 140, 160), "speed_range": [-5, -4, 4, 5],
         "price": 22, "weight": 0, "depth": (200, 300), "zone": 168, "fish_speed": 2, "aggression": (40, 80),
         "zig_speed": 0.5, "zig_frames": (40, 90), "rarity": 60,
         "belly": (235, 238, 240), "look": {"tail": "fork", "dorsal": "small", "marks": "stripes", "extras": []},
         "dash": (0.01, 1.8, (10, 25))},
        {"name": "Trevally", "active": "golden","size": (45, 20), "color": (110, 190, 220), "speed_range": [-3, -2, 2, 3],
         "price": 75, "weight": 2, "depth": (300, 450), "zone": 108, "fish_speed": 6, "aggression": (10, 30),
         "zig_speed": 1.3, "zig_frames": (14, 30), "rarity": 30,
         "belly": (225, 235, 240), "look": {"tail": "crescent", "dorsal": "two", "marks": "none", "extras": ["gill_spot"]},
         "dash": (0.008, 2.0, (14, 30))},
        {"name": "Grouper", "active": "night", "requires": {"strength": 5},"size": (80, 30), "color": (150, 70, 60), "speed_range": [-1, 1],
         "price": 190, "weight": 4.5, "depth": (450, 560), "zone": 60, "fish_speed": 3, "aggression": (30, 60),
         "zig_speed": 0.3, "zig_frames": (60, 120), "rarity": 10,
         "belly": (205, 160, 120), "look": {"tail": "round", "dorsal": "spiny", "marks": "spots", "extras": ["big_mouth"]},
         "pause": (0.02, (120, 300)), "dash": (0.001, 2.2, (10, 20))},
        {"name": "Snapper", "active": "day", "size": (46, 20), "color": (200, 70, 70), "speed_range": [-3, -2, 2, 3],
         "price": 90, "weight": 2, "depth": (280, 400), "zone": 105, "fish_speed": 4, "aggression": (20, 40),
         "zig_speed": 1.0, "zig_frames": (20, 40), "rarity": 25,
         "belly": (240, 200, 190), "look": {"tail": "fork", "dorsal": "long", "marks": "none", "extras": ["gill_spot"]},
         "dash": (0.01, 2.0, (12, 24))},
        {"name": "Barracuda", "active": "golden", "requires": {"strength": 4}, "size": (70, 18), "color": (150, 160, 170),
         "speed_range": [-4, 4], "price": 140, "weight": 2.5, "depth": (330, 460), "zone": 90, "fish_speed": 7, "aggression": (10, 25),
         "zig_speed": 1.4, "zig_frames": (10, 20), "rarity": 15,
         "belly": (235, 235, 240), "look": {"tail": "fork", "dorsal": "split", "marks": "bars", "extras": ["big_mouth"]},
         "dash": (0.012, 2.4, (10, 18))},
        {"name": "Bonito", "active": "day", "size": (44, 16), "color": (60, 90, 200), "speed_range": [-4, -3, 3, 4],
         "price": 70, "weight": 1.5, "depth": (250, 380), "zone": 110, "fish_speed": 6, "aggression": (10, 30),
         "zig_speed": 1.2, "zig_frames": (12, 26), "rarity": 25,
         "belly": (240, 240, 250), "look": {"tail": "crescent", "dorsal": "small", "marks": "wavy", "extras": ["finlets"]},
         "dash": (0.008, 1.6, (14, 28))},
    ],
    "boat": [
        {"name": "Mackerel", "active": "day","size": (48, 16), "color": (60, 120, 160), "speed_range": [-4, -3, 3, 4],
         "price": 50, "weight": 1, "depth": (200, 330), "zone": 110, "fish_speed": 6, "aggression": (8, 20),
         "zig_speed": 1.5, "zig_frames": (10, 25), "rarity": 60,
         "belly": (235, 235, 230), "look": {"tail": "fork", "dorsal": "two", "marks": "wavy", "extras": ["finlets"]},
         "dash": (0.006, 1.4, (20, 40))},
        {"name": "Yellowfin Tuna", "active": "golden", "requires": {"strength": 5},"size": (90, 34), "color": (240, 190, 40), "speed_range": [-2, -1, 1, 2],
         "price": 260, "weight": 5, "depth": (330, 470), "zone": 70, "fish_speed": 4, "aggression": (20, 40),
         "zig_speed": 0.8, "zig_frames": (40, 80), "rarity": 30,
         "belly": (245, 240, 215), "look": {"tail": "crescent", "dorsal": "two", "marks": "gold_stripe", "extras": ["finlets"]},
         "dash": (0.004, 1.5, (30, 60))},
        {"name": "Sailfish", "active": "day", "requires": {"rating": 6, "strength": 8},"size": (110, 28), "color": (90, 110, 200), "speed_range": [-3, 3],
         "price": 750, "weight": 6, "depth": (420, 560), "zone": 50, "fish_speed": 7, "aggression": (8, 20),
         "zig_speed": 1.2, "zig_frames": (15, 30), "rarity": 10,
         "belly": (215, 220, 235), "look": {"tail": "crescent", "dorsal": "sail", "marks": "spots", "extras": ["bill"]},
         "dash": (0.005, 2.5, (12, 25))},
        {"name": "Amberjack", "active": "day", "requires": {"strength": 4}, "size": (75, 28), "color": (200, 160, 60),
         "speed_range": [-2, 2], "price": 150, "weight": 4, "depth": (340, 480), "zone": 80, "fish_speed": 5, "aggression": (15, 35),
         "zig_speed": 0.9, "zig_frames": (30, 60), "rarity": 20,
         "belly": (240, 230, 200), "look": {"tail": "crescent", "dorsal": "two", "marks": "stripes", "extras": ["gill"]},
         "dash": (0.006, 1.8, (18, 36))},
        {"name": "Mahi-Mahi", "active": "day", "requires": {"rating": 5}, "size": (84, 26), "color": (80, 200, 120),
         "speed_range": [-4, -3, 3, 4], "price": 300, "weight": 4.5, "depth": (300, 420), "zone": 70, "fish_speed": 6, "aggression": (10, 25),
         "zig_speed": 1.3, "zig_frames": (14, 30), "rarity": 18,
         "belly": (240, 240, 120), "look": {"tail": "fork", "dorsal": "long", "marks": "spots", "extras": ["finlets"]},
         "dash": (0.01, 2.2, (14, 28))},
        {"name": "Blue Marlin", "active": "golden", "requires": {"rating": 7, "strength": 9}, "size": (120, 34), "color": (40, 80, 190),
         "speed_range": [-2, 2], "price": 900, "weight": 7, "depth": (420, 560), "zone": 45, "fish_speed": 8, "aggression": (6, 16),
         "zig_speed": 1.1, "zig_frames": (20, 40), "rarity": 6,
         "belly": (220, 230, 245), "look": {"tail": "crescent", "dorsal": "long", "marks": "bars", "extras": ["bill"]},
         "dash": (0.004, 2.6, (14, 26))},
    ],
}


def tail_outline(style, x, cy, d, size, flap):
    """The tail fin, with its base at x. flap swings the tips while the fish thrashes. d is the direction the fish faces."""
    if style == "round":
        arc = [(x - d * size * math.cos(i * math.pi / 8), cy + size * math.sin(i * math.pi / 8) + flap * 0.5 * math.sin(i * math.pi / 8)) for i in range(-4, 5)]
        return [(x, cy)] + arc
    notch = 0.2 if style == "crescent" else 0.5  # A crescent has a deeper notch than a forked tail
    tip = x - d * size
    return [(x, cy), (tip, cy - size + flap), (x - d * size * notch, cy), (tip, cy + size + flap)]


class Fish:
    def __init__(self, spec):
        self.name = spec["name"]
        self.width, self.height = spec["size"]
        self.color = spec["color"]
        self.price = spec["price"]
        self.weight = spec["weight"]
        self.depth_range = spec["depth"]
        self.zone_size = spec["zone"]  # Length of the player's safe zone on the gauge
        self.fish_speed = spec["fish_speed"]  # How fast the fish moves on the gauge
        self.aggression = spec["aggression"]  # (min, max) frames before changing direction
        self.zig_speed = spec["zig_speed"]  # How fast the fish climbs or dives
        self.zig_frames = spec["zig_frames"]  # (min, max) frames before turning around
        self.belly = spec.get("belly")  # Underside colour, if it is not just a shade of the body
        self.look = spec.get("look", {})  # Tail, fins, markings and extras that tell the species apart
        self.pause_rate, self.pause_frames = spec.get("pause", (0, (0, 0)))  # Stops from time to time, such as resting on the bottom
        self.dash_rate, self.dash_mult, self.dash_frames = spec.get("dash", (0, 1, (0, 0)))  # Bursts of speed, such as chasing bait
        self.pause_ticks = 0
        self.dash_ticks = 0

        self.speed = random.choice(spec["speed_range"])
        self.facing = 1 if self.speed >= 0 else -1  # Kept after the fish is caught and its speed is zeroed
        self.y = random.randint(*self.depth_range)
        self.x = -self.width if self.speed > 0 else WIDTH
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.active = spec["active"]  # "day", "night" or "golden" (dawn and dusk)
        self.lbs = round(self.weight * random.uniform(0.7, 1.4) + 0.1, 2)  # Recorded in the journal
        if self.weight:  # A bigger fish of the same kind sells for more. Tiny species with no weight keep their base price.
            self.price = max(1, round(self.price * self.lbs / self.weight))
        self.length = round(self.width * random.uniform(1.5, 2.5), 1)  # In cm
        self.zig_dir = random.choice((-1, 1))
        self.zig_timer = random.randint(*self.zig_frames)

    def pace(self):
        """Ticks through any pause or dash, and returns how fast the fish moves this frame."""
        if self.pause_ticks > 0:
            self.pause_ticks -= 1
            return 0.0
        if self.dash_ticks > 0:
            self.dash_ticks -= 1
            return self.dash_mult
        if random.random() < self.pause_rate:
            self.pause_ticks = random.randint(*self.pause_frames)
            return 0.0
        if random.random() < self.dash_rate:
            self.dash_ticks = random.randint(*self.dash_frames)
            return self.dash_mult
        return 1.0

    def update(self, weather=None):
        """weather: the current weather's modifiers. Fish swim faster or slower, and shift up or down in the water."""
        speed = weather["speed"] if weather else 1.0
        shift = weather["depth"] if weather else 0
        pace = self.pace()
        self.x += self.speed * speed * pace

        self.zig_timer -= 1
        top, bottom = self.depth_range
        top, bottom = max(WATER_TOP + 20, top + shift), min(HEIGHT - 40, bottom + shift)
        if self.zig_timer <= 0 or (self.y <= top and self.zig_dir < 0) or (self.y >= bottom and self.zig_dir > 0):
            self.zig_dir = -self.zig_dir
            self.zig_timer = random.randint(*self.zig_frames)
        self.y = min(bottom, max(top, self.y + self.zig_dir * self.zig_speed * speed * pace))

        self.sync_rect()

    def sync_rect(self):
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def is_off_screen(self):
        return self.x > WIDTH + 50 or self.x < -self.width - 50

    def draw(self, surface, theme, thrash=0.0, t=0.0):
        """thrash: 0 for a calm fish, higher while it is fighting the hook. t drives the animation."""
        cy = self.rect.centery
        s = perspective_scale(cy)
        # Deeper fish fade into the water
        fade = 0.35 * depth_t(cy)
        color = lerp_color(self.color, water_color(theme, cy), fade)
        shade = lerp_color(color, BLACK, 0.35)
        outline = lerp_color(color, BLACK, 0.8)
        belly = lerp_color(self.belly or shade, water_color(theme, cy), fade)
        mark = lerp_color(color, BLACK, 0.5)  # Spots, bars and stripes
        fin_colour = lerp_color(color, BLACK, 0.15)

        bw, bh = int(self.width * s), int(self.height * s)
        tail = 10 * s

        # Draw onto a transparent canvas so the whole fish can be rotated while it thrashes
        pad = int(max(bw, bh) * 1.2)
        sprite = pygame.Surface((bw + 2 * pad, bh + 2 * pad), pygame.SRCALPHA)
        cx, cy0 = sprite.get_rect().center
        body = pygame.Rect(0, 0, bw, bh)
        body.center = (cx, cy0)

        # d is the way the fish faces. at(f) is the x of a point f of the way from the tail end (0) to the head (1)
        d = self.facing

        def at(f):
            return body.left + bw * f if d > 0 else body.right - bw * f

        def y_at(v):
            return body.centery + bh * v

        flap = math.sin(t * 1.6) * thrash * 8 * s  # Tail beats while fighting
        tail_points = tail_outline(self.look.get("tail", "fork"), at(0) + d * 5 * s, cy0, d, tail, flap)
        eye_pos = (at(1) - d * 10 * s, cy0 - 3 * s)

        top, bottom = body.top + bh * 0.2, body.bottom - bh * 0.2
        fins = self.fins(body, at, top, bottom, d)

        # Dark outline first, offset in each direction, so the fish reads clearly against the water
        shapes = [tail_points] + fins
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            for shape in shapes:
                pygame.draw.polygon(sprite, outline, [(x + dx, y + dy) for x, y in shape])
            pygame.draw.ellipse(sprite, outline, body.move(dx, dy))

        pygame.draw.polygon(sprite, color, tail_points)
        for fin in fins:
            pygame.draw.polygon(sprite, fin_colour, fin)
        pygame.draw.ellipse(sprite, color, body)

        # Pale belly along the bottom of the body
        belly_rect = pygame.Rect(int(body.left + bw * 0.1), int(body.centery + bh * 0.1), int(bw * 0.8), int(bh * 0.4))
        pygame.draw.ellipse(sprite, belly, belly_rect)

        # Light stripe along the top of the body
        highlight = pygame.Rect(0, 0, int(bw * 0.5), int(bh * 0.25))
        highlight.center = (body.centerx, int(body.top + bh * 0.3))
        pygame.draw.ellipse(sprite, lerp_color(color, WHITE, 0.35), highlight)

        self.draw_marks(sprite, body, at, s, mark)
        self.draw_extras(sprite, body, at, d, s, mark)

        eye = (int(eye_pos[0]), int(eye_pos[1]))
        pygame.draw.circle(sprite, BLACK, eye, max(2, int(4 * s)))
        pygame.draw.circle(sprite, WHITE, eye, max(1, int(3 * s)))
        pygame.draw.circle(sprite, BLACK, eye, max(1, int(2 * s)))

        if thrash:
            # A gentle tilt and bob. The side-to-side swim comes from the game moving the fish.
            sprite = pygame.transform.rotate(sprite, math.sin(t * 1.1) * thrash * 6)
        offset_y = math.cos(t * 1.3) * thrash * 3
        surface.blit(sprite, sprite.get_rect(center=(self.rect.centerx, self.rect.centery + offset_y)))

    def fins(self, body, at, top, bottom, d):
        """Every fin as a polygon. The dorsal fin depends on the species, the rest are common to all."""
        bh = body.height
        fins = []
        dorsal = self.look.get("dorsal")
        if dorsal == "spiny":
            fins.append([(at(0.3), top), (at(0.45), body.top - bh * 0.45), (at(0.65), top)])
        elif dorsal == "long":
            fins.append([(at(0.25), top), (at(0.4), body.top - bh * 0.3), (at(0.8), body.top - bh * 0.25), (at(0.85), top)])
        elif dorsal == "split":
            fins.append([(at(0.3), top), (at(0.4), body.top - bh * 0.5), (at(0.55), top)])
            fins.append([(at(0.6), top), (at(0.75), body.top - bh * 0.4), (at(0.85), top)])
        elif dorsal == "two":
            fins.append([(at(0.3), top), (at(0.4), body.top - bh * 0.4), (at(0.5), top)])
            fins.append([(at(0.52), top), (at(0.6), body.top - bh * 0.3), (at(0.7), top)])
        elif dorsal == "small":
            fins.append([(at(0.4), top), (at(0.5), body.top - bh * 0.2), (at(0.6), top)])
        elif dorsal == "sail":
            height = bh * (1.6 if self.dash_ticks else 1.1)  # The sailfish raises its sail when it bursts after bait
            fins.append([(at(0.2), top), (at(0.4), body.top - height), (at(0.7), body.top - height * 0.6), (at(0.8), top)])

        if "finlets" in self.look.get("extras", []):
            for f in (0.1, 0.18):
                fins.append([(at(f), top), (at(f + 0.03), body.top - bh * 0.15), (at(f + 0.06), top)])
                fins.append([(at(f), bottom), (at(f + 0.03), body.bottom + bh * 0.15), (at(f + 0.06), bottom)])

        fins.append([(at(0.25), bottom), (at(0.35), body.bottom + bh * 0.18), (at(0.45), bottom)])  # Anal fin
        fins.append([(at(0.72), body.centery + bh * 0.05), (at(0.6), body.centery + bh * 0.35), (at(0.66), body.centery + bh * 0.1)])  # Pectoral

        if "bill" in self.look.get("extras", []):
            fins.append([(at(0.98), body.centery - bh * 0.08), (at(0.98) + d * body.width * 0.25, body.centery), (at(0.98), body.centery + bh * 0.08)])
        return fins

    def draw_marks(self, sprite, body, at, s, colour):
        """Patterns that tell the species apart, such as spots, bars and stripes."""
        bh = body.height
        mid = body.centery
        style = self.look.get("marks", "none")
        if style == "spots":
            for f, v in ((0.2, -0.2), (0.32, 0.1), (0.45, -0.25), (0.5, 0.15), (0.62, -0.05), (0.7, -0.22), (0.78, 0.12), (0.4, 0.3)):
                pygame.draw.circle(sprite, colour, (int(at(f)), int(mid + bh * v)), max(1, int(1.5 * s)))
        elif style == "bars":
            for f in (0.3, 0.42, 0.54, 0.66):
                pygame.draw.line(sprite, colour, (int(at(f)), int(body.top + bh * 0.15)), (int(at(f)), int(body.bottom - bh * 0.15)), max(1, int(s)))
        elif style == "stripes":
            for v in (-0.2, 0, 0.2):
                pygame.draw.line(sprite, colour, (int(at(0.15)), int(mid + bh * v)), (int(at(0.9)), int(mid + bh * v)), 1)
        elif style == "blotches":
            for f in (0.3, 0.45, 0.6, 0.75):
                rect = pygame.Rect(0, 0, int(body.width * 0.1), int(bh * 0.3))
                rect.center = (int(at(f)), mid)
                pygame.draw.ellipse(sprite, colour, rect)
        elif style == "wavy":
            for f in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7):
                wave = [(int(at(f)), int(body.top + bh * 0.1)), (int(at(f + 0.04)), int(body.top + bh * 0.3)), (int(at(f + 0.08)), int(body.top + bh * 0.1))]
                pygame.draw.lines(sprite, colour, False, wave, 1)
        elif style == "gold_stripe":
            pygame.draw.line(sprite, (250, 205, 60), (int(at(0.12)), mid), (int(at(0.9)), mid), max(1, int(2 * s)))
        elif style == "scales":
            for row in range(3):
                for col in range(5):
                    pos = (int(at(0.25 + col * 0.12)), int(mid + bh * (-0.25 + row * 0.25)))
                    pygame.draw.circle(sprite, colour, pos, max(1, int(2 * s)), 1)

    def draw_extras(self, sprite, body, at, d, s, colour):
        """Features on the head and gills, such as barbels, a big mouth or a gill flap."""
        bh = body.height
        mid = body.centery
        extras = self.look.get("extras", [])
        if "gill" in extras:
            flap = pygame.Rect(0, 0, max(2, int(body.width * 0.08)), int(bh * 0.5))
            flap.center = (int(at(0.8)), mid)
            pygame.draw.ellipse(sprite, colour, flap)
        if "gill_spot" in extras:
            pygame.draw.circle(sprite, colour, (int(at(0.75)), int(mid - bh * 0.1)), max(2, int(3 * s)))
        if "barbels" in extras:
            for dy in (0.15, 0.25):
                pygame.draw.line(sprite, colour, (int(at(1)), int(mid + bh * dy)), (int(at(1) + d * 5 * s), int(mid + bh * (dy + 0.1))), max(1, int(s)))
        if "big_mouth" in extras:
            pygame.draw.line(sprite, BLACK, (int(at(0.98)), int(mid + bh * 0.05)), (int(at(0.8)), int(mid + bh * 0.05)), max(1, int(s)))


def can_catch(spec, stats):
    """Some species only come to tackle that is strong enough. With no stats (the sea test), everything swims."""
    if stats is None:
        return True
    return all(stats[key] >= value for key, value in spec.get("requires", {}).items())


def spawn_random_fish(area, stats=None):
    species = [spec for spec in SPECIES[area] if can_catch(spec, stats)]
    spec = random.choices(species, weights=[s["rarity"] for s in species])[0]
    return Fish(spec)


def move_toward(current, target, step):
    if current < target:
        return min(target, current + step)
    if current > target:
        return max(target, current - step)
    return current
