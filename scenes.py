import math

import pygame

from config import UI_WIDTH, WHITE, GREY, GOLD, HIGHLIGHT, BLACK
from draw import draw_text
from economy import BAIT_SHOP, COOLER_SHOP
from equipment import PART_BY_KEY, SHOP_PARTS, SLOT_NAMES
from sponsors import SPONSORS
from setup_menu import SetupScene
from journal_scene import JournalScene
from fish import SPECIES
from fishing import AREA_INFO, FishingScene
from scene import Scene
from ui import (draw_backdrop, draw_button, draw_coin, draw_keycap, draw_panel,
                draw_thumbnail, draw_wavy_title, draw_fish_shape)

FISH_COLOURS = {spec["name"]: spec["color"] for area in SPECIES for spec in SPECIES[area]}
LURE_COLOURS = {"pond": (120, 200, 90), "shore": (244, 170, 200), "boat": (200, 205, 215)}

CONTROLS = [
    ("Menus", [("Up / Down", "move through the menu"), ("Enter or click", "choose"), ("Esc", "go back"), ("M", "mute sound")]),
    ("Casting", [("Click", "set the target, hold, release on the white tick"), ("B / S / J", "shop, tackle setup or journal while idle")]),
    ("Fishing", [("Up", "reel in, or tap to twitch the lure or jerk the jig"),
                 ("Down", "sink the pond bait, or reel in fast at sea"), ("Left / Right", "walk along the bank, or wiggle a snag free")]),
    ("Strikes and fights", [("WAIT... GO!", "press Space on the GO ring's green target"),
                            ("Left / Right / Up", "safe zone, and reel (watch the LINE bar)")]),
]

MODE_CARDS = [
    ("pond", "Pond", ["Bait and wait. Lower the worm to a layer with Up/Down.", "Tip: watch the float for nibbles, strike on the big dip."]),
    ("shore", "Shore", ["Shorecasting. Reel a paddletail through the surf.", "Tip: tap Up to twitch the lure. Fish strike mid-retrieve."]),
    ("boat", "Open Sea", ["Micro jigging. Let the jig fall, then jerk it.", "Tip: jerk in rhythm to draw fish up. Deep fish are big fish."]),
]


def clicked_index(event, rects):
    """Which button rectangle was clicked, if any."""
    for i, rect in enumerate(rects):
        if rect.collidepoint(event.pos):
            return i
    return None


def hovered_index(event, rects):
    for i, rect in enumerate(rects):
        if rect.collidepoint(event.pos):
            return i
    return None


def draw_leaping_fish(screen, t):
    """A fish leaps out of the sea, then splashes back in. Repeats every 4 seconds."""
    cycle = int(t) % 240
    if cycle < 120:
        q = cycle / 120
        x = 150 + 450 * q
        y = 330 - 130 * math.sin(math.pi * q)
        draw_fish_shape(screen, x, y, 46, 1, (120, 170, 200))
    for start in (0, 120):
        age = cycle - start
        if 0 <= age < 14:
            pygame.draw.circle(screen, (220, 240, 250), (150 if start == 0 else 600, 330), 4 + age * 2, 2)


class TitleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.ticks = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            self.app.switch(MenuScene(self.app))

    def update(self):
        self.ticks += 1

    def draw(self, screen):
        draw_backdrop(screen, self.ticks)
        draw_wavy_title(screen, self.app.large_font, "PIXEL FISHING", (UI_WIDTH // 2, 170), self.ticks)
        draw_text(screen, self.app.font, "Pond  -  Shore  -  Open Sea", WHITE, (UI_WIDTH // 2, 258), center=True)
        draw_leaping_fish(screen, self.ticks)
        if (self.ticks // 30) % 2 == 0:
            draw_text(screen, self.app.font, "Press any key", GOLD, (UI_WIDTH // 2, 470), center=True)


class MenuScene(Scene):
    ITEMS = [("Go Fishing", "fish"), ("Shop", "shop"), ("Setup", "setup"), ("Journal", "journal"), ("Controls", "controls"), ("Quit", "quit")]

    def __init__(self, app):
        super().__init__(app)
        self.selected = 0
        self.ticks = 0
        self.rects = [pygame.Rect(250, 176 + i * 52, 300, 46) for i in range(len(self.ITEMS))]

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            hover = hovered_index(event, self.rects)
            if hover is not None:
                self.selected = hover
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = clicked_index(event, self.rects)
            if index is not None:
                self.selected = index
                self.activate(self.ITEMS[index][1])
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.ITEMS)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.ITEMS)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.activate(self.ITEMS[self.selected][1])

    def activate(self, action):
        self.app.sound.play("click")
        if action == "fish":
            self.app.open(ModeScene(self.app))
        elif action == "shop":
            self.app.open(ShopScene(self.app))
        elif action == "setup":
            self.app.open(SetupScene(self.app))
        elif action == "journal":
            self.app.open(JournalScene(self.app))
        elif action == "controls":
            self.app.open(ControlsScene(self.app))
        elif action == "quit":
            self.app.running = False

    def update(self):
        self.ticks += 1

    def draw(self, screen):
        draw_backdrop(screen, self.ticks)
        draw_wavy_title(screen, self.app.large_font, "PIXEL FISHING", (UI_WIDTH // 2, 110), self.ticks)
        for i, (label, _) in enumerate(self.ITEMS):
            draw_button(screen, self.app.font, label, self.rects[i], i == self.selected, self.ticks)

        economy = self.app.economy
        panel = pygame.Rect(230, 490, 340, 70)
        draw_panel(screen, panel)
        draw_coin(screen, (panel.left + 30, panel.top + 26))
        draw_text(screen, self.app.font, f"${economy.money}", WHITE, (panel.left + 56, panel.top + 10))
        stats = f"Caught {economy.total_caught}   Sold ${economy.total_sold}"
        draw_text(screen, self.app.small_font, stats, GREY, (panel.left + 56, panel.top + 46))


class ControlsScene(Scene):
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            self.app.close()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.app.close()

    def draw(self, screen):
        draw_backdrop(screen, 0)
        panel = pygame.Rect(40, 36, 720, 520)
        draw_panel(screen, panel, alpha=230)
        draw_text(screen, self.app.font, "Controls", GOLD, (UI_WIDTH // 2, 62), center=True)

        y = 96
        for section, rows in CONTROLS:
            draw_text(screen, self.app.small_font, section.upper(), HIGHLIGHT, (70, y))
            y += 28
            for keys, action in rows:
                width = 0
                x = 80
                for part in keys.split(" / "):
                    width = draw_keycap(screen, self.app.small_font, part, (x, y))
                    x += width + 6
                draw_text(screen, self.app.small_font, action, WHITE, (300, y + 3))
                y += 28
            y += 12
        draw_text(screen, self.app.small_font, "Esc, Enter or click to go back", GREY, (UI_WIDTH // 2, 580), center=True)


class ModeScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.selected = 0
        self.ticks = 0
        self.rects = [pygame.Rect(80, 96 + i * 130, 640, 118) for i in range(len(MODE_CARDS))]

    def open_selected(self):
        self.app.sound.play("click")
        self.app.open(FishingScene(self.app, MODE_CARDS[self.selected][0]))

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            hover = hovered_index(event, self.rects)
            if hover is not None:
                self.selected = hover
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = clicked_index(event, self.rects)
            if index is not None:
                self.selected = index
                self.open_selected()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(MODE_CARDS)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(MODE_CARDS)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.open_selected()
            elif event.key == pygame.K_ESCAPE:
                self.app.close()

    def update(self):
        self.ticks += 1

    def draw(self, screen):
        draw_backdrop(screen, self.ticks)
        draw_wavy_title(screen, self.app.font, "Choose where to fish", (UI_WIDTH // 2, 50), self.ticks)
        for i, (area, title, lines) in enumerate(MODE_CARDS):
            rect = self.rects[i]
            selected = i == self.selected
            draw_panel(screen, rect, alpha=235 if selected else 170)
            if selected:
                pygame.draw.rect(screen, GOLD, rect, 2, border_radius=12)
            thumb = pygame.Rect(rect.left + 16, rect.top + 16, 150, 86)
            draw_thumbnail(screen, thumb, area, self.ticks)

            x = rect.left + 186
            draw_text(screen, self.app.font, title, HIGHLIGHT if selected else WHITE, (x, rect.top + 10))
            for j, line in enumerate(lines):
                draw_text(screen, self.app.small_font, line, WHITE, (x, rect.top + 46 + j * 24))
            bait = self.app.economy.bait[area]
            status = f"Needs: {AREA_INFO[area]['lure']}  (you have {bait})"
            draw_text(screen, self.app.small_font, status, GREY if bait else (230, 120, 120), (x, rect.top + 94))
        draw_text(screen, self.app.small_font, "Enter or click to fish here     Esc: back", GREY, (UI_WIDTH // 2, 575), center=True)


class ShopScene(Scene):
    TABS = ["Bait", "Parts", "Upgrades", "Repair", "Bounties", "Sponsors", "Sell"]
    VISIBLE_ROWS = 5

    def __init__(self, app):
        super().__init__(app)
        self.tab = 0
        self.selected = 0
        self.message = ""
        self.ticks = 0
        self.tab_rects = [pygame.Rect(40 + i * 103, 84, 98, 36) for i in range(len(self.TABS))]
        self.row_rects = []

    def items(self):
        if self.TABS[self.tab] == "Bait":
            return BAIT_SHOP
        if self.TABS[self.tab] == "Parts":
            return SHOP_PARTS
        if self.TABS[self.tab] == "Upgrades":
            return COOLER_SHOP
        if self.TABS[self.tab] == "Repair":
            return self.app.economy.repair_items()
        if self.TABS[self.tab] == "Bounties":
            return self.app.economy.contracts
        if self.TABS[self.tab] == "Sponsors":
            return SPONSORS
        return self.app.economy.creel

    def set_tab(self, tab):
        self.tab = tab
        self.selected = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            hover = hovered_index(event, self.row_rects)
            if hover is not None:
                self.selected = self.scroll_offset() + hover
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            tab = clicked_index(event, self.tab_rects)
            if tab is not None:
                self.set_tab(tab)
                return
            row = clicked_index(event, self.row_rects)
            if row is not None and self.items():
                self.selected = self.scroll_offset() + row
                self.act()
        elif event.type == pygame.KEYDOWN:
            self.handle_key(event.key)

    def handle_key(self, key):
        if key == pygame.K_ESCAPE:
            self.app.close()
        elif key == pygame.K_LEFT:
            self.set_tab((self.tab - 1) % len(self.TABS))
        elif key == pygame.K_RIGHT:
            self.set_tab((self.tab + 1) % len(self.TABS))
        elif key == pygame.K_UP and self.items():
            self.selected = (self.selected - 1) % len(self.items())
        elif key == pygame.K_DOWN and self.items():
            self.selected = (self.selected + 1) % len(self.items())
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.items():
            self.act()

    def scroll_offset(self):
        return max(0, min(self.selected - self.VISIBLE_ROWS + 1, len(self.items()) - self.VISIBLE_ROWS))

    def act(self):
        economy = self.app.economy
        tab = self.TABS[self.tab]
        sound = self.app.sound
        if tab == "Bait":
            item = BAIT_SHOP[self.selected]
            bought = economy.buy_bait(item)
            self.message = f"Bought {item['name']}" if bought else "Not enough money"
            sound.play("buy" if bought else "error")
        elif tab == "Parts":
            part = SHOP_PARTS[self.selected]
            if part["key"] in economy.owned:
                self.message = "You already own that"
                sound.play("error")
            else:
                bought = economy.buy_part(part)
                self.message = f"Bought and fitted {part['name']}" if bought else "Not enough money"
                sound.play("buy" if bought else "error")
        elif tab == "Bounties":
            self.message = "Catch the fish, and they count towards the contract"
        elif tab == "Repair":
            item = self.items()[self.selected]
            repaired = economy.repair(item["key"])
            self.message = f"Repaired {item['name']} for ${item['price']}" if repaired else "Not enough money"
            sound.play("buy" if repaired else "error")
            self.selected = min(self.selected, max(0, len(self.items()) - 1))
        elif tab == "Sponsors":
            sponsor = SPONSORS[self.selected]
            if sponsor["key"] in economy.sponsors:
                self.message = "You already sponsor with them"
                sound.play("error")
            elif economy.sign_sponsor(sponsor):
                self.message = f"Signed with {sponsor['name']}. Fitted their gear"
                sound.play("buy")
            else:
                self.message = f"They want {sponsor['reputation']} reputation first"
                sound.play("error")
        elif tab == "Upgrades":
            item = COOLER_SHOP[self.selected]
            if economy.creel_limit >= item["capacity"]:
                self.message = "You already have that"
                sound.play("error")
            else:
                bought = economy.buy_cooler(item)
                self.message = f"Bought the {item['name']}, holds {item['capacity']}" if bought else "Not enough money"
                sound.play("buy" if bought else "error")
        else:
            fish = economy.sell(self.selected)
            self.message = f"Sold {fish['name']} for ${fish['price']}"
            self.selected = min(self.selected, max(0, len(economy.creel) - 1))
            sound.play("coin")

    def update(self):
        self.ticks += 1

    def draw_row(self, screen, rect, item, selected, tab):
        if tab == "Bait":
            # Bait is coloured like the lure, and attractants are gold
            attractant = item.get("kind") == "attractant"
            colour = (230, 190, 70) if attractant else LURE_COLOURS[item["area"]]
            pygame.draw.circle(screen, colour, (rect.left + 28, rect.centery), 12)
            pygame.draw.circle(screen, BLACK, (rect.left + 28, rect.centery), 12, 2)
            detail = f"Draws fish to the lure for {item['amount']} casts" if attractant else f"Gives {item['amount']} casts"
        elif tab == "Parts":
            owned = item["key"] in self.app.economy.owned
            pygame.draw.rect(screen, GOLD if owned else (110, 110, 120), (rect.left + 16, rect.centery - 12, 24, 24), border_radius=5)
            detail = f"{SLOT_NAMES[item['slot']]}: {item['desc']}"
        elif tab == "Bounties":
            pygame.draw.rect(screen, GOLD if item["progress"] >= item["count"] else (110, 110, 120), (rect.left + 16, rect.centery - 12, 24, 24), border_radius=5)
            detail = f"{item['progress']} of {item['count']} caught"
        elif tab == "Repair":
            pygame.draw.rect(screen, (220, 120, 60) if item["wear"] > 50 else GOLD, (rect.left + 16, rect.centery - 12, 24, 24), border_radius=5)
            detail = f"Condition {100 - item['wear']:.0f}%. Worn gear performs worse"
        elif tab == "Sponsors":
            signed = item["key"] in self.app.economy.sponsors
            pygame.draw.rect(screen, GOLD if signed else (110, 110, 120), (rect.left + 16, rect.centery - 12, 24, 24), border_radius=5)
            detail = f"Signature {PART_BY_KEY[item['part']]['name']}. Pays ${item['pay']} a day while fitted"
        elif tab == "Upgrades":
            pygame.draw.rect(screen, GOLD, (rect.left + 16, rect.centery - 12, 24, 24), border_radius=5)
            detail = f"Holds {item['capacity']} fish in the cooler"
        else:
            colour = FISH_COLOURS.get(item["name"], WHITE)
            pygame.draw.ellipse(screen, colour, (rect.left + 14, rect.centery - 9, 30, 18))
            detail = "Ready to sell"

        draw_text(screen, self.app.font, item["name"], HIGHLIGHT if selected else WHITE, (rect.left + 60, rect.top + 6))
        draw_text(screen, self.app.small_font, detail, GREY, (rect.left + 60, rect.top + 36))

        if tab == "Sell":
            price, colour = f"${item['price']}", GOLD
        elif tab == "Sponsors":
            if item["key"] in self.app.economy.sponsors:
                price, colour = "SIGNED", (120, 220, 130)
            elif self.app.economy.reputation < item["reputation"]:
                price, colour = f"REP {item['reputation']}", GREY
            else:
                price, colour = "SIGN", GOLD
        elif tab == "Bounties" and item["progress"] >= item["count"]:
            price, colour = "DONE", (120, 220, 130)
        elif tab == "Upgrades" and self.app.economy.creel_limit >= item["capacity"]:
            price, colour = "OWNED", (120, 220, 130)
        elif tab == "Parts" and item["key"] in self.app.economy.owned:
            price, colour = "OWNED", (120, 220, 130)
        else:
            price, colour = f"${item['price']}", GOLD
        pill = pygame.Rect(0, 0, 110, 30)
        pill.midright = (rect.right - 16, rect.centery)
        pygame.draw.rect(screen, (40, 36, 20), pill, border_radius=15)
        pygame.draw.rect(screen, colour, pill, 2, border_radius=15)
        draw_text(screen, self.app.small_font, price, colour, pill.center, center=True)

    def draw(self, screen):
        economy = self.app.economy
        draw_backdrop(screen, self.ticks)

        header = pygame.Rect(40, 18, 720, 52)
        draw_panel(screen, header)
        draw_text(screen, self.app.font, "Shop", GOLD, (60, 30))
        draw_text(screen, self.app.small_font, f"Reputation {economy.reputation}", GREY, (200, 38))
        draw_coin(screen, (UI_WIDTH - 150, 44))
        draw_text(screen, self.app.font, f"${economy.money}", WHITE, (UI_WIDTH - 130, 30))

        for i, name in enumerate(self.TABS):
            draw_button(screen, self.app.small_font, name, self.tab_rects[i], i == self.tab, self.ticks)

        panel = pygame.Rect(40, 134, 720, 360)
        draw_panel(screen, panel)
        items = self.items()
        self.row_rects = []
        if not items:
            if self.TABS[self.tab] == "Repair":
                draw_text(screen, self.app.font, "Your gear is in good shape", GREY, (UI_WIDTH // 2, 300), center=True)
                draw_text(screen, self.app.small_font, "Parts wear down as you fish. Repair them here.", GREY, (UI_WIDTH // 2, 340), center=True)
            else:
                draw_text(screen, self.app.font, "Nothing here yet", GREY, (UI_WIDTH // 2, 300), center=True)
                draw_text(screen, self.app.small_font, "Catch some fish first, then sell them here.", GREY, (UI_WIDTH // 2, 340), center=True)
        offset = self.scroll_offset()
        for row in range(self.VISIBLE_ROWS):
            index = offset + row
            if index >= len(items):
                break
            rect = pygame.Rect(panel.left + 10, panel.top + 10 + row * 68, panel.width - 20, 60)
            self.row_rects.append(rect)
            selected = index == self.selected
            pygame.draw.rect(screen, (40, 64, 96) if selected else (24, 36, 58), rect, border_radius=8)
            if selected:
                pygame.draw.rect(screen, GOLD, rect, 2, border_radius=8)
            self.draw_row(screen, rect, items[index], selected, self.TABS[self.tab])

        if len(items) > self.VISIBLE_ROWS:
            draw_text(screen, self.app.small_font, f"{offset + 1}-{min(len(items), offset + self.VISIBLE_ROWS)} of {len(items)}", GREY, (panel.right - 110, panel.bottom - 24))

        footer = pygame.Rect(40, 506, 720, 40)
        draw_panel(screen, footer)
        if self.message:
            draw_text(screen, self.app.small_font, self.message, GOLD, footer.center, center=True)
        draw_text(screen, self.app.small_font, "Left/Right: tab    Up/Down: select    Enter or click: buy/sell    Esc: back", GREY, (UI_WIDTH // 2, 570), center=True)
