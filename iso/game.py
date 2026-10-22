import math
import random

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (AmbientLight, ClockObject, DirectionalLight, Fog, KeyboardButton, OrthographicLens,
                          Point2, Point3, PointLight, Vec4, loadPrcFileData)

import story
from economy import RIVALS, Economy
from fish import spawn_random_fish
from iso import saves
from iso.mesh import MeshBuilder
from iso.angler import SPEED as WALK_SPEED, Angler
from iso.audio import Audio
from iso.bubbles import Bubbles
from iso.doodads import Ambience, Car, Sailboat, Ship, Walker
from iso.fishing import IDLE, FIGHTING, CHARGING, HOOKSET, SNAGGED, AREA_INFO, HOOKSET_RING_TARGET, Fishing
from iso.hud import Hud
from iso.kiosks import build_kiosks
from iso.scenery import MOORING, build_rowboat, build_scenery
from iso.level import START, SPOTS, WIDTH, HEIGHT, KIOSKS, Level
from iso.npcs import TALK_RANGE, Chatter, build_clerks, build_npcs, build_seats
from iso.townsfolk import TOWN_EXCHANGES, Townsperson, build_townsfolk
from iso.sky import Sky
from iso.screens import Screens
from iso.waves import Waves
from weather import DAY_FRAMES, Weather

CAMERA_DISTANCE = 30  # How far the fixed camera sits from the angler
PITCH = math.degrees(math.atan(1 / math.sqrt(2)))  # The classic isometric angle, about 35 degrees
FILM_WIDTH = 26  # How many tiles across the view is. The map is wide, so the view shows more of it than it used to
SPI_GETWORKAREA = 48  # Windows: the screen, less the taskbar
SM_CXSIZEFRAME, SM_CYSIZEFRAME, SM_CYCAPTION = 32, 33, 4  # Windows: the window frame's width and height, and the title bar
HUD_LIMIT = -0.6  # Clicks lower than this, as a fraction of the window, are on the HUD
FOG_START, FOG_END = 30, 64
STAMINA_REGEN = 10  # Per second while standing still
STAMINA_WALK_REGEN = 4  # Per second while walking
FIGHT_STAMINA = 0.25  # Stamina a fight costs per second while reeling, scaled by the fish's weight

# The mood of the scene at each time of day: fog (and sky), ambient light and sunlight. Brighter than the old dark game.
MOODS = {
    "Dawn": {"fog": (0.62, 0.64, 0.74), "ambient": (0.46, 0.44, 0.48), "sun": (0.95, 0.78, 0.6)},
    "Day": {"fog": (0.56, 0.78, 0.92), "ambient": (0.56, 0.6, 0.62), "sun": (1.0, 0.97, 0.9)},
    "Dusk": {"fog": (0.86, 0.6, 0.56), "ambient": (0.5, 0.4, 0.42), "sun": (1.0, 0.6, 0.4)},
    "Night": {"fog": (0.16, 0.22, 0.34), "ambient": (0.26, 0.3, 0.4), "sun": (0.45, 0.52, 0.72)},
}
LANTERN = (1.0, 0.8, 0.5)  # Warm light carried by the angler
NIGHT_AMOUNT = {"Dawn": 0.4, "Day": 0.0, "Dusk": 0.7, "Night": 1.0}  # How much the lamps and headlights show at each time of day

# Keys held down while fishing, polled each frame
HELD = {"up": KeyboardButton.up, "down": KeyboardButton.down, "left": KeyboardButton.left, "right": KeyboardButton.right}

SHOP_NAMES = {name: kiosk["name"] for name, kiosk in KIOSKS.items()}  # The kiosks' names, as the prompt says them
DOCK = (61, 25)  # The pier tile a rowing boat is brought back to, at the day's end
CORNER_TILE = (3, 3)  # The north-west corner, the quietest part of the map, where a tin is hidden in the long grass
CORNER_HINT_RANGE = 5  # Tiles from the corner within which the angler is told something glints there
BUOY = (72, 26)  # The red buoy out at sea, which the buoy race goes round
BUOY_RANGE = 1.5  # How near the angler must row to the buoy, or the pier, to round it or finish
FORECAST_LINES = {
    "Storm": "A storm is coming in. Get the boats tied up early.",
    "Rain": "Rain is on its way. The fish bite well in it, mind.",
    "Windy": "Wind is picking up. Mind your line out there.",
    "Cloudy": "Clouds are building. Might turn wet later.",
    "Clear": "Clear skies for a good while yet.",
}  # What Sam says about the weather, when it can be forecast
ANGLER_RADIUS = 0.28  # The angler's body, as a circle on the ground. It may not touch a blocked or taken tile
MUSIC_NEAR_SPOT = 6.0  # Within this many tiles of a fishing spot, the area's own music plays. Further off, it is the town's
NAME_RANGE = 3.5  # Within this many tiles of someone, the angler sees their name above them


def mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def body_tiles(x, y, radius=ANGLER_RADIUS):
    """The tiles a circle on the ground touches: the tile of its centre, and the tiles its edge reaches."""
    tiles = {(int(math.floor(x)), int(math.floor(y)))}
    for i in range(8):
        a = i * math.tau / 8
        tiles.add((int(math.floor(x + radius * math.cos(a))), int(math.floor(y + radius * math.sin(a)))))
    return tiles


def window_prc():
    """The window's place and size, set before it opens: the whole work area of the screen, less the frame and title bar.
    The game opens at its final size, so it never starts big and then shrinks. Off Windows, Panda's default is kept."""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        area = wintypes.RECT()
        user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(area), 0)
        frame_x, frame_y = user32.GetSystemMetrics(SM_CXSIZEFRAME), user32.GetSystemMetrics(SM_CYSIZEFRAME)
        caption = user32.GetSystemMetrics(SM_CYCAPTION)
    except (AttributeError, OSError):
        return ""
    left, top = area.left + frame_x, area.top + frame_y + caption
    width = area.right - area.left - 2 * frame_x
    height = area.bottom - area.top - 2 * frame_y - caption
    return f"win-origin {left} {top}\nwin-size {width} {height}\n"


class IsoGame(ShowBase):
    def __init__(self):
        loadPrcFileData("", "window-title Pixel Angler (Isometric)\nsync-video #t\nframebuffer-multisample #t\nmultisamples 4\n" + window_prc())
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(0.56, 0.78, 0.92, 1)

        self.economy = Economy()
        self.weather = Weather()
        self.audio = Audio()
        self.level = Level()
        self.water_node = self.level.build(self.render)
        self.waves = Waves(self.render, self.level)  # Crests rolling in over the sea
        self.shopkeepers = build_kiosks(self.render)
        self.scenery = build_scenery(self.render, self.level)  # Benches, lamps, bins, moored boats and the other things that make the place alive
        # Built before the people, so they walk round the NPCs. After the scenery, so they know where the benches and deckchairs are
        self.clerks = build_clerks(self.level)  # The shopkeepers behind the counters
        self.seats = build_seats(self.scenery.benches, self.scenery.deckchairs)  # Benches and deckchairs, for anyone to rest on
        self.npcs = build_npcs(self.render, self.level, spawn_random_fish, self.clerks, self.seats)
        self.chatter = Chatter(self.npcs)  # The anglers talking to one another
        self.townsfolk = build_townsfolk(self.render, self.level, self.clerks, self.seats)  # The people about the town who are not anglers
        self.town_chatter = Chatter(self.townsfolk, TOWN_EXCHANGES)  # The townsfolk chatting with one another
        self.rowboat, self.boat_anchor = build_rowboat(self.render)  # Hired from the Boat Hire, moored at the pier until used
        self.returning = False  # Set when the day ends with the angler at sea: the boat is rowed back to the pier
        self.travel_tiles = set()  # Tiles a walker or car is on or has reserved, which the angler may not step onto
        self.last_day = None  # The game day last seen, so a new day can be noticed
        self.ambience = Ambience(self.render, self.level)  # The people, cars and boats that keep the place busy
        self.angler = Angler(self.render, START)
        self.angler.dress(self.economy.outfit_colours())  # Wears what the angler owns and has on
        self.fishing = Fishing(self.render, self.level, self.economy, self.weather, self.audio)
        self.fishing.tip_of = lambda: self.angler.rod_tip(self.render)
        self.sky = Sky(self, self.weather)
        self.dialogue = None  # The NPC talking to the angler: {"npc", "lines", "index"}, or None
        self.met = set()  # The NPCs the angler has talked to
        self.save_slot = None  # The save slot being played, chosen on the title screen. Nothing is saved until one is
        self.leave_armed = 0.0  # Seconds left in which a second Esc leaves a fight or cast in progress
        self.race = None  # The buoy race under way: {"stage": "out" or "back", "time": seconds}, or None
        self.corner_hinted = False  # Whether the angler has been told something glints in the corner
        self.rival_seen = {}  # Fish each rival had landed when last counted, so each catch is counted once
        self.glint = MeshBuilder()
        self.glint.box(CORNER_TILE[0] + 0.35, CORNER_TILE[1] + 0.35, 0, 0.3, 0.3, 0.3, (240, 200, 60))  # The tin in the long grass
        self.glint_node = self.glint.build("corner_tin")
        self.glint_node.reparentTo(self.render)
        self.hud = Hud(self)
        self.bubbles = Bubbles(self)  # The words the anglers say, above their heads
        self.stamina = 100.0
        self.frame_no = 0  # Counts frames, which drive the camera's shake
        self.weather_ticks = 0.0  # Weather ticks owed, at 60 a second, so the day runs at the same speed on any refresh rate
        self.mood = dict(MOODS["Day"])  # Blended towards the time of day each frame
        self.night = 0.0  # How dark it is, from 0 in the day to 1 at night, which turns the lamps and headlights on
        self.stack = ["title"]  # The screens on top of the game. The bottom one is the game itself.
        self.area = None  # The fishing area, once a fishing trip has started
        self.screens = Screens(self)

        self.setup_camera()
        self.setup_lights()
        self.setup_fog()
        self.setup_input()
        self.taskMgr.add(self.update, "update")
        self.audio.set_music("menu")

    # Set up

    def setup_camera(self):
        """A fixed isometric camera. It follows the angler, but its angle never changes, and the lens is orthographic."""
        self.lens = OrthographicLens()
        self.lens_aspect = self.getAspectRatio()
        self.lens.setFilmSize(FILM_WIDTH, FILM_WIDTH / self.lens_aspect)
        self.lens.setNearFar(1, 200)
        self.cam.node().setLens(self.lens)

    def fit_lens(self):
        """Keeps the view's width the same when the window is resized, so the map is never squashed."""
        aspect = self.getAspectRatio()
        if abs(aspect - self.lens_aspect) > 1e-4:
            self.lens_aspect = aspect
            self.lens.setFilmSize(FILM_WIDTH, FILM_WIDTH / aspect)

    def track_camera(self):
        x, y = self.angler.x, self.angler.y
        horizontal = CAMERA_DISTANCE * math.cos(math.radians(PITCH))
        offset = horizontal / math.sqrt(2)  # Split evenly between x and y, so the view looks along a diagonal
        shake = self.fishing.shake
        jitter_x = math.sin(self.frame_no * 1.7) * shake * 0.04
        jitter_y = math.cos(self.frame_no * 2.3) * shake * 0.04
        self.cam.setPos(x - offset + jitter_x, y - offset + jitter_y, CAMERA_DISTANCE * math.sin(math.radians(PITCH)))
        self.cam.lookAt(x, y, 0)  # Aimed at the ground, so the middle of the screen is where the angler stands

    def setup_lights(self):
        self.ambient = AmbientLight("ambient")
        self.ambient_np = self.render.attachNewNode(self.ambient)
        self.moon = DirectionalLight("sun")
        sun_np = self.render.attachNewNode(self.moon)
        sun_np.setHpr(30, -60, 0)  # Pointing down from above, and a little to one side
        self.lantern = PointLight("lantern")
        self.lantern.setAttenuation((1, 0.06, 0.02))
        self.lantern_np = self.render.attachNewNode(self.lantern)
        self.render.setLight(self.ambient_np)
        self.render.setLight(sun_np)
        self.render.setLight(self.lantern_np)

    def setup_fog(self):
        self.fog = Fog("haze")
        self.fog.setLinearRange(FOG_START, FOG_END)
        self.render.setFog(self.fog)

    def setup_input(self):
        self.accept("mouse1", self.on_press)
        self.accept("mouse1-up", self.on_release)
        self.accept("wheel_up", self.on_wheel, [1])
        self.accept("wheel_down", self.on_wheel, [-1])
        for key in ("b", "e", "f", "j", "m", "r", "t", "x", "z", "space", "enter", "escape", "arrow_left", "arrow_right",
                    "arrow_up", "arrow_down", "bracket_left", "bracket_right", "backspace", "1", "2", "3"):
            self.accept(key, self.on_key, [key])

    @property
    def screen(self):
        return self.stack[-1]

    # Mouse

    def mouse_window(self):
        """The cursor as (x, y) from -1 to 1, or None if it is outside the window."""
        if self.mouseWatcherNode is None or not self.mouseWatcherNode.hasMouse():
            return None
        return self.mouseWatcherNode.getMouse()

    def ground_under_mouse(self):
        """Where the cursor's ray meets the ground, in tile coordinates."""
        mouse = self.mouse_window()
        if mouse is None:
            return None
        near, far = Point3(), Point3()
        self.lens.extrude(Point2(*mouse), near, far)
        near = self.render.getRelativePoint(self.cam, near)
        far = self.render.getRelativePoint(self.cam, far)
        if abs(far.z - near.z) < 1e-6:
            return None
        t = -near.z / (far.z - near.z)
        return near.x + t * (far.x - near.x), near.y + t * (far.y - near.y)

    def tile_under_mouse(self):
        ground = self.ground_under_mouse()
        if ground is None:
            return None
        tile = (int(math.floor(ground[0])), int(math.floor(ground[1])))
        return tile if (0 <= tile[0] < WIDTH and 0 <= tile[1] < HEIGHT) else None

    def on_press(self):
        mouse = self.mouse_window()
        if mouse is None:
            return
        if self.screen != "fishing":
            self.screens.click(mouse)
            return
        if mouse[1] < HUD_LIMIT:
            return
        if self.dialogue:
            self.next_line()
            return
        if self.fishing.state == HOOKSET:
            self.fishing.set_hook()
            return
        tile = self.tile_under_mouse()
        if tile is None:
            return
        npc = self.npc_on(tile)
        if npc:
            self.approach(npc)
        elif self.level.water_zone(*tile):
            self.cast_at(tile)
        elif self.can_walk(*tile) and self.fishing.state == IDLE:
            self.walk_to(tile)

    def on_release(self):
        if self.screen == "fishing" and self.fishing.state == CHARGING:
            self.fishing.release_cast()

    def on_wheel(self, step):
        if self.screen == "fishing":
            self.fishing.adjust_clutch(step)

    # Keys

    def on_key(self, key):
        if self.screen != "fishing":
            self.screens.key(key)
            return
        fishing = self.fishing
        if self.dialogue:
            if key == "escape":
                self.end_talk()
            elif key in ("e", "space", "enter"):
                self.next_line()
            return
        if key == "escape":
            if fishing.state != IDLE and self.leave_armed <= 0:
                self.leave_armed = 3.0  # A cast or fight is under way: the first Esc only warns, so an accident does not lose it
                self.hud.say("Press Esc again to give up this and leave", 3)
            else:
                self.leave_armed = 0.0
                self.leave_fishing()
        elif key == "e":
            self.interact()
        elif key == "b" and fishing.state == IDLE:
            self.screens.push("shop")
        elif key == "t" and fishing.state == IDLE:
            self.screens.push("setup")
        elif key == "j" and fishing.state == IDLE:
            self.screens.push("journal")
        elif key == "f":
            on = fishing.toggle_scent()
            self.hud.say("Scent on for the next cast" if on else "Scent off")
        elif key == "r":
            fishing.restring()
        elif key == "x":
            fishing.reel_in()
        elif key == "z":
            self.sell_all()
        elif key == "bracket_left":
            fishing.adjust_clutch(-1)
        elif key == "bracket_right":
            fishing.adjust_clutch(1)
        elif key == "arrow_left" and fishing.state == SNAGGED:
            fishing.wiggle(-1)
        elif key == "arrow_right" and fishing.state == SNAGGED:
            fishing.wiggle(1)
        elif key in ("space", "enter") and fishing.state == HOOKSET:
            fishing.set_hook()
        elif key == "m":
            self.hud.say("Sound off" if self.audio.toggle_mute() else "Sound on")

    def walk_to(self, tile):
        if self.fishing.state in (FIGHTING, SNAGGED):
            self.hud.say("Land the fish or free the lure first")
            return
        path = self.level.route(self.angler.tile(), tile, self.can_walk)
        if path:
            self.fishing.reel_in(silent=True)
            self.angler.walk_to(path)

    # Talking and shopping

    def talkers(self):
        """Everyone the angler can talk to: the anglers, the townsfolk, and the people out walking who are on the map now."""
        walkers = [item for item in self.ambience.items if isinstance(item, Walker) and item.stage != "gone"]
        return self.npcs + self.townsfolk + walkers

    def npc_on(self, tile):
        for npc in self.talkers():
            if npc.tile == tile:
                return npc
        return None

    def nearby_npc(self):
        for npc in self.talkers():
            if npc.distance(self.angler.x, self.angler.y) <= TALK_RANGE:
                return npc
        return None

    def nearby_shop(self):
        """The shop whose door the angler is standing at, if any."""
        for name, (counter, _front) in self.level.counters().items():
            if KIOSKS[name].get("shop", True) and math.hypot(counter[0] - self.angler.x, counter[1] - self.angler.y) <= 1.9:
                return name
        return None

    def interact(self):
        """E talks to the NPC next to the angler, goes into the shop whose door is next to them, or sits to rest on a bench."""
        if self.angler.seated:
            self.angler.stand()
            return
        bench = self.nearby_bench()
        if bench and self.fishing.state == IDLE and not self.nearby_npc():
            self.angler.sit_down(*bench)
            self.hud.say("You sit down to rest. Stamina comes back faster. E to stand up", 4)
            return
        npc = self.nearby_npc()
        if npc:
            if self.fishing.state != IDLE:
                self.hud.say("Reel in before you talk")
            else:
                self.start_talk(npc)
            return
        shop = self.nearby_shop()
        if shop == "bait" and self.fishing.state == IDLE:
            self.screens.push("shop")
        elif shop == "food" and self.fishing.state == IDLE:
            self.screens.push("food")
        elif shop == "boats" and self.fishing.state == IDLE:
            self.screens.push("boats")

    def today(self):
        return self.weather.clock // DAY_FRAMES + 1

    # Save slots

    def choose_slot(self, slot):
        """Plays the slot: its saved game if there is one, or a new game if it is empty. Then the main menu opens."""
        loaded = saves.load(self.economy, slot)
        if loaded:
            self.weather.clock, self.met = loaded
        else:
            self.economy.reset()
            self.weather.clock = 0
            self.met = set()
        self.save_slot = slot
        self.last_day = None  # The first frame of the slot counts as a new day, which saves it straight away
        self.angler.dress(self.economy.outfit_colours())
        self.stack = ["menu"]

    def save_game(self):
        if self.save_slot is not None:
            saves.save(self.economy, self.weather.clock, self.met, self.save_slot)

    def userExit(self):
        self.save_game()
        super().userExit()

    def boat_out(self):
        """Whether the angler has a rowing boat today, so they may row out over the sea."""
        return self.economy.boat_hired(self.today())

    def near_castable(self):
        """Whether there is castable water within a few tiles of the angler."""
        tx, ty = int(self.angler.x), int(self.angler.y)
        return any(self.level.water_zone(tx + dx, ty + dy) for dx in range(-3, 4) for dy in range(-3, 4))

    def nearby_bench(self):
        """The bench the angler is standing in front of, if any, where they can sit to rest."""
        for bx, by in self.scenery.benches:
            if math.hypot(bx - self.angler.x, by - self.angler.y) <= 1.3:
                return bx, by
        return None

    def on_water(self):
        return self.level.water_zone(int(self.angler.x), int(self.angler.y)) is not None

    def free_at(self, x, y):
        """Whether the angler's body fits at this point: every tile its edge touches is open, and clear of walkers and cars."""
        for tile in body_tiles(x, y):
            if not self.can_walk(*tile) or tile in self.travel_tiles:
                return False
        return True

    def path_blocked(self, x, y):
        """Whether the next tile on the angler's path is taken, so they wait for it to clear."""
        return (x, y) in self.travel_tiles

    def can_walk(self, x, y):
        """Where the angler may step: the land, and the open water too while a boat is hired or being brought back."""
        if self.level.walkable(x, y):
            return True
        return (self.boat_out() or self.returning) and self.can_row(x, y)

    def can_row(self, x, y):
        """Water a boat can float on: open sea, clear of the moored boats and lamps, and of the sailing boats."""
        if self.level.water_zone(x, y) is None or (x, y) in self.level.blocked:
            return False
        for item in self.ambience.items:
            if isinstance(item, (Sailboat, Ship)):
                bx, by = item.position()
                radius = 3.5 if isinstance(item, Ship) else 2.2  # How far a rowing boat keeps from a sailing boat
                if math.hypot(x + 0.5 - bx, y + 0.5 - by) < radius:
                    return False
        return True

    def update_rowboat(self):
        """The rowing boat shows while it is hired or being brought back. It floats under the angler while they are out on the water,
        and stays at the last place they moored it otherwise."""
        out = self.boat_out() or self.returning
        if out:
            self.rowboat.show()
        else:
            self.rowboat.hide()
        afloat = out and self.on_water()
        self.angler.sitting = afloat
        if afloat:
            self.economy.boat_used = True  # Out on the water today, which wears the rowboat at the day's end
            self.boat_anchor = (self.angler.x, self.angler.y)
            self.rowboat.setH(self.angler.node.getH() + 90)  # The bow points where the angler faces
        self.rowboat.setPos(self.boat_anchor[0], self.boat_anchor[1], -0.05)

    def on_new_day(self):
        """A new game day has begun. A boat hired for the old day is brought back to the pier, with the angler in it
        if they are out on the water, so nobody is left at sea."""
        if self.boat_out() or not self.on_water():
            return
        if self.screen == "fishing" and self.fishing.state != IDLE:
            self.fishing.reel_in(silent=True)  # The line comes in before the boat turns for home
        self.returning = True
        self.hud.say("The day is done. Your boat is brought back to the pier", 6)
        path = self.level.route((int(self.angler.x), int(self.angler.y)), DOCK, self.can_walk)
        if path:
            self.angler.walk_to(path)
        else:
            self.angler.x, self.angler.y = DOCK[0] + 0.5, DOCK[1] + 0.5
            self.finish_return()

    def finish_return(self):
        """The boat is moored at the pier again, and the angler is on the pier with it."""
        self.returning = False
        self.boat_anchor = MOORING
        self.angler.stop()
        if self.screen == "fishing":
            self.leave_fishing()

    def objective(self):
        """What the story asks for next: the current chapter's job, and how far the angler has got with it."""
        return story.objective(self.economy)

    def boat_status(self):
        if self.returning:
            return "Boat: coming back to the pier"
        if self.boat_out():
            return "Boat hired until the day is done"
        return "No boat today"

    def approach(self, npc):
        """Clicking an NPC talks to them if they are close, and walks over to them if not."""
        if self.nearby_npc() is npc and self.fishing.state == IDLE:
            self.start_talk(npc)
            return
        stand = self.level.stand_beside(npc.tile)
        if stand:
            self.walk_to(stand)

    def start_talk(self, npc):
        if npc.is_angler and npc.name not in self.met:
            self.economy.advance_story("talk")  # Each angler met counts towards the story's first job
        self.met.add(npc.name)
        npc.talking = True
        lines = npc.lines(random)
        story_line = self.economy.talk_story(npc.name)
        if story_line:
            lines[1] = story_line  # The giver tells the story in place of a tip
        if npc.name == "Sam":  # Sam keeps an eye on the sea, so he gives the forecast when there is one
            forecast = self.weather.forecast()
            if forecast:
                lines[2] = FORECAST_LINES[forecast]
        if isinstance(npc, Townsperson):
            job_line = self.economy.talk_job(npc.name)  # Townsfolk offer and pay side jobs in place of their small talk
            if job_line:
                lines[2] = job_line
        self.dialogue = {"npc": npc, "lines": lines, "index": 0}
        self.show_line()

    def show_line(self):
        dialogue = self.dialogue
        self.bubbles.say("talk", dialogue["npc"], dialogue["lines"][dialogue["index"]])

    def next_line(self):
        if not self.dialogue:
            return
        if self.dialogue["index"] < len(self.dialogue["lines"]) - 1:
            self.dialogue["index"] += 1
            self.show_line()
        else:
            self.end_talk()

    def end_talk(self):
        if self.dialogue:
            self.dialogue["npc"].talking = False
        self.dialogue = None
        self.bubbles.clear("talk")

    def sell_all(self):
        if not self.economy.creel:
            self.hud.say("Nothing in the creel to sell")
            return
        total, count = 0, 0
        while self.economy.creel:
            total += self.economy.sell(0)["price"]
            count += 1
        self.hud.say(f"Sold {count} fish for ${total}")

    # Screens

    def enter_fishing(self):
        """Starts fishing from the menu. There is no area to pick: the angler casts where they click, and the water they choose sets the area."""
        self.stack = ["fishing"]
        if self.area is None:
            self.select_area("pond")
        self.hud.say("Walk down to the pond, the surf or the sea, and click the water to cast", 6)

    def cast_at(self, tile):
        """Casts at a water tile. Clicking another kind of water switches the tackle, the bait and the music to that area."""
        zone = self.level.water_zone(*tile)
        if zone == "boat" and not self.boat_out():
            self.hud.say("Hire a rowing boat at the Boat Hire first", 6)
            return
        if self.fishing.state == IDLE and zone != self.area:
            self.select_area(zone)
        self.fishing.start_charge(tile)

    def select_area(self, area):
        """Makes the water area the one being fished: its tackle setup, and the fishing scene's rules for it."""
        self.area = area
        self.economy.switch_setup(area)  # Each zone brings its own tackle setup
        self.fishing.set_area(area)
        self.hud.say(f"{AREA_INFO[area]['name']}", 3)

    def begin_fishing(self, area):
        """Walks to the spot for this area, and starts fishing there. Called from the area menu."""
        if area == "boat" and not self.boat_out():
            self.hud.say("Hire a rowing boat at the Boat Hire first", 6)
            return
        self.area = area
        self.stack = ["fishing"]
        self.economy.switch_setup(area)  # Each zone brings its own tackle setup
        self.fishing.set_area(area)
        spot = SPOTS[area]
        path = self.level.route(self.angler.tile(), spot, self.can_walk)
        self.angler.walk_to(path)
        self.hud.say(f"{AREA_INFO[area]['name']}: click the water to cast", 6)

    def leave_fishing(self):
        """Back to the area menu, with the lure reeled in. Leaving in the middle of a buoy race ends it."""
        self.fishing.reel_in(silent=True)
        self.end_talk()
        self.race = None
        self.stack = ["menu"]

    # Buoy race, the corner tin and the other small things about the map

    def start_race(self):
        """Puts the angler in the motor boat at its mooring, to row round the buoy and back to the pier."""
        self.race = {"stage": "out", "time": 0.0}
        self.angler.x, self.angler.y = MOORING
        self.angler.place()
        self.stack = ["fishing"]
        self.hud.say("Race! Row round the red buoy and back to the pier", 5)

    def update_race(self, dt):
        race = self.race
        race["time"] += dt
        here = (self.angler.x, self.angler.y)
        if race["stage"] == "out" and math.hypot(here[0] - BUOY[0] - 0.5, here[1] - BUOY[1] - 0.5) < BUOY_RANGE:
            race["stage"] = "back"
            self.hud.say("Round the buoy! Now home to the pier", 4)
        elif race["stage"] == "back" and math.hypot(here[0] - DOCK[0] - 0.5, here[1] - DOCK[1] - 0.5) < BUOY_RANGE:
            reward = self.economy.finish_race(race["time"])
            self.hud.say(f"Race over in {race['time']:.1f} seconds. Paid ${reward}", 5)
            self.race = None

    def update_corner(self):
        """The tin in the north-west corner: a glint once the angler is near, and the money once they stand on it."""
        if self.economy.corner_found:
            self.glint_node.hide()
            return
        tile = (int(self.angler.x), int(self.angler.y))
        if not self.corner_hinted and math.hypot(self.angler.x - CORNER_TILE[0], self.angler.y - CORNER_TILE[1]) < CORNER_HINT_RANGE:
            self.corner_hinted = True
            self.hud.say("Something glints in the long grass in the far north-west corner", 5)
        if tile == CORNER_TILE:
            self.economy.found_corner()
            self.glint_node.hide()

    def update_side_spots(self, dt):
        if self.race and self.screen == "fishing":  # The clock only runs while the angler is out in the boat, not in the shops
            self.update_race(dt)
        self.update_corner()
        if self.leave_armed > 0:
            self.leave_armed -= dt

    def update_music(self):
        """The music follows the angler. The menus have their own tune. While fishing, the area's music plays once the angler is
        at the spot or out on the water, and the town's tune plays while they walk about the place."""
        if self.screen != "fishing":
            name = "menu"
        elif self.area is None or (not self.on_water() and math.hypot(self.angler.x - SPOTS[self.area][0] - 0.5,
                                                                        self.angler.y - SPOTS[self.area][1] - 0.5) > MUSIC_NEAR_SPOT):
            name = "town"
        else:
            name = self.area
        self.audio.set_music(name)

    # Per frame

    def update(self, task):
        dt = min(ClockObject.getGlobalClock().getDt(), 0.1)
        # The weather runs at 60 ticks a second, so a day lasts the same time however often the screen refreshes
        self.weather_ticks += dt * 60
        while self.weather_ticks >= 1:
            self.weather.update()
            self.weather_ticks -= 1
        self.economy.new_day(self.weather.clock // DAY_FRAMES + 1)
        for message in self.economy.new_rewards:
            self.hud.say(message, 6)
        self.economy.new_rewards.clear()

        day = self.today()
        if day != self.last_day:
            self.last_day = day
            self.save_game()
            self.on_new_day()
        # The rod comes out only when the angler is still and near water they can cast into. Otherwise it is carried on the back.
        self.angler.rod_out = self.screen == "fishing" and not self.angler.moving() and self.near_castable()
        self.angler.update(dt, self.path_blocked)
        if self.returning and not self.angler.path:
            self.finish_return()
        self.frame_no += 1
        self.fit_lens()
        self.screens.sync()  # Menus are built and torn down as the screen stack changes
        if self.screen == "fishing":
            if self.dialogue and self.dialogue["npc"].distance(self.angler.x, self.angler.y) > TALK_RANGE * 1.5:
                self.end_talk()  # Walking off ends the talk, so the box never sits on screen with nobody to hear it
            if self.fishing.state == IDLE:
                self.walk_keys(dt)
            self.update_fishing(dt)
        else:
            self.screens.update(dt)

        self.update_npcs(dt)
        self.sky.update((self.angler.x, self.angler.y))
        self.ambience.update(dt, body_tiles(self.angler.x, self.angler.y))
        self.travel_tiles = self.ambience.taken_tiles()
        self.update_music()
        self.waves.update(dt)
        self.update_mood(dt)
        self.lantern_np.setPos(self.angler.x, self.angler.y, 2.4)
        self.update_rowboat()
        self.update_side_spots(dt)
        self.scenery.update(dt, self.frame_no)
        self.track_camera()
        self.update_hud(dt)
        self.bubbles.update(dt)
        return task.cont

    def update_name_tags(self):
        """Shows the name of anyone the angler is near, in a gold tag above them. The tag gives way to their speech bubbles."""
        near_screen = self.screen == "fishing"
        for person in self.talkers():
            key = f"name-{person.name}"
            close = near_screen and person.distance(self.angler.x, self.angler.y) <= NAME_RANGE and not self.bubbles.speaking(person)
            if close and key not in self.bubbles.bubbles:
                self.bubbles.say(key, person, person.name, tag=True)
            elif not close:
                self.bubbles.clear(key)

    def update_npcs(self, dt):
        """Each angler fishes, and says what happens with their catch. Anglers talking with the angler face them."""
        busy = {self.dialogue["npc"].name} if self.dialogue else set()
        for npc in self.npcs:  # The rivalry: each fish a pond angler lands is counted once, for the day's score
            if npc.name in RIVALS:
                seen = self.rival_seen.get(npc.name, 0)
                for _ in range(npc.catches - seen):
                    self.economy.rival_catch(npc.name)
                self.rival_seen[npc.name] = npc.catches
        for npc in self.talkers():
            if not isinstance(npc, Walker):  # The ambience already moves the people out walking
                npc.update(dt, self.frame_no)
            if npc.talking and not npc.is_angler:
                npc.face_point(self.angler.x, self.angler.y)  # Townsfolk turn to the angler while they talk. Anglers keep to the water
            for speaker, text in npc.events:
                if speaker is not npc or not npc.talking:  # Someone talking with the angler does not also say things on the side
                    self.bubbles.say(f"say-{speaker.name}", speaker, text, 3.0)
            npc.events.clear()
        self.chatter.update(dt, self.bubbles, busy)
        self.town_chatter.update(dt, self.bubbles, busy)
        self.update_name_tags()
        # The angler's face shows what they are doing: focused on the line, straining in a fight, or whatever the fish did
        fishing = self.fishing
        mood = fishing.current_mood()
        if mood == "neutral" and fishing.state != IDLE:
            mood = "focus"
        self.angler.body.set_expression(mood)

    def update_fishing(self, dt):
        held = self.held_keys()
        self.fishing.rod_out = self.angler.rod_out
        self.fishing.update(dt, (self.angler.x, self.angler.y), held)
        for message in self.fishing.events:
            self.hud.say(message)
        self.fishing.events.clear()

        # The angler's stamina drains while reeling a fish in, and refills while standing still
        if self.fishing.state == FIGHTING and held["up"]:
            cost = FIGHT_STAMINA * self.fishing.caught["fish"].weight / 3 * dt
            self.stamina = max(0.0, self.stamina - cost * 60)
        else:
            rate = STAMINA_WALK_REGEN if self.angler.moving() else STAMINA_REGEN
            if self.angler.seated:
                rate *= 3  # Resting on a bench
            self.stamina = min(100.0, self.stamina + rate * dt)

    def walk_keys(self, dt):
        """WASD walks the angler while it is not fishing. W is up the screen, which is +x +y on the ground, and D is right, which is +x -y.
        The walk stops at water and the edge of the bank, so the angler slides along the shore instead of into it."""
        if self.mouseWatcherNode is None:
            return
        held = {key: self.mouseWatcherNode.isButtonDown(KeyboardButton.ascii_key(key)) for key in "wasd"}
        forward = held["w"] - held["s"]
        side = held["d"] - held["a"]
        if not (forward or side):
            return
        length = math.hypot(forward, side)
        forward, side = forward / length, side / length
        vx, vy = (forward + side) / math.sqrt(2), (forward - side) / math.sqrt(2)
        self.unwedge()
        step = WALK_SPEED * dt
        ax, ay = self.angler.x, self.angler.y
        nx, ny = ax + vx * step, ay + vy * step
        if self.free_at(nx, ny):
            self.angler.step_to(nx, ny, vx, vy)
        elif self.free_at(nx, ay):
            self.angler.step_to(nx, ay, vx, 0)
        elif self.free_at(ax, ny):
            self.angler.step_to(ax, ny, 0, vy)

    def unwedge(self):
        """If the angler's body has been pushed into a walker, a car or a blocked tile, moves it to the nearest open spot.
        Otherwise every direction is refused and WASD appears to do nothing."""
        ax, ay = self.angler.x, self.angler.y
        if self.free_at(ax, ay):
            return
        for radius in (0.1, 0.2, 0.3, 0.45, 0.6, 0.8):
            for i in range(16):
                a = i * math.tau / 16
                nx, ny = ax + radius * math.cos(a), ay + radius * math.sin(a)
                if self.free_at(nx, ny):
                    self.angler.x, self.angler.y = nx, ny
                    self.angler.place()
                    return

    def held_keys(self):
        if self.mouseWatcherNode is None:
            return {name: False for name in HELD}
        return {name: self.mouseWatcherNode.isButtonDown(button()) for name, button in HELD.items()}

    def update_mood(self, dt):
        target = MOODS[self.weather.phase()]
        blend = min(1.0, dt * 0.5)
        for key in self.mood:
            self.mood[key] = mix(self.mood[key], target[key], blend)
        flicker = 1 + 0.03 * math.sin(self.weather.clock * 0.3) + 0.02 * math.sin(self.weather.clock * 0.9)
        self.fog.setColor(Vec4(*self.mood["fog"], 1))
        self.setBackgroundColor(*self.mood["fog"], 1)
        self.ambient.setColor(Vec4(*self.mood["ambient"], 1))
        self.moon.setColor(Vec4(*self.mood["sun"], 1))
        self.lantern.setColor(Vec4(*(c * flicker for c in LANTERN), 1))
        self.night += (NIGHT_AMOUNT[self.weather.phase()] - self.night) * blend
        self.scenery.set_night(self.night)
        for item in self.ambience.items:
            if isinstance(item, Car):
                item.glow.setAlphaScale(self.night)

    def update_hud(self, dt):
        fishing = self.fishing
        fight = None
        if fishing.state == FIGHTING:
            fight = fishing.fight
        snap = {
            "tide": self.weather.tide_name(),
            "feeding": "Feeding frenzy!" if self.weather.frenzy() else "Feeding calm",
            "bite": f"x{self.weather.mods['bite']:.2f}",
            "money": self.economy.money,
            "creel": len(self.economy.creel),
            "creel_limit": self.economy.creel_limit,
            "reputation": self.economy.reputation,
            "day": self.weather.clock // DAY_FRAMES + 1,
            "clock": self.clock_text(),
            "phase": self.weather.phase(),
            "weather": self.weather.name,
            "moon": self.weather.moon(),
            "area": AREA_INFO[self.area]["name"] if self.area else "",
            "drag": fishing.clutch,
            "depth": self.depth_text(),
            "hint": self.hint_text(),
            "gauge": self.gauge(fight),
            "ring": self.hookset_ring(),
            "boat": self.boat_status(),
            "caught": f"Caught {self.economy.total_caught}   Sold {self.economy.total_sold}   Reputation {self.economy.reputation}",
            "story": self.objective(),
            "bait": "Bait  " + "  ".join(f"{name.capitalize()} {count}" for name, count in self.economy.bait.items()),
            "wait": "WAIT..." if fishing.state == HOOKSET and not fishing.hookset_go and int(fishing.frame) // 8 % 2 == 0 else
                    ("GO!" if fishing.state == HOOKSET and fishing.hookset_go else None),
        }
        self.hud.update(dt, snap)

    def clock_text(self):
        hour = self.weather.hour()
        return f"{int(hour):02d}:{int(hour % 1 * 60):02d}"

    def depth_text(self):
        """Sea areas read how deep the lure is, its layer, and the jerk count for the micro jig."""
        fishing = self.fishing
        if fishing.area == "pond":
            return f"Bait at {fishing.pond_layer()}"
        metres = max(0, fishing.lure["depth"] - 120) / 11
        text = f"Depth {metres:.0f}m  {fishing.depth_layer()}"
        if fishing.area == "boat":
            text += f"  Jerks {fishing.jerks}"
        return text

    def hint_text(self):
        state = self.fishing.state
        if self.dialogue:
            last = self.dialogue["index"] == len(self.dialogue["lines"]) - 1
            return ("E or Enter to close" if last else "E or Enter for more") + "   Esc closes"
        if state == IDLE:
            npc = self.nearby_npc()
            if npc:
                return f"E talk to {npc.name}   Click water to cast   Esc back"
            shop = self.nearby_shop()
            if shop:
                return f"E buy at the {SHOP_NAMES[shop]}   WASD walk   Esc back"
        if state == SNAGGED:
            return "Left and Right alternately to wiggle free. Hold Up to pull."
        if state == FIGHTING:
            return "Left / Right keep the marker in the green. Hold Up to reel. [ ] or wheel for drag"
        if state == CHARGING:
            return "Release on the white tick to cast"
        if state == HOOKSET:
            return "Click or Space on the GO ring"
        if self.angler.seated:
            return "E stand up   WASD walk   Esc back"
        if state == IDLE and self.nearby_bench():
            return "E sit down and rest   WASD walk   Esc back"
        return "WASD walk   E talk   Click water to cast   B shop   T setup   Esc back"

    def gauge(self, fight):
        """The one gauge shown at the bottom centre: the cast meter, the fight or the snag."""
        fishing = self.fishing
        if fishing.state == CHARGING:
            needed = fishing.needed_power()
            tol = fishing.tolerance()
            # The white tick marks the power that lands on the target, and the bar fills as the meter sweeps
            return {"kind": "cast", "title": "CAST", "hint": "SPOT ON" if abs(fishing.cast_power - needed) <= tol else "",
                    "zone_x": 0, "zone_width": 0, "marker": needed, "progress": fishing.cast_power, "tension": 0}
        if fight is not None:
            return {"kind": "fight", "title": "FISH ON!", "hint": "Keep the marker in the green",
                    "zone_x": fight.zone_x / 360, "zone_width": fight.fish.zone_size / 360, "marker": fight.marker_x / 360,
                    "progress": fight.progress / 100, "tension": fight.tension / 100}
        if fishing.state == SNAGGED:
            return {"kind": "snag", "title": "SNAGGED!", "hint": "Alternate Left and Right",
                    "zone_x": 0, "zone_width": 0, "marker": 0, "progress": fishing.snag.progress / 100,
                    "tension": fishing.snag.tension / 100}
        return None

    def hookset_ring(self):
        """The GO ring, drawn over the lure on the screen. None while no hookset is on."""
        fishing = self.fishing
        if fishing.state != HOOKSET or not fishing.hookset_go:
            return None
        point = self.screen_point(*fishing.strike_point())
        if point is None:
            return None
        # The ring shrinks from its start size onto the target, which is drawn as the half-size ring
        scale = fishing.hookset_ring_radius() / HOOKSET_RING_TARGET * 0.5
        return {"x": point[0], "y": point[1], "scale": scale, "go": int(fishing.frame) % 12 < 6}

    def screen_point(self, x, y, z):
        """Where a world point lands on the screen, as HUD coordinates, or None if it is off screen."""
        local = Point2()
        if not self.lens.project(self.cam.getRelativePoint(self.render, Point3(x, y, z)), local):
            return None
        return (local[0] * self.getAspectRatio(), local[1])
