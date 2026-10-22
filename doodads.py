# Background life: passers-by, cars, birds, boats and dolphins that come and go, so each area feels alive.
# Doodads only decorate the scene. They use their own random stream and never touch the fish.
# Each doodad is painted at its own small size, then scaled by how far away it is, so distant things look small.
import math
import random

import pygame

from config import WIDTH, BLACK, WHITE
from draw import WATER_TOP, perspective_scale

ROAD_Y = 84  # The pond's distant road runs along the far bank, above the angler
CANVAS = (140, 100)  # Each doodad is painted onto a canvas this size, centred on its position
SKIN = (236, 196, 156)
CLOTHES = [(200, 70, 70), (70, 120, 200), (230, 200, 80), (90, 170, 110), (160, 110, 190)]
CAR_COLOURS = [(190, 40, 40), (230, 230, 235), (50, 100, 190), (230, 190, 60), (60, 60, 70)]
HULL = (120, 60, 50)
SAIL = (246, 246, 240)

# How often each kind shows up, in frames (60 a second): (min, max) gap between arrivals
AREA_DOODADS = {
    "pond": [("passerby", (900, 1800)), ("car", (500, 1000)), ("birds", (500, 1000))],
    "shore": [("walker", (1000, 2000)), ("gulls", (400, 900)), ("sailboat", (1500, 2700))],
    "boat": [("gulls", (300, 700)), ("ship", (2400, 3600)), ("sailboat", (1200, 2400)), ("dolphin", (400, 900))],
}
WARM_UP_FRAMES = 900  # Simulated on arrival, so the scene is already busy when you start


class Doodad:
    """Something in the background. Subclasses paint themselves around the middle of a canvas."""

    def __init__(self, size, distance):
        # size: how big the thing is, compared with the angler. distance: 1 is as close as the angler, 0 is the horizon.
        self.scale = size * distance
        self.x = 0.0
        self.y = 0.0

    def draw(self, surface):
        canvas = pygame.Surface(CANVAS, pygame.SRCALPHA)
        self.paint(canvas, CANVAS[0] // 2, CANVAS[1] // 2)
        if self.scale != 1:
            canvas = pygame.transform.scale(canvas, (round(CANVAS[0] * self.scale), round(CANVAS[1] * self.scale)))
        surface.blit(canvas, canvas.get_rect(center=(int(self.x), int(self.y))))

    def paint(self, surface, ox, oy):
        raise NotImplementedError


class Mover(Doodad):
    """Something that travels across the scene from one side to the other, then leaves."""

    def __init__(self, right, y, speed, size, distance):
        super().__init__(size, distance)
        self.x = -30 if right else WIDTH + 30
        self.y = y
        self.speed = speed
        self.frame = 0

    def update(self):
        self.x += self.speed
        self.frame += 1

    def done(self):
        return self.x < -80 or self.x > WIDTH + 80


class Passerby(Mover):
    """A walker on the far path, sometimes with a dog on a lead. Human-sized, then shrunk by distance."""

    def __init__(self, rng, right, y, distance, dog=False):
        super().__init__(right, y, rng.uniform(0.5, 0.8) * (1 if right else -1), 3.2, distance)
        self.shirt = rng.choice(CLOTHES)
        self.dog = dog

    def paint(self, surface, ox, oy):
        feet = oy + 11  # The figure is centred on (ox, oy)
        step = math.sin(self.frame * 0.3) * 2  # Legs swing as they walk
        pygame.draw.line(surface, (58, 58, 78), (ox - 2, feet - 6), (ox - 2 + step, feet), 2)
        pygame.draw.line(surface, (58, 58, 78), (ox + 2, feet - 6), (ox + 2 - step, feet), 2)
        pygame.draw.rect(surface, self.shirt, (ox - 4, feet - 16, 8, 11))
        pygame.draw.circle(surface, SKIN, (ox, feet - 20), 3)
        pygame.draw.rect(surface, BLACK, (ox - 3, feet - 23, 6, 2))  # Hair or cap
        if self.dog:
            dx = ox + (10 if self.speed > 0 else -10)
            pygame.draw.ellipse(surface, (150, 100, 60), (dx - 4, feet - 6, 8, 5))
            pygame.draw.circle(surface, (150, 100, 60), (dx + (3 if self.speed > 0 else -3), feet - 8), 2)


class Car(Mover):
    """Cars on the distant road, with lights that catch the eye."""

    def __init__(self, rng, right):
        super().__init__(right, ROAD_Y, rng.uniform(2.2, 3.2) * (1 if right else -1), 2.0, 0.5)
        self.colour = rng.choice(CAR_COLOURS)

    def paint(self, surface, ox, oy):
        pygame.draw.rect(surface, BLACK, (ox - 14, oy - 6, 28, 10), 1)
        pygame.draw.rect(surface, self.colour, (ox - 13, oy - 5, 26, 8))
        pygame.draw.rect(surface, (120, 160, 190), (ox - 6, oy - 10, 12, 6))
        pygame.draw.circle(surface, BLACK, (ox - 8, oy + 3), 2)
        pygame.draw.circle(surface, BLACK, (ox + 8, oy + 3), 2)
        light = (255, 240, 170) if self.speed > 0 else (230, 40, 40)
        pygame.draw.rect(surface, light, (ox + 12 if self.speed > 0 else ox - 14, oy - 2, 2, 2))


class Flock(Mover):
    """A few birds in a loose V, flapping as they go. Higher birds look further away and are drawn smaller."""

    def __init__(self, rng, right, y_range, colour):
        y = rng.randint(*y_range)
        distance = 0.5 + 0.5 * (y - y_range[0]) / (y_range[1] - y_range[0])
        super().__init__(right, y, rng.uniform(0.8, 1.3) * (1 if right else -1), 1.6, distance)
        self.colour = colour
        count = rng.randint(3, 5)
        self.birds = [(i * 12 - (count - 1) * 6, rng.randint(-4, 4)) for i in range(count)]  # Centred on the flock

    def paint(self, surface, ox, oy):
        for offset_x, offset_y in self.birds:
            bx, by = ox + offset_x, oy + offset_y
            wing = math.sin(self.frame * 0.25 + offset_x) * 4  # Wings beat, each bird a little out of step
            pygame.draw.lines(surface, self.colour, False, [(bx - 5, by - wing), (bx, by), (bx + 5, by - wing)], 1)


class Sailboat(Mover):
    """A far-off sailing boat on the horizon, moving very slowly."""

    def __init__(self, rng, right):
        super().__init__(right, WATER_TOP + 10, rng.uniform(0.2, 0.35) * (1 if right else -1), 2.2, 0.35)

    def paint(self, surface, ox, oy):
        pygame.draw.polygon(surface, HULL, [(ox - 6, oy), (ox + 6, oy), (ox + 4, oy + 3), (ox - 4, oy + 3)])
        pygame.draw.polygon(surface, SAIL, [(ox, oy - 14), (ox, oy), (ox - 6, oy)])
        pygame.draw.polygon(surface, SAIL, [(ox + 1, oy - 10), (ox + 1, oy), (ox + 6, oy)])


class Ship(Mover):
    """A cargo ship crossing the horizon, slow and heavy."""

    def __init__(self, rng, right):
        super().__init__(right, WATER_TOP + 14, rng.uniform(0.25, 0.4) * (1 if right else -1), 2.0, 0.4)

    def paint(self, surface, ox, oy):
        pygame.draw.rect(surface, (60, 70, 90), (ox - 30, oy - 2, 60, 6))
        pygame.draw.rect(surface, (240, 240, 240), (ox - 22, oy - 10, 30, 8))
        pygame.draw.rect(surface, (200, 60, 50), (ox - 12, oy - 16, 8, 6))  # Bridge
        pygame.draw.rect(surface, (120, 120, 130), (ox + 14, oy - 7, 6, 5))


class Dolphin(Doodad):
    """Breaches out of the sea in an arc, then dives back under. Its position is the arc's start point."""

    def __init__(self, rng):
        self.base_y = rng.randint(330, 420)
        super().__init__(2.0, perspective_scale(self.base_y))
        self.x = rng.randint(120, WIDTH - 120)
        self.y = self.base_y
        self.direction = rng.choice((-1, 1))
        self.life = rng.randint(55, 75)
        self.frame = 0

    def update(self):
        self.frame += 1

    def done(self):
        return self.frame >= self.life

    def paint(self, surface, ox, oy):
        t = self.frame / self.life
        x = ox + self.direction * 36 * (t - 0.5)
        y = oy - math.sin(math.pi * t) * 28
        angle = math.cos(math.pi * t) * self.direction * 30  # Nose points up on the way out, down on the way in
        body = pygame.Surface((26, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(body, (90, 130, 170), body.get_rect())
        pygame.draw.ellipse(body, (200, 220, 235), (4, 5, 18, 4))  # Pale belly
        body = pygame.transform.rotate(body, angle)
        surface.blit(body, body.get_rect(center=(int(x), int(y))))
        if t < 0.1 or t > 0.9:
            pygame.draw.circle(surface, WHITE, (int(x), oy), 4, 1)  # Splash where it breaks the surface


def make_doodad(kind, rng):
    right = rng.random() < 0.5
    if kind == "passerby":
        return Passerby(rng, right, ROAD_Y + 20, 0.5, dog=rng.random() < 0.3)
    if kind == "walker":
        return Passerby(rng, right, WATER_TOP - 14, 0.6, dog=True)
    if kind == "car":
        return Car(rng, right)
    if kind == "birds":
        return Flock(rng, right, (30, 100), (40, 40, 50))
    if kind == "gulls":
        return Flock(rng, right, (30, 110), (250, 250, 250))
    if kind == "sailboat":
        return Sailboat(rng, right)
    if kind == "ship":
        return Ship(rng, right)
    return Dolphin(rng)


class Ambience:
    """Keeps one area busy. Arrivals are random, but each area always starts with the same mix."""

    def __init__(self, area):
        self.area = area
        self.schedule = AREA_DOODADS[area]
        self.rng = random.Random(f"ambience-{area}")  # Its own stream, so the fish are not affected
        self.timers = [self.rng.randint(*gap) for _, gap in self.schedule]
        self.items = []
        for _ in range(WARM_UP_FRAMES):
            self.update()

    def update(self):
        for i, (kind, gap) in enumerate(self.schedule):
            self.timers[i] -= 1
            if self.timers[i] <= 0:
                self.items.append(make_doodad(kind, self.rng))
                self.timers[i] = self.rng.randint(*gap)
        for item in self.items:
            item.update()
        self.items = [item for item in self.items if not item.done()]

    def draw(self, surface):
        if self.area == "pond":
            self.draw_road(surface)
        for item in self.items:
            item.draw(surface)

    def draw_road(self, surface):
        # A narrow road with a dashed centre line, running along the far bank
        pygame.draw.rect(surface, (70, 70, 78), (0, ROAD_Y - 4, WIDTH, 10))
        for x in range(0, WIDTH, 24):
            pygame.draw.rect(surface, (220, 200, 90), (x, ROAD_Y, 10, 2))
