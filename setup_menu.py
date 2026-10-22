import pygame

from config import UI_WIDTH, WHITE, BLACK, GREY, GOLD, HIGHLIGHT, GREEN
from draw import draw_text
from equipment import PARTS, SLOTS, SLOT_NAMES, STAT_ROWS
from scene import Scene
from ui import draw_backdrop, draw_panel, draw_wavy_title

ROD_COLOUR = (96, 62, 36)
LINE_COLOUR = (238, 238, 238)
BAR_BACK = (50, 52, 66)


class SetupScene(Scene):
    """Fishing-planet style tackle setup: pick a slot, then fit one of your parts to it."""

    def __init__(self, app):
        super().__init__(app)
        self.slot = 0
        self.part = 0
        self.focus = 0  # 0 is the slot list, 1 is the parts list
        self.message = ""
        self.ticks = 0
        self.slot_rects = [pygame.Rect(40, 84 + i * 58, 230, 50) for i in range(len(SLOTS))]
        self.part_rects = [pygame.Rect(310, 84 + i * 56, 450, 52) for i in range(4)]  # The hook slot has four parts

    def parts(self):
        return [part for part in PARTS if part["slot"] == SLOTS[self.slot]]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.close()
            elif event.key == pygame.K_UP:
                self.move(-1)
            elif event.key == pygame.K_DOWN:
                self.move(1)
            elif event.key == pygame.K_RIGHT:
                self.focus = 1
            elif event.key == pygame.K_LEFT:
                self.focus = 0
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.focus == 0:
                    self.focus = 1
                else:
                    self.fit_selected()
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.slot_rects):
                if rect.collidepoint(event.pos):
                    self.slot, self.part, self.focus = i, 0, 0
            for i, rect in enumerate(self.part_rects[:len(self.parts())]):
                if rect.collidepoint(event.pos):
                    self.part, self.focus = i, 1
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.slot_rects):
                if rect.collidepoint(event.pos):
                    self.slot, self.part, self.focus = i, 0, 0
                    return
            for i, rect in enumerate(self.part_rects[:len(self.parts())]):
                if rect.collidepoint(event.pos):
                    self.part, self.focus = i, 1
                    self.fit_selected()

    def move(self, step):
        if self.focus == 0:
            self.slot = (self.slot + step) % len(SLOTS)
            self.part = 0
        else:
            self.part = (self.part + step) % len(self.parts())

    def fit_selected(self):
        part = self.parts()[self.part]
        economy = self.app.economy
        if part["key"] in economy.owned:
            economy.equip(part)
            self.message = f"Fitted {part['name']}"
            self.app.sound.play("click")
        else:
            self.message = f"Buy {part['name']} in the Shop for ${part['price']}"
            self.app.sound.play("error")

    def update(self):
        self.ticks += 1

    def draw(self, screen):
        economy = self.app.economy
        draw_backdrop(screen, self.ticks)
        draw_wavy_title(screen, self.app.font, "Setup", (UI_WIDTH // 2, 36), self.ticks)

        # Slots, each showing the part fitted to it
        for i, rect in enumerate(self.slot_rects):
            selected = i == self.slot
            draw_panel(screen, rect, alpha=235 if selected else 170)
            if selected:
                pygame.draw.rect(screen, GOLD, rect, 2, border_radius=12)
            slot = SLOTS[i]
            draw_text(screen, self.app.small_font, SLOT_NAMES[slot].upper(), HIGHLIGHT if selected else GREY, (rect.left + 12, rect.top + 6))
            draw_text(screen, self.app.small_font, economy.equipped(slot)["name"], WHITE, (rect.left + 12, rect.top + 26))

        self.draw_preview(screen, pygame.Rect(30, 386, 250, 150))

        # Parts you can fit to the selected slot
        parts_panel = pygame.Rect(300, 74, 470, 232)
        draw_panel(screen, parts_panel)
        for i, part in enumerate(self.parts()):
            self.draw_part(screen, self.part_rects[i], part, self.focus == 1 and i == self.part)

        # Combined stats of everything fitted
        stats_panel = pygame.Rect(300, 318, 470, 218)
        draw_panel(screen, stats_panel)
        draw_text(screen, self.app.small_font, "COMBINED STATS", GOLD, (stats_panel.left + 14, stats_panel.top + 10))
        stats = economy.stats()
        for row, (key, label, fmt, full) in enumerate(STAT_ROWS):
            y = stats_panel.top + 38 + row * 19
            draw_text(screen, self.app.small_font, label, WHITE, (stats_panel.left + 14, y))
            bar = pygame.Rect(stats_panel.left + 170, y + 4, 200, 10)
            pygame.draw.rect(screen, BAR_BACK, bar, border_radius=4)
            fill = min(1.0, stats[key] / full)
            pygame.draw.rect(screen, GOLD, (bar.left, bar.top, int(bar.width * fill), bar.height), border_radius=4)
            draw_text(screen, self.app.small_font, fmt.format(stats[key]), WHITE, (bar.right + 10, y))

        footer = pygame.Rect(30, 548, 740, 36)
        draw_panel(screen, footer)
        text = self.message or "Up/Down choose  -  Right/Enter for parts  -  Enter fits  -  Esc back"
        draw_text(screen, self.app.small_font, text, GOLD if self.message else GREY, footer.center, center=True)

    def draw_part(self, screen, rect, part, selected):
        economy = self.app.economy
        equipped = economy.setup[part["slot"]] == part["key"]
        owned = part["key"] in economy.owned
        pygame.draw.rect(screen, (40, 64, 96) if selected else (24, 36, 58), rect, border_radius=8)
        if selected:
            pygame.draw.rect(screen, GOLD, rect, 2, border_radius=8)
        draw_text(screen, self.app.font, part["name"], HIGHLIGHT if selected else WHITE, (rect.left + 14, rect.top + 2))
        draw_text(screen, self.app.small_font, part["desc"], GREY, (rect.left + 14, rect.top + 30))

        if equipped:
            tag, colour = "FITTED", GREEN
        elif owned:
            tag, colour = "OWNED", (120, 220, 130)
        elif part["price"] == 0:
            tag, colour = "SPONSOR", GREY  # Signature parts are only earned by signing with a sponsor
        else:
            tag, colour = f"${part['price']}", GOLD
        pill = pygame.Rect(0, 0, 96, 26)
        pill.midright = (rect.right - 12, rect.centery)
        pygame.draw.rect(screen, (40, 36, 20), pill, border_radius=13)
        pygame.draw.rect(screen, colour, pill, 2, border_radius=13)
        draw_text(screen, self.app.small_font, tag, colour, pill.center, center=True)

    def draw_preview(self, screen, rect):
        """A quick picture of the rod: longer rods reach further, bigger reels turn faster."""
        draw_panel(screen, rect)
        stats = self.app.economy.stats()
        base = (rect.left + 40, rect.bottom - 40)
        length = 80 + stats["reach"] * 1.6
        tip = (int(base[0] + length * 0.85), int(base[1] - length * 0.5))
        pygame.draw.line(screen, BLACK, base, tip, 6)
        pygame.draw.line(screen, ROD_COLOUR, base, tip, 4)
        reel = (base[0] + 14, base[1] - 10)
        pygame.draw.circle(screen, BLACK, reel, int(6 + 2 * stats["speed"]) + 1)
        pygame.draw.circle(screen, GREY, reel, int(6 + 2 * stats["speed"]))
        pygame.draw.line(screen, LINE_COLOUR, tip, (tip[0] + 8, rect.bottom - 12), 1)
        draw_text(screen, self.app.small_font, f"Rating {stats['rating']}   Strength {stats['strength']}", WHITE, (rect.left + 12, rect.top + 10))
