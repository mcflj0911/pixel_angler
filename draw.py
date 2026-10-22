import math
import random

import pygame

from config import WIDTH, HEIGHT, BLACK, WHITE

WATER_TOP = 120  # The bank is the strip across the top, the water starts below it
PIXEL = 2  # The world is drawn at half resolution and scaled up, for chunky pixels

# Fixed camera: a 3/4 top-down view of the water from the bank, through a wide-angle lens.
# Ground points are (X, z). X runs across the screen from the middle, in pixels at the bank.
# z is the depth: 0 at the shoreline, 1 at the bottom of the screen, and negative on the bank behind it.
# Lines that run away from the bank converge on a point just below the bottom of the screen.
CAMERA_TILT = 0.8  # Lower is a wider lens, and the lines converge harder
BANK_DEPTH = 0.2  # How far the bank runs back from the shoreline, in ground units
BANK_SPAN = WATER_TOP / BANK_DEPTH  # Screen pixels per unit of depth on the bank
WATER_SPAN = HEIGHT - WATER_TOP  # Screen pixels from the shoreline to the bottom
GROUND_HALF = 1200  # How far across the ground to draw, so it still fills the screen at the bottom

# Each area has its own look. "wave" scales how choppy the water is.
THEMES = {
    "pond": {
        "bank_light": (128, 178, 96), "bank_dark": (92, 140, 66), "edge": (62, 104, 50),
        "foam": (200, 236, 196), "shallow": (78, 150, 120), "deep": (22, 78, 84), "wave": 1,
    },
    "shore": {
        "bank_light": (232, 210, 160), "bank_dark": (206, 178, 124), "edge": (168, 138, 94),
        "foam": (235, 248, 250), "shallow": (92, 196, 206), "deep": (14, 64, 102), "wave": 1,
    },
    "boat": {
        "bank_light": (168, 112, 64), "bank_dark": (128, 82, 44), "edge": (84, 54, 30),
        "foam": (222, 242, 250), "shallow": (40, 120, 172), "deep": (6, 30, 70), "wave": 2,
    },
}


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def lerp_point(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def lateral_scale(z):
    """How much things are stretched across the screen at depth z. Nearer is wider, and the far water pulls in."""
    return CAMERA_TILT / (z + CAMERA_TILT)


def ground_point(X, z):
    """Screen position (x, y) of a ground point. The lens pulls things in towards the middle as they recede."""
    if z < 0:
        y = WATER_TOP + z * BANK_SPAN
    else:
        y = WATER_TOP + WATER_SPAN * z * (1 + CAMERA_TILT) / (z + CAMERA_TILT)
    return (WIDTH / 2 + X * lateral_scale(z), y)


def ground_disc(X, z, rx, rz, steps=16):
    """A flat circle lying on the ground, as a polygon on the screen. It looks flatter the further away it is."""
    return [ground_point(X + rx * math.cos(a), z + rz * math.sin(a)) for a in (2 * math.pi * i / steps for i in range(steps))]


# We look out from the bank: higher on screen is closer, lower is further out and deeper.
def depth_t(y):
    """0 at the shoreline, 1 at the bottom of the screen. This inverts ground_point, so colours follow the lens."""
    s = min(1.0, max(0.0, (y - WATER_TOP) / WATER_SPAN))
    return s * CAMERA_TILT / (1 + CAMERA_TILT - s)


def water_color(theme, y):
    return lerp_color(theme["shallow"], theme["deep"], depth_t(y))


def perspective_scale(y):
    # Things further out look smaller
    return 1.15 - 0.35 * depth_t(y)


def make_background(area):
    theme = THEMES[area]
    bg = pygame.Surface((WIDTH, HEIGHT))
    shadow = lerp_color(theme["edge"], BLACK, 0.3)
    rng = random.Random(3)  # Own RNG so the game's random stream is untouched

    # Bank: a gradient that darkens towards the water
    for y in range(WATER_TOP):
        pygame.draw.line(bg, lerp_color(theme["bank_light"], theme["bank_dark"], y / WATER_TOP), (0, y), (WIDTH, y))

    # Water gets deeper and darker towards the bottom
    for y in range(WATER_TOP, HEIGHT):
        pygame.draw.line(bg, water_color(theme, y), (0, y), (WIDTH, y))

    # Faint lines running away from the bank, which converge on the bottom of the screen
    streak = lerp_color(theme["shallow"], WHITE, 0.1)
    for X in range(-GROUND_HALF, GROUND_HALF, 180):
        pygame.draw.line(bg, streak, ground_point(X, 0), ground_point(X, 1), 1)

    if area == "pond":
        # Lily pads with a notch cut out of each, lying flat on the water
        for _ in range(14):
            X, z = rng.uniform(-900, 900), rng.uniform(0.2, 0.95)
            pygame.draw.polygon(bg, (48, 112, 70), ground_disc(X, z, 12, 0.02))
            x, y = ground_point(X, z)
            pygame.draw.polygon(bg, water_color(theme, y), [(x, y), ground_point(X + 12, z - 0.01), ground_point(X + 12, z + 0.01)])

    # Everything on the bank is laid out on the ground too, so it converges with the water
    if area == "shore":
        # Sand speckles and pebbles with a lit top edge and a shadowed bottom
        for _ in range(400):
            x, y = ground_point(rng.uniform(-WIDTH / 2, WIDTH / 2), rng.uniform(-BANK_DEPTH, 0))
            pygame.draw.circle(bg, theme["bank_dark"], (int(x), int(y)), rng.choice((1, 2)))
        for _ in range(26):
            X, z = rng.uniform(-WIDTH / 2, WIDTH / 2), rng.uniform(-BANK_DEPTH, -0.02)
            x, y = ground_point(X, z)
            r = max(1, int(rng.randint(3, 5) * lateral_scale(z)))
            pygame.draw.circle(bg, shadow, (int(x), int(y) + 1), r)
            pygame.draw.circle(bg, theme["edge"], (int(x), int(y)), r)
            pygame.draw.circle(bg, lerp_color(theme["edge"], WHITE, 0.4), (int(x) - 1, int(y) - 1), 1)
    elif area == "pond":
        # Grass tufts along the bank, in two shades
        for X in range(-WIDTH // 2, WIDTH // 2, 10):
            x, y = ground_point(X, -0.01)
            height = rng.randint(6, 18)
            shade = theme["edge"] if rng.random() < 0.5 else theme["bank_dark"]
            pygame.draw.line(bg, shade, (x, y), (x + rng.randint(-3, 3), y - height), 2)
    else:
        # Wooden deck planks, each with a slightly different tone and a dark seam running back from the water
        for X in range(-WIDTH // 2, WIDTH // 2, 60):
            tone = lerp_color(theme["bank_light"], theme["bank_dark"], rng.random() * 0.5)
            pygame.draw.polygon(bg, tone, [ground_point(X, -BANK_DEPTH), ground_point(X + 60, -BANK_DEPTH), ground_point(X + 60, 0), ground_point(X, 0)])
            pygame.draw.line(bg, shadow, ground_point(X, -BANK_DEPTH), ground_point(X, 0), 2)

    pygame.draw.rect(bg, theme["edge"], (0, WATER_TOP - 8, WIDTH, 8))  # Wet edge of the bank
    pygame.draw.line(bg, lerp_color(theme["edge"], WHITE, 0.3), (0, WATER_TOP - 9), (WIDTH, WATER_TOP - 9))
    return bg


def make_panel(width, height):
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (0, 0, 0, 110), panel.get_rect(), border_radius=8)
    return panel


def draw_text(surface, font, text, color, pos, center=False):
    label = font.render(text, True, color)
    shadow = font.render(text, True, BLACK)
    rect = label.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(shadow, rect.move(2, 2))
    surface.blit(label, rect)


def pixelate(world, screen):
    """Draw the world layer at 1/PIXEL resolution and scale it back up with hard pixels."""
    small = pygame.transform.scale(world, (WIDTH // PIXEL, HEIGHT // PIXEL))
    screen.blit(pygame.transform.scale(small, (WIDTH, HEIGHT)), (0, 0))
