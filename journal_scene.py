import pygame

from config import UI_WIDTH, WHITE, GREY, GOLD
from draw import draw_text
from fish import SPECIES
from journal import AREAS, AREA_NAMES, LORE, MILESTONES, kinds_caught
from scene import Scene
from ui import draw_backdrop, draw_fish_shape, draw_panel, draw_wavy_title

# Species in a 3 by 3 grid: one column per area, one row per species
ORDER = [(area, spec) for area in AREAS for spec in SPECIES[area]]
CARD_W, CARD_H = 230, 92
UNCAUGHT = (40, 50, 64)


def wrap(text, font, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if font.size(trial)[0] <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


class JournalScene(Scene):
    """The angler's field journal: every species, with silhouettes, records, lore and milestones."""

    def __init__(self, app):
        super().__init__(app)
        self.selected = 0
        self.ticks = 0
        self.rects = [pygame.Rect(40 + (i // 3) * 250, 96 + (i % 3) * 100, CARD_W, CARD_H) for i in range(len(ORDER))]

    def move(self, dx, dy):
        col, row = divmod(self.selected, 3)
        col = min(2, max(0, col + dx))
        row = min(2, max(0, row + dy))
        self.selected = col * 3 + row

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.close()
            elif event.key == pygame.K_LEFT:
                self.move(-1, 0)
            elif event.key == pygame.K_RIGHT:
                self.move(1, 0)
            elif event.key == pygame.K_UP:
                self.move(0, -1)
            elif event.key == pygame.K_DOWN:
                self.move(0, 1)
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.rects):
                if rect.collidepoint(event.pos):
                    self.selected = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.app.close()

    def update(self):
        self.ticks += 1

    def draw(self, screen):
        economy = self.app.economy
        draw_backdrop(screen, self.ticks)
        draw_wavy_title(screen, self.app.font, "Field Journal", (UI_WIDTH // 2, 30), self.ticks)

        for col, area in enumerate(AREAS):
            draw_text(screen, self.app.small_font, AREA_NAMES[area].upper(), GOLD, (40 + col * 250, 72))

        for i, (area, spec) in enumerate(ORDER):
            self.draw_card(screen, self.rects[i], spec, spec["name"] in economy.catch_log, i == self.selected)

        self.draw_info(screen, ORDER[self.selected][1])
        self.draw_milestones(screen)
        draw_text(screen, self.app.small_font, "Arrows choose  -  Esc back", GREY, (UI_WIDTH // 2, 580), center=True)

    def draw_card(self, screen, rect, spec, caught, selected):
        draw_panel(screen, rect, alpha=235 if selected else 170)
        if selected:
            pygame.draw.rect(screen, GOLD, rect, 2, border_radius=12)
        colour = spec["color"] if caught else UNCAUGHT
        draw_fish_shape(screen, rect.left + 56, rect.centery, min(80, spec["size"][0] * 1.5), 1, colour)
        name = spec["name"] if caught else "???"
        draw_text(screen, self.app.small_font, name, WHITE if caught else GREY, (rect.left + 110, rect.top + 18))
        count = self.app.economy.catch_log.get(spec["name"], {}).get("count", 0)
        draw_text(screen, self.app.small_font, f"Caught {count}" if caught else "Not yet caught", GREY, (rect.left + 110, rect.top + 46))

    def draw_info(self, screen, spec):
        panel = pygame.Rect(40, 400, 380, 160)
        draw_panel(screen, panel)
        caught = self.app.economy.catch_log.get(spec["name"])
        draw_text(screen, self.app.font, spec["name"] if caught else "???", GOLD, (panel.left + 14, panel.top + 8))
        if not caught:
            draw_text(screen, self.app.small_font, "Catch one to reveal it.", GREY, (panel.left + 14, panel.top + 56))
            return
        for i, line in enumerate(wrap(LORE[spec["name"]], self.app.small_font, panel.width - 28)):
            draw_text(screen, self.app.small_font, line, WHITE, (panel.left + 14, panel.top + 48 + i * 22))
        records = f"Heaviest {caught['best_lbs']:.2f} lb    Longest {caught['best_len']:.0f} cm"
        draw_text(screen, self.app.small_font, records, GOLD, (panel.left + 14, panel.bottom - 28))

    def draw_milestones(self, screen):
        panel = pygame.Rect(430, 400, 330, 160)
        draw_panel(screen, panel)
        draw_text(screen, self.app.font, "Milestones", GOLD, (panel.left + 14, panel.top + 8))
        economy = self.app.economy
        for i, (key, need, title, reward) in enumerate(MILESTONES):
            y = panel.top + 50 + i * 26
            have = min(need, kinds_caught(economy.catch_log, key))
            text = f"{title.split(':')[0]}  {have}/{need}"
            colour = (120, 220, 130) if key in economy.claimed else WHITE
            draw_text(screen, self.app.small_font, text, colour, (panel.left + 14, y))
            done = "DONE" if key in economy.claimed else f"+${reward}"
            done_x = panel.right - 14 - self.app.small_font.size(done)[0]
            draw_text(screen, self.app.small_font, done, colour, (done_x, y))
