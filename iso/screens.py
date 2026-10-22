"""The menus: title, main menu, area select, shop, tackle setup, field journal and controls.
They use the same economy, tackle and sponsor data as the side-view game, and draw in the same light style as the HUD."""
from panda3d.core import TextNode

import story
from economy import BAIT_SHOP, BOAT_HIRE, CLOTHES, COOLER_SHOP, FOOD_SHOP, MOTOR_BOAT, SCENT_PRESS_FISH, TANK_PAY, TANK_SLOTS
from iso import saves
from weather import DAY_FRAMES
from equipment import PARTS, SHOP_PARTS, SLOT_NAMES, SLOTS, STAT_ROWS
from fish import SPECIES
from iso.hud import GREEN, GOLD, INK, MUTED, PANEL_ALPHA, label, rect
from iso.ui import INK as PANEL_INK, Button, Menu  # Dark ink for text on the light panels
from journal import AREA_NAMES, AREAS, LORE, MILESTONES, kinds_caught
from sponsors import SPONSORS

CONTROLS = [
    ("Menus", "Arrows move, Enter or click chooses, Esc goes back, M mutes the sound"),
    ("Casting", "Click the water and hold, then release on the white tick. B shop, T setup, J journal while idle"),
    ("Fishing", "Up reels in, or taps to twitch the lure or jerk the jig. Down sinks the bait or reels in fast at sea"),
    ("Strikes", "Click or Space on the GO ring when it reaches the green target"),
    ("Fights", "Left and Right move the safe zone. Hold Up to reel. [ ] or the wheel set the drag"),
    ("Snags", "Alternate Left and Right to wiggle free. Hold Up to pull harder"),
    ("Other", "WASD or click the ground to walk. E talks to the anglers and goes into the shops. X reels in, F adds scent, R restrings, Z sells the creel"),
]
TABS = ["Tackle", "Bait", "Clothes", "Upkeep", "Bounties", "Sponsors", "Sell"]


class Screen:
    """One menu. It builds its nodes under the aspect2d root, and destroys them when it closes."""

    def __init__(self, game):
        self.game = game
        self.root = game.aspect2d.attachNewNode("screen")
        self.buttons = []
        self.menu = None
        self.build()

    def build(self):
        pass

    def key(self, key):
        """Esc goes back, the arrows move, Enter chooses. Subclasses add what else they need."""
        if key == "escape":
            self.game.screens.pop()
        elif key in ("arrow_up", "arrow_down") and self.menu:
            self.menu.move(-1 if key == "arrow_up" else 1)
        elif key in ("enter", "space") and self.menu:
            self.menu.activate()

    def click(self, mouse):
        if self.menu:
            self.menu.click(*self.to_screen(mouse))

    def to_screen(self, mouse):
        """A window mouse position, as the aspect2d units the menus are laid out in."""
        return (mouse[0] * self.game.getAspectRatio(), mouse[1])

    def update(self, dt):
        pass

    def destroy(self):
        if self.menu:
            self.menu.destroy()
        self.root.removeNode()


class Title(Screen):
    def build(self):
        self.title = label(self.root, "PIXEL FISHING", 0, 0.35, scale=0.15, colour=GOLD, align=TextNode.ACenter)
        label(self.root, "Pond   -   Shore   -   Open Sea", 0, 0.12, scale=0.05, colour=INK, align=TextNode.ACenter)
        label(self.root, "A pier town, a summer of fishing. Make friends with the anglers, hire a boat, and land the big one.",
              0, 0.0, scale=0.036, colour=MUTED, align=TextNode.ACenter, wrap=1.5)
        for i, slot in enumerate(saves.SLOTS):
            label(self.root, saves.summary(slot), 0, -0.3 - i * 0.08, scale=0.05, colour=INK, align=TextNode.ACenter)
        self.prompt = label(self.root, "Press 1, 2 or 3 to play that save. Enter or click plays slot 1", 0, -0.62, scale=0.045,
                            colour=INK, align=TextNode.ACenter)
        self.ticks = 0

    def key(self, key):
        slot = int(key) if key in ("1", "2", "3") else 1
        self.game.choose_slot(slot)

    def click(self, mouse):
        self.game.choose_slot(1)

    def update(self, dt):
        self.ticks += dt
        self.prompt.show() if int(self.ticks * 2) % 2 == 0 else self.prompt.hide()


class MainMenu(Screen):
    def build(self):
        label(self.root, "PIXEL FISHING", 0, 0.7, scale=0.1, colour=GOLD, align=TextNode.ACenter)
        game = self.game
        items = [
            ("Go Fishing", game.enter_fishing),
            ("Shop", lambda: game.screens.push("shop")),
            ("Setup", lambda: game.screens.push("setup")),
            ("Journal", lambda: game.screens.push("journal")),
            ("Controls", lambda: game.screens.push("controls")),
            ("Quit", game.userExit),
        ]
        self.menu = Menu(self.root, items, top=0.4, spacing=0.14, width=0.8, height=0.11)
        self.wallet = rect(self.root, -0.8, 0.8, -0.85, -0.6, (255, 255, 255), PANEL_ALPHA)
        self.wallet_text = label(self.root, "", -0.74, -0.7, scale=0.05, colour=PANEL_INK)
        self.wallet_text.setText(f"${game.economy.money}   Caught {game.economy.total_caught}   Sold ${game.economy.total_sold}")


class Controls(Screen):
    def build(self):
        rect(self.root, -0.9, 0.9, -0.85, 0.85, (255, 255, 255), PANEL_ALPHA)
        label(self.root, "Controls", 0, 0.72, scale=0.07, colour=PANEL_INK, align=TextNode.ACenter)
        y = 0.6
        for section, text in CONTROLS:
            label(self.root, section.upper(), -0.82, y, scale=0.04, colour=GREEN)
            label(self.root, text, -0.82, y - 0.055, scale=0.034, colour=PANEL_INK, wrap=1.6)
            y -= 0.17
        label(self.root, "Esc, Enter or click to go back", 0, -0.8, scale=0.04, colour=MUTED, align=TextNode.ACenter)
        self.menu = Menu(self.root, [("Back", self.game.screens.pop)], top=-0.68, spacing=0.1, width=0.4, height=0.09)

    def key(self, key):
        if key in ("enter", "space"):
            self.game.screens.pop()
        else:
            super().key(key)


class Journal(Screen):
    def build(self):
        game = self.game
        economy = game.economy
        label(self.root, "Field Journal", 0, 0.8, scale=0.07, colour=INK, align=TextNode.ACenter)
        self.species = [(area, spec) for area in AREAS for spec in SPECIES[area]]
        self.index = 0
        items = []
        for area, spec in self.species:
            caught = spec["name"] in economy.catch_log
            items.append((f"{spec['name'] if caught else '???'}  ({AREA_NAMES[area]})", lambda: None))
        # 18 species in a column: the spacing keeps the last row above the HUD. The stats sit clear of the list's right edge.
        self.menu = Menu(self.root, items, top=0.62, spacing=0.075, width=1.1, height=0.07)
        self.detail = label(self.root, "", 0.6, 0.6, scale=0.04, colour=INK)
        self.lore = label(self.root, "", 0.6, 0.3, scale=0.034, colour=INK)
        self.record = label(self.root, "", 0.6, -0.1, scale=0.04, colour=GOLD)
        self.milestones = label(self.root, "", 0.6, -0.4, scale=0.036, colour=INK)
        self.story = label(self.root, "", 0.6, -0.78, scale=0.034, colour=GOLD, wrap=1.1)
        self.best = label(self.root, "", 0.6, 0.74, scale=0.036, colour=GOLD)
        self.refresh_detail()

    def refresh_detail(self):
        economy = self.game.economy
        area, spec = self.species[self.menu.index]
        caught = economy.catch_log.get(spec["name"])
        self.detail.setText(spec["name"] if caught else "???")
        self.lore.setText(LORE[spec["name"]] if caught else "Catch one to reveal it.")
        record = f"Caught {caught['count']}   Heaviest {caught['best_lbs']:.2f} lb   Longest {caught['best_len']:.0f} cm" if caught else ""
        if caught and caught.get("diary"):
            record += "\nDiary\n" + "\n".join(caught["diary"])  # The last few catches of this kind
        self.record.setText(record)
        lines = []
        for key, need, title, reward in MILESTONES:
            have = min(need, kinds_caught(economy.catch_log, key))
            state = "DONE" if key in economy.claimed else f"{have}/{need}  +${reward}"
            lines.append(f"{title.split(':')[0]}   {state}")
        self.milestones.setText("\n".join(lines))
        self.story.setText(story.objective(economy))
        if economy.catch_log:
            name, best = max(economy.catch_log.items(), key=lambda item: item[1]["best_lbs"])
            best_text = f"Best catch: {name}   {best['best_lbs']:.2f} lb"
        else:
            best_text = "Best catch: none yet"
        self.best.setText(f"{best_text}   Pier Cups {len(economy.trophies)}")

    def key(self, key):
        super().key(key)
        self.refresh_detail()

    def click(self, mouse):
        super().click(mouse)
        self.refresh_detail()


class Setup(Screen):
    def build(self):
        self.economy = self.game.economy
        self.slot = 0
        self.focus = 0  # 0 is the slot list, 1 is the parts list
        self.message = ""
        label(self.root, "Tackle Setup", 0, 0.85, scale=0.07, colour=INK, align=TextNode.ACenter)
        self.slot_menu = None
        self.part_menu = None
        self.stats_text = label(self.root, "", 0.2, -0.3, scale=0.04, colour=INK)  # Made before rebuild, which fills it in
        self.message_text = label(self.root, "", 0, -0.85, scale=0.04, colour=GOLD, align=TextNode.ACenter)
        self.rebuild()

    def rebuild(self, keep_part=False):
        """Rebuilds both lists. After a fit the part cursor stays where it was (keep_part); a new slot starts at the top."""
        part_row = self.part_menu.index if self.part_menu and keep_part else 0
        if self.slot_menu:
            self.slot_menu.destroy()
        if self.part_menu:
            self.part_menu.destroy()
        slot_items = [(SLOT_NAMES[slot], lambda i=i: self.select_slot(i)) for i, slot in enumerate(SLOTS)]
        self.slot_menu = Menu(self.root, slot_items, top=0.66, spacing=0.12, width=0.6, height=0.09, x=-0.6)
        self.slot_menu.index = self.slot
        self.slot_menu.refresh()
        parts = [part for part in PARTS if part["slot"] == SLOTS[self.slot]]
        part_items = [(self.part_label(part), lambda part=part: self.fit(part)) for part in parts]
        self.part_menu = Menu(self.root, part_items, top=0.66, spacing=0.12, width=1.0, height=0.09, x=0.45)
        self.part_menu.index = min(part_row, len(part_items) - 1)
        self.part_menu.refresh()
        self.parts = parts
        self.refresh_stats()

    def part_label(self, part):
        if part["key"] == self.economy.setup[part["slot"]]:
            tag = "FITTED"
        elif part["key"] in self.economy.owned:
            tag = "OWNED"
        elif part["price"] == 0:
            tag = "SPONSOR"
        else:
            tag = f"${part['price']}"
        return f"{part['name']}  -  {tag}"

    def select_slot(self, index):
        self.slot = index
        self.focus = 1
        self.rebuild()

    def fit(self, part):
        if part["key"] in self.economy.owned:
            self.economy.equip(part)
            self.message_text.setText(f"Fitted {part['name']}")
            self.game.audio.play("click")
        else:
            self.message_text.setText(f"Buy {part['name']} in the Shop for ${part['price']}")
            self.game.audio.play("error")
        self.rebuild(keep_part=True)

    def refresh_stats(self):
        stats = self.economy.stats()
        lines = []
        for key, label_text, fmt, full in STAT_ROWS:
            lines.append(f"{label_text:<16} {fmt.format(stats[key])}")
        self.stats_text.setText("COMBINED STATS\n" + "\n".join(lines))

    def key(self, key):
        if key == "escape":
            self.game.screens.pop()
        elif key == "arrow_right":
            self.focus = 1
        elif key == "arrow_left":
            self.focus = 0
        else:
            menu = self.part_menu if self.focus == 1 else self.slot_menu
            if key == "arrow_up":
                menu.move(-1)
            elif key == "arrow_down":
                menu.move(1)
            elif key in ("enter", "space"):
                if self.focus == 0:
                    self.select_slot(self.slot_menu.index)
                else:
                    menu.activate()

    def click(self, mouse):
        x, y = self.to_screen(mouse)
        if self.slot_menu.click(x, y):
            return
        self.part_menu.click(x, y)


class Shop(Screen):
    """The shop, in tabs. Each tab sorts its goods under headings, and the list scrolls when it is longer than the screen."""
    VISIBLE_ROWS = 6
    ROW_TOP = 0.5  # Centre of the first row on screen
    ROW_SPACING = 0.14

    def build(self):
        self.economy = self.game.economy
        self.tab = 0
        self.message = ""
        self.tab_buttons = []
        for i, name in enumerate(TABS):
            self.tab_buttons.append(Button(self.root, name, -0.94 + i * 0.27, 0.78, 0.25, 0.09, scale=0.03))
        self.header = label(self.root, "", -0.9, 0.92, scale=0.05, colour=INK)
        self.info = label(self.root, "", -0.9, 0.69, scale=0.034, colour=INK, wrap=1.8)
        self.description = label(self.root, "", -0.9, -0.46, scale=0.036, colour=INK, wrap=1.8)
        self.more = label(self.root, "", 0, -0.3, scale=0.032, colour=MUTED, align=TextNode.ACenter)
        self.empty = label(self.root, "Nothing here yet", 0, 0.1, scale=0.05, colour=MUTED, align=TextNode.ACenter)
        self.message_text = label(self.root, "", 0, -0.82, scale=0.04, colour=GOLD, align=TextNode.ACenter)
        label(self.root, "Left/Right: tab   Up/Down: select   Enter or click: buy or sell   Esc: back", 0, -0.66, scale=0.032,
              colour=MUTED, align=TextNode.ACenter)
        self.buttons = []  # (button, action, row index) for each row on screen that can be chosen
        self.headings = []  # Heading labels on screen
        self.cursor = 0  # Index into the tab's rows
        self.scroll = 0  # The first row on screen
        self.refresh_tabs()
        self.rebuild_rows()

    def rows(self):
        """The tab's rows, as (label, action, description). A heading has no action, so the cursor skips over it."""
        tab = TABS[self.tab]
        economy = self.economy
        if tab == "Tackle":
            rows = []
            for slot in SLOTS:
                rows.append((SLOT_NAMES[slot].upper(), None, ""))
                for part in SHOP_PARTS:
                    if part["slot"] == slot:
                        rows.append((self.part_row(part), lambda p=part: self.act(p), part["desc"]))
            return rows
        if tab == "Bait":
            rows = [("BAIT", None, "")]
            rows += [self.bait_row(item) for item in BAIT_SHOP if "kind" not in item]
            rows.append(("SCENTS", None, ""))
            rows += [self.bait_row(item) for item in BAIT_SHOP if "kind" in item]
            zone = economy.zone or "pond"
            rows.append(("PRESS YOUR OWN", None, ""))
            rows.append((f"Press {SCENT_PRESS_FISH} fish into {AREA_NAMES[zone]} scent   {len(economy.creel)} in the creel",
                         lambda z=zone: self.act({"craft": z}),
                         f"Free. Two fish from the creel make one scent for {AREA_NAMES[zone]}. Press F before a cast to use it"))
            return rows
        if tab == "Clothes":
            rows = []
            for slot, heading in (("coat", "COATS"), ("hat", "HATS"), ("trousers", "TROUSERS")):
                rows.append((heading, None, ""))
                rows += [self.clothes_row(item) for item in CLOTHES if item["slot"] == slot]
            return rows
        if tab == "Upkeep":
            rows = [("COOLERS", None, "")]
            rows += [(f"{item['name']}   holds {item['capacity']}   ${item['price']}", lambda i=item: self.act(i),
                      "A bigger cooler keeps more fish before you have to sell") for item in COOLER_SHOP]
            rows.append(("REPAIRS", None, ""))
            rows += [(f"{item['name']}   wear {item['wear']:.0f}%   ${item['price']}", lambda i=item: self.act(i),
                      "Mends the worn part back to new") for item in economy.repair_items()]
            rows.append((f"AQUARIUM   {len(economy.tank)} of {TANK_SLOTS}", None, ""))
            rows += [(f"Put {fish['name']} in the tank", lambda i=index: self.act({"tank_in": i}),
                      f"The tank keeps the fish, and pays ${TANK_PAY} a day for each one") for index, fish in enumerate(economy.creel)]
            rows += [(f"Take {fish['name']} out of the tank", lambda i=index: self.act({"tank_out": i}),
                      "Puts the fish back in the creel, ready to sell") for index, fish in enumerate(economy.tank)]
            return rows
        if tab == "Bounties":
            rows = [("TOWN CONTEST", None, "")]
            contest = economy.contest
            if contest:
                done = min(contest["progress"], contest["count"])
                rows.append((f"{contest['title']}   {done} of {contest['count']}   ${contest['reward']}", None,
                             "Finish it today. It is lost when the next game day starts"))
            else:
                rows.append(("No contest today", None, ""))
            rows.append(("PIER CUP THIS WEEK", None, ""))
            cup = economy.cup
            if cup and cup["paid"]:
                rows.append(("Won this week. The trophy is in the journal", None, ""))
            elif cup:
                done = min(cup["progress"], cup["count"])
                rows.append((f"Land {cup['count']} fish this week   {done} of {cup['count']}   ${cup['reward']}", None,
                             "A week-long contest. Win it for a trophy in the journal"))
            rows.append(("TOWNSFOLK JOB", None, ""))
            job = economy.job
            if job:
                done = min(job["progress"], job["count"])
                rows.append((f"{job['title']} for {job['giver']}   {done} of {job['count']}   ${job['reward']}", None,
                             f"Go back to {job['giver']} when it is done"))
            else:
                rows.append(("Talk to a townsperson to get a job", None, ""))
            rows.append(("CONTRACTS", None, ""))
            rows += [(f"{item['name']}   {item['progress']} of {item['count']}   ${item['price']}", lambda i=item: self.act(i),
                      "Catch the fish, and they count towards the contract") for item in economy.contracts]
            return rows
        if tab == "Sponsors":
            return [(self.sponsor_row(item), lambda i=item: self.act(i), f"Signing fits their part. Pays ${item['pay']} a day while it is fitted")
                    for item in SPONSORS]
        return [(f"{item['name']}   sell for ${item['price']}", lambda i=item: self.act(i), "Sold for its price at the shop")
                for item in economy.creel]

    def part_row(self, part):
        owned = part["key"] in self.economy.owned
        return f"{part['name']}   {'OWNED' if owned else '$' + str(part['price'])}"

    def bait_row(self, item):
        """A bait or scent row, with the area it is for. Its description says what it does and how to use it."""
        return (f"{item['name']}   {AREA_NAMES[item['area']]}   ${item['price']}", lambda i=item: self.act(i), item["desc"])

    def clothes_row(self, item):
        worn = self.economy.outfit[item["slot"]] == item["key"]
        owned = item["key"] in self.economy.wardrobe
        status = "WEARING" if worn else "OWNED" if owned else f"${item['price']}"
        return (f"{item['name']}   {status}", lambda i=item: self.act(i), "Wear it to change how the angler looks")

    def sponsor_row(self, item):
        signed = item["key"] in self.economy.sponsors
        return f"{item['name']}   {'SIGNED' if signed else 'SIGN'}   pays ${item['pay']} a day"

    def info_text(self):
        """What the tab is for, and the stock that matters to it."""
        tab = TABS[self.tab]
        economy = self.economy
        if tab == "Tackle":
            return "Buy here, then fit what you own in Setup (T). Each area keeps its own setup."
        if tab == "Bait":
            bait = "   ".join(f"{AREA_NAMES[area]} {count}" for area, count in economy.bait.items())
            scent = "   ".join(f"{AREA_NAMES[area]} {count}" for area, count in economy.attractant.items())
            return f"Bait in stock   {bait}\nScents in stock   {scent}"
        if tab == "Upkeep":
            return "Coolers hold your catch. Repairs bring worn tackle back to new. The aquarium keeps fish and pays each day."
        if tab == "Clothes":
            return "Pieces you own stay in the wardrobe. Buy once, then wear any of them."
        if tab == "Bounties":
            return "Contracts pay out when you land the fish they ask for."
        if tab == "Sponsors":
            return "Sign with a sponsor, then fit their part to be paid each day."
        return f"Fish in the creel: {len(economy.creel)} of {economy.creel_limit}"

    def rebuild_rows(self, keep_row=False):
        """Rebuilds the rows for this tab and shows the part of the list the cursor is in. After a buy or a sale the cursor stays
        on its row (keep_row); a tab change starts at the top."""
        for button, _action, _index in self.buttons:
            button.destroy()
        for heading in self.headings:
            heading.destroy()
        self.buttons, self.headings = [], []
        if not keep_row:
            self.cursor, self.scroll = 0, 0
        rows = self.rows()
        self.empty.show() if not rows else self.empty.hide()
        choosable = [i for i, row in enumerate(rows) if row[1]]
        if not choosable:
            self.description.setText("")
            self.more.setText("")
            return
        after = [i for i in choosable if i >= self.cursor]  # The cursor lands on the next row that can be chosen
        self.cursor = after[0] if after else choosable[-1]
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        if self.cursor >= self.scroll + self.VISIBLE_ROWS:
            self.scroll = self.cursor - self.VISIBLE_ROWS + 1
        last = min(len(rows), self.scroll + self.VISIBLE_ROWS)
        for slot, index in enumerate(range(self.scroll, last)):
            text, action, _desc = rows[index]
            y = self.ROW_TOP - slot * self.ROW_SPACING
            if action is None:
                self.headings.append(label(self.root, text, -0.82, y - 0.01, scale=0.032, colour=GREEN))
            else:
                button = Button(self.root, text, 0, y, 1.7, 0.12)
                button.set_selected(index == self.cursor)
                self.buttons.append((button, action, index))
        above = "more above   " if self.scroll > 0 else ""
        below = "more below" if last < len(rows) else ""
        self.more.setText(above + below)
        self.description.setText(rows[self.cursor][2])

    def refresh_tabs(self):
        for i, button in enumerate(self.tab_buttons):
            button.set_selected(i == self.tab)
        self.header.setText(f"Shop   ${self.economy.money}   Reputation {self.economy.reputation}")
        self.info.setText(self.info_text())

    def set_tab(self, tab):
        self.tab = tab % len(TABS)
        self.refresh_tabs()
        self.rebuild_rows()

    def move(self, step):
        """Moves the cursor to the next row that can be chosen, skipping the headings."""
        choosable = [i for i, row in enumerate(self.rows()) if row[1]]
        if not choosable:
            return
        pos = choosable.index(self.cursor) if self.cursor in choosable else 0
        self.cursor = choosable[(pos + step) % len(choosable)]
        self.rebuild_rows(keep_row=True)

    def act(self, item):
        economy = self.economy
        sound = self.game.audio
        tab = TABS[self.tab]
        if tab == "Tackle":
            if item["key"] in economy.owned:
                self.message = "You already own that"
            else:
                bought = economy.buy_part(item)
                self.message = f"Bought and fitted {item['name']}" if bought else "Not enough money"
        elif tab == "Bait":
            if "craft" in item:
                pressed = economy.press_scent(item["craft"])
                self.message = f"Pressed a scent for {AREA_NAMES[item['craft']]}" if pressed else "Not enough fish in the creel"
            else:
                bought = economy.buy_bait(item)
                self.message = f"Bought {item['name']}" if bought else "Not enough money"
        elif tab == "Clothes":
            if item["key"] in economy.wardrobe:
                economy.wear_clothes(item)
                self.message = f"Wearing the {item['name']}"
            elif economy.buy_clothes(item):
                self.message = f"Bought and put on the {item['name']}"
            else:
                self.message = "Not enough money"
            self.game.angler.dress(economy.outfit_colours())
        elif tab == "Upkeep":
            if "tank_in" in item:
                moved = economy.tank_in(item["tank_in"])
                self.message = "Put the fish in the tank" if moved else "The tank is full"
            elif "tank_out" in item:
                moved = economy.tank_out(item["tank_out"])
                self.message = "Took the fish out of the tank" if moved else "The cooler is full"
            elif "capacity" in item:
                if economy.creel_limit >= item["capacity"]:
                    self.message = "You already have that"
                else:
                    bought = economy.buy_cooler(item)
                    self.message = f"Bought the {item['name']}" if bought else "Not enough money"
            else:
                repaired = economy.repair(item["key"])
                self.message = f"Repaired {item['name']}" if repaired else "Not enough money"
        elif tab == "Bounties":
            self.message = "Catch the fish, and they count towards the contract"
        elif tab == "Sponsors":
            if item["key"] in economy.sponsors:
                self.message = "You already sponsor with them"
            elif economy.sign_sponsor(item):
                self.message = f"Signed with {item['name']}. Fitted their gear"
            else:
                self.message = f"They want {item['reputation']} reputation first"
        else:
            economy.sell(economy.creel.index(item))
            self.message = f"Sold {item['name']} for ${item['price']}"
        sound.play("buy" if "Bought" in self.message or "Repaired" in self.message or "Signed" in self.message else "click")
        self.message_text.setText(self.message)
        self.refresh_tabs()
        self.rebuild_rows(keep_row=True)

    def key(self, key):
        if key == "escape":
            self.game.screens.pop()
        elif key == "arrow_left":
            self.set_tab(self.tab - 1)
        elif key == "arrow_right":
            self.set_tab(self.tab + 1)
        elif key == "arrow_up":
            self.move(-1)
        elif key == "arrow_down":
            self.move(1)
        elif key in ("enter", "space"):
            rows = self.rows()
            if self.cursor < len(rows) and rows[self.cursor][1]:
                rows[self.cursor][1]()

    def click(self, mouse):
        x, y = self.to_screen(mouse)
        for i, button in enumerate(self.tab_buttons):
            if button.contains(x, y):
                self.set_tab(i)
                return
        for button, action, index in self.buttons:
            if button.contains(x, y):
                self.cursor = index
                action()
                return

    def destroy(self):
        for button, _action, _index in self.buttons:
            button.destroy()
        for heading in self.headings:
            heading.destroy()
        super().destroy()


class FoodStore(Screen):
    """The food store on the walk. Food restores stamina, so the angler can keep reeling in."""

    def build(self):
        self.economy = self.game.economy
        label(self.root, "Food Store", 0, 0.85, scale=0.07, colour=INK, align=TextNode.ACenter)
        self.header = label(self.root, "", 0, 0.7, scale=0.045, colour=INK, align=TextNode.ACenter)
        items = [(f"{item['name']}   +{item['energy']} stamina   ${item['price']}", lambda i=i: self.buy(i)) for i, item in enumerate(FOOD_SHOP)]
        self.menu = Menu(self.root, items, top=0.5, spacing=0.14, width=1.6, height=0.11)
        self.message_text = label(self.root, "", 0, -0.7, scale=0.045, colour=GOLD, align=TextNode.ACenter)
        label(self.root, "Up/Down: choose   Enter or click: buy and eat   Esc: leave", 0, -0.85, scale=0.032, colour=MUTED, align=TextNode.ACenter)
        self.refresh()

    def refresh(self):
        self.header.setText(f"Your money ${self.economy.money}")

    def buy(self, index):
        item = FOOD_SHOP[index]
        if self.economy.buy_food(item):
            self.game.stamina = min(100.0, self.game.stamina + item["energy"])
            self.message_text.setText(f"Ate the {item['name']}. Stamina up by {item['energy']}")
            self.game.audio.play("buy")
        else:
            self.message_text.setText("Not enough money")
            self.game.audio.play("error")
        self.refresh()


class BoatHire(Screen):
    """The boat hire kiosk at the pier. A hired rowing boat lasts the game day, and lets the angler row out over the open sea."""

    def build(self):
        self.economy = self.game.economy
        label(self.root, "Boat Hire", 0, 0.85, scale=0.07, colour=INK, align=TextNode.ACenter)
        self.header = label(self.root, "", 0, 0.7, scale=0.045, colour=INK, align=TextNode.ACenter)
        label(self.root, "Walk down the pier to the rowing boat. Once you have one, you can row out over the open sea.",
              0, 0.58, scale=0.034, colour=MUTED, align=TextNode.ACenter, wrap=1.6)
        self.motor_label = f"{MOTOR_BOAT['name']}   ${MOTOR_BOAT['price']}   no daily fee"
        self.items = [(f"{BOAT_HIRE['name']}   ${BOAT_HIRE['price']}", self.hire), (self.motor_label, self.buy_motor)]
        self.items.append(("Repair the rowboat", self.repair))
        self.items.append(("Buoy race in the motor boat", self.race))
        items = self.items
        self.menu = Menu(self.root, items, top=0.36, spacing=0.14, width=1.6, height=0.11)
        self.message_text = label(self.root, "", 0, -0.7, scale=0.045, colour=GOLD, align=TextNode.ACenter)
        label(self.root, "Enter or click: choose   Esc: leave", 0, -0.85, scale=0.032, colour=MUTED, align=TextNode.ACenter)
        self.refresh()

    def refresh(self):
        day = self.game.weather.clock // DAY_FRAMES + 1
        wear = self.economy.boat_wear
        self.menu.buttons[2].label.setText(
            f"Repair the rowboat   ${self.economy.boat_repair_cost()}   wear {wear:.0f}%" if wear > 0 else "Repair the rowboat   no repair needed")
        if self.economy.motorboat:
            self.header.setText("Your motor boat is always ready at the pier")
            self.menu.buttons[1].label.setText("Motor boat   OWNED")
        elif self.economy.boat_hired(day):
            self.header.setText("Your boat is hired for today")
        else:
            self.header.setText(f"Your money ${self.economy.money}")

    def hire(self):
        day = self.game.weather.clock // DAY_FRAMES + 1
        if self.economy.motorboat:
            self.message_text.setText("You have the motor boat. Head out along the pier")
            self.game.audio.play("bell")
        elif self.economy.hire_boat(day):
            self.message_text.setText("Boat hired. Head out along the pier")
            self.game.audio.play("bell")
        elif self.economy.boat_hired(day):
            self.message_text.setText("You already have a boat for today")
            self.game.audio.play("error")
        else:
            self.message_text.setText("Not enough money")
            self.game.audio.play("error")
        self.refresh()

    def repair(self):
        economy = self.economy
        if economy.boat_wear <= 0:
            self.message_text.setText("The rowboat needs no repair")
            self.game.audio.play("error")
        elif economy.repair_boat():
            self.message_text.setText("Rowboat repaired and as good as new")
            self.game.audio.play("buy")
        else:
            self.message_text.setText(f"Not enough money. The repair is ${economy.boat_repair_cost()}")
            self.game.audio.play("error")
        self.refresh()

    def race(self):
        """Starts the buoy race in the motor boat. The game takes over from here."""
        if not self.economy.motorboat:
            self.message_text.setText("The buoy race needs the motor boat")
            self.game.audio.play("error")
            return
        self.game.start_race()

    def buy_motor(self):
        if self.economy.buy_motorboat():
            self.message_text.setText("Bought the motor boat. It is moored at the pier")
            self.game.audio.play("buy")
        elif self.economy.motorboat:
            self.message_text.setText("You already own the motor boat")
            self.game.audio.play("error")
        else:
            self.message_text.setText("Not enough money")
            self.game.audio.play("error")
        self.refresh()


SCREENS = {"title": Title, "menu": MainMenu, "shop": Shop, "setup": Setup, "journal": Journal, "controls": Controls,
           "food": FoodStore, "boats": BoatHire}


class Screens:
    """Keeps the menus in step with the game's screen stack. The fishing scene itself has no menu."""

    def __init__(self, game):
        self.game = game
        self.built = None
        self.current = None
        self.sync()

    def push(self, name):
        self.game.stack.append(name)
        self.sync()

    def pop(self):
        if len(self.game.stack) > 1:
            self.game.stack.pop()
        self.sync()

    def sync(self):
        """Builds the menu for the top of the stack, and drops the one that was there before."""
        top = self.game.stack[-1]
        if top == self.built:
            return
        if self.current:
            self.current.destroy()
            self.current = None
        self.built = top
        if top in SCREENS:
            self.current = SCREENS[top](self.game)

    def key(self, key):
        self.sync()
        if self.current:
            self.current.key(key)
            self.sync()

    def click(self, mouse):
        self.sync()
        if self.current:
            self.current.click(mouse)
            self.sync()

    def update(self, dt):
        self.sync()
        if self.current:
            self.current.update(dt)
