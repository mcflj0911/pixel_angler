from panda3d.core import LineSegs

from iso.hud import card
from iso.level import HEIGHT, WIDTH
from weather import PHASE_TINT, RAIN_DROPS, TINT

RAIN = (170, 196, 230)
WIND = (214, 226, 236)
RAIN_SPAN = 26  # How far around the angler the rain and wind fall, in tiles
RAIN_HEIGHT = 9  # Height the rain starts from


class Sky:
    """Rain, wind streaks, the dawn, dusk and storm tint, and lightning.
    Driven by the Weather object from weather.py, which keeps the state. This only draws it."""

    def __init__(self, base, weather):
        self.weather = weather
        self.root = base.render.attachNewNode("sky")
        self.rain_root = self.root.attachNewNode("rain")
        self.wind_root = self.root.attachNewNode("wind")
        self.tint = card(base.render2d, -1, 1, -1, 1, "tint")
        self.tint.setBin("fixed", -5)  # Over the scene, under the HUD
        self.tint.hide()

    def update(self, focus):
        """focus: the (x, y) the camera looks at, so the weather travels with the angler."""
        name = self.weather.name
        self.update_rain(name, focus)
        self.update_wind(name, focus)
        self.update_tint(name)

    def update_rain(self, name, focus):
        self.rain_root.removeNode()
        self.rain_root = self.root.attachNewNode("rain")
        count = RAIN_DROPS.get(name, 0)
        if not count:
            return
        lines = LineSegs()
        lines.setColor(RAIN[0] / 255, RAIN[1] / 255, RAIN[2] / 255, 0.7)
        lines.setThickness(1.2)
        for i in range(count):
            # Each drop falls on its own cycle, so the rain looks steady rather than moving in a block
            fall = (self.weather.frame * 0.22 + i * 0.37) % 1.0
            x = focus[0] + ((i * 0.618) % 1.0 - 0.5) * RAIN_SPAN
            y = focus[1] + ((i * 0.377) % 1.0 - 0.5) * RAIN_SPAN
            if not (0 <= x <= WIDTH and 0 <= y <= HEIGHT):
                continue  # Keep the rain over the map
            z_top = RAIN_HEIGHT * (1 - fall) + 0.5
            lines.moveTo(x, y, z_top)
            lines.drawTo(x - 0.15, y, z_top - 0.9)
        self.rain_root.attachNewNode(lines.create())

    def update_wind(self, name, focus):
        self.wind_root.removeNode()
        self.wind_root = self.root.attachNewNode("wind")
        if name != "Windy":
            return
        lines = LineSegs()
        lines.setColor(WIND[0] / 255, WIND[1] / 255, WIND[2] / 255, 0.6)
        for i in range(14):
            offset = ((i * 0.71 - self.weather.frame * 0.02) % 1.0 - 0.5) * RAIN_SPAN
            x = focus[0] + offset
            y = focus[1] + ((i * 0.37) % 1.0 - 0.5) * RAIN_SPAN
            if not (0 <= x <= WIDTH and 0 <= y <= HEIGHT):
                continue  # Keep the wind streaks over the map
            z = 1.2 + (i % 3) * 0.6
            lines.moveTo(x, y, z)
            lines.drawTo(x + 1.3, y, z)
        self.wind_root.attachNewNode(lines.create())

    def update_tint(self, name):
        """Darkens the sky in bad weather, tints dawn and dusk, and flashes with lightning in a storm."""
        weather = self.weather
        alpha = TINT.get(name, 0) / 255
        colour = (10, 16, 40)
        phase_tint = PHASE_TINT[weather.phase()]
        if phase_tint:
            colour = phase_tint[:3]
            alpha = max(alpha, phase_tint[3] / 255)
        if weather.flash > 0:
            colour = (255, 255, 255)
            alpha = max(alpha, min(1.0, 14 * weather.flash / 255))
            weather.flash -= 1
        if alpha <= 0:
            self.tint.hide()
            return
        self.tint.show()
        self.tint.setColor(*[c / 255 for c in colour], alpha)
