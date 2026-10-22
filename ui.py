import math

import pygame

from config import WIDTH, HEIGHT, WHITE, BLACK, GOLD, HIGHLIGHT
from draw import THEMES, lerp_color, draw_text

SKY_TOP = (14, 28, 52)
SKY_BOTTOM = (34, 70, 100)
SEA = (40, 110, 150)
PANEL_FILL = (14, 22, 38)
PANEL_EDGE = (70, 100, 140)
BUTTON_FILL = (22, 36, 58)
BUTTON_FILL_SELECTED = (44, 74, 110)
KEYCAP_FILL = (96, 110, 140)
KEYCAP_SHADOW = (50, 58, 78)

_backdrop = None


def get_backdrop():
    """The sky gradient never changes, so it is drawn once and reused."""
    global _backdrop
    if _backdrop is None:
        _backdrop = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            _backdrop.fill(lerp_color(SKY_TOP, SKY_BOTTOM, y / HEIGHT), (0, y, WIDTH, 1))
    return _backdrop


def draw_fish_shape(screen, x, y, length, facing, color):
    """A simple fish silhouette, used for decoration on the menus."""
    h = length * 0.45
    body = pygame.Rect(0, 0, length, h)
    body.center = (int(x), int(y))
    if facing > 0:
        tail = [(body.left + 4, y), (body.left - length * 0.3, y - h * 0.5), (body.left - length * 0.3, y + h * 0.5)]
    else:
        tail = [(body.right - 4, y), (body.right + length * 0.3, y - h * 0.5), (body.right + length * 0.3, y + h * 0.5)]
    pygame.draw.polygon(screen, color, tail)
    pygame.draw.ellipse(screen, color, body)


def draw_backdrop(screen, t):
    """Sky with a sun glow, animated waves and fish swimming past."""
    screen.blit(get_backdrop(), (0, 0))

    # Sun glow, top right
    glow = pygame.Surface((320, 320), pygame.SRCALPHA)
    for r in range(150, 0, -10):
        pygame.draw.circle(glow, (255, 220, 140, int(35 * (1 - r / 150))), (160, 160), r)
    screen.blit(glow, (WIDTH - 240, -120))

    # Waves
    for row in range(330, HEIGHT, 22):
        shade = lerp_color(SEA, (6, 24, 50), (row - 330) / (HEIGHT - 330))
        points = [(x, row + math.sin(x * 0.03 + t * 0.05 + row) * 2) for x in range(0, WIDTH + 20, 20)]
        pygame.draw.lines(screen, shade, False, points, 2)

    # Silhouettes drifting left and right through the water
    for i, (length, speed, row) in enumerate([(60, 0.6, 360), (40, 0.9, 400), (80, 0.4, 470), (30, 1.1, 520)]):
        x = (t * speed + i * 230) % (WIDTH + 200) - 100
        facing = 1 if i % 2 == 0 else -1
        draw_fish_shape(screen, x if facing > 0 else WIDTH - x, row, length, facing, lerp_color(SEA, BLACK, 0.5))


def draw_panel(screen, rect, alpha=210):
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PANEL_FILL, alpha), panel.get_rect(), border_radius=12)
    screen.blit(panel, rect.topleft)
    pygame.draw.rect(screen, PANEL_EDGE, rect, 2, border_radius=12)


def draw_button(screen, font, label, rect, selected, t=0):
    pygame.draw.rect(screen, BUTTON_FILL_SELECTED if selected else BUTTON_FILL, rect, border_radius=10)
    pygame.draw.rect(screen, GOLD if selected else PANEL_EDGE, rect, 2, border_radius=10)
    if selected:
        # A little arrow that bobs left and right
        ax = rect.left + 14 + int(math.sin(t * 0.2) * 3)
        pygame.draw.polygon(screen, GOLD, [(ax, rect.centery - 7), (ax + 10, rect.centery), (ax, rect.centery + 7)])
    draw_text(screen, font, label, HIGHLIGHT if selected else WHITE, rect.center, center=True)


def draw_keycap(screen, font, label, topleft):
    """Draws a key label like a keyboard key and returns its width."""
    text = font.render(label, True, WHITE)
    rect = pygame.Rect(topleft[0], topleft[1], max(34, text.get_width() + 18), 26)
    pygame.draw.rect(screen, KEYCAP_SHADOW, rect.move(0, 3), border_radius=6)
    pygame.draw.rect(screen, KEYCAP_FILL, rect, border_radius=6)
    screen.blit(text, text.get_rect(center=rect.center))
    return rect.width


def draw_wavy_title(screen, font, text, centre, t, colour=GOLD):
    """Each letter bobs on its own, so the title looks alive."""
    letters = [font.render(c, True, colour) for c in text]
    x = centre[0] - sum(letter.get_width() for letter in letters) // 2
    for i, (char, letter) in enumerate(zip(text, letters)):
        y = centre[1] + math.sin(t * 0.08 + i * 0.45) * 6
        screen.blit(font.render(char, True, BLACK), (x + 3, y + 3))
        screen.blit(letter, (x, y))
        x += letter.get_width()


def draw_coin(screen, centre, radius=11):
    pygame.draw.circle(screen, BLACK, centre, radius + 1)
    pygame.draw.circle(screen, GOLD, centre, radius)
    pygame.draw.circle(screen, lerp_color(GOLD, WHITE, 0.5), (centre[0] - 3, centre[1] - 3), 3)


def draw_thumbnail(screen, rect, area, t):
    """A small picture of each fishing area, shown on the area select cards."""
    theme = THEMES[area]
    thumb = pygame.Surface((rect.w, rect.h))
    bank_h = int(rect.h * 0.3)
    for y in range(rect.h):
        if y < bank_h:
            colour = theme["bank_light"]
        else:
            colour = lerp_color(theme["shallow"], theme["deep"], (y - bank_h) / (rect.h - bank_h))
        thumb.fill(colour, (0, y, rect.w, 1))
    if area == "pond":
        pygame.draw.ellipse(thumb, (48, 112, 70), (rect.w * 0.2, rect.h * 0.62, 22, 9))
        bobber_x = int(rect.w * 0.7)
        pygame.draw.line(thumb, WHITE, (bobber_x, bank_h), (bobber_x, rect.h * 0.55), 1)
        pygame.draw.circle(thumb, (220, 60, 60), (bobber_x, int(rect.h * 0.55)), 3)
    elif area == "shore":
        for x in range(0, rect.w, 9):
            thumb.set_at((x, int(bank_h / 2) + (x * 7) % 5), theme["edge"])
        pygame.draw.circle(thumb, (150, 150, 160), (int(rect.w * 0.65), int(rect.h * 0.7)), 4)
    else:
        for x in range(0, rect.w, 22):
            pygame.draw.line(thumb, theme["edge"], (x, 0), (x, bank_h), 2)
        jig_y = int(rect.h * 0.6 + math.sin(t * 0.1) * 3)
        pygame.draw.polygon(thumb, (200, 205, 215), [(rect.w * 0.7, jig_y), (rect.w * 0.7 + 4, jig_y + 7), (rect.w * 0.7, jig_y + 14), (rect.w * 0.7 - 4, jig_y + 7)])
    screen.blit(thumb, rect.topleft)
    pygame.draw.rect(screen, PANEL_EDGE, rect, 2)
