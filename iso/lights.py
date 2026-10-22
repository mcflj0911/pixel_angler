"""Traffic lights at every crossing, on both roads. Cars and people share one cycle: the cars go on green, then amber, then the
people walk while the cars wait on red. A crossing is never open to both at once. Each light shows the phase the cars see."""
from iso.level import CROSSING_COLUMNS, ROAD_ROWS, SOUTH_ROWS
from iso.mesh import MeshBuilder

POST = (60, 60, 66)
HOUSING = (34, 34, 40)
BULBS = {"red": (230, 60, 50), "amber": (250, 190, 50), "green": (80, 220, 110)}
BULB_HEIGHT = {"red": 2.5, "amber": 2.2, "green": 1.9}  # The bulbs stack on the housing, red at the top
CYCLE = (("green", 10.0), ("amber", 2.0), ("walk", 9.0))  # Each phase, and how long it lasts in seconds
LIT = {"green": "green", "amber": "amber", "walk": "red"}  # The bulb that shows in each phase, as the cars see it


def build_light(render, x, y):
    """A traffic light on a post at (x, y): a housing with three bulbs. Returns each bulb's node by its colour."""
    root = render.attachNewNode("traffic_light")
    root.setPos(x, y, 0)
    mesh = MeshBuilder()
    mesh.box(-0.04, -0.04, 0, 0.08, 0.08, 2.4, POST)  # The post
    mesh.box(-0.14, -0.1, 1.7, 0.28, 0.2, 0.9, HOUSING)  # The housing
    mesh.build("post").reparentTo(root)
    bulbs = {}
    for colour, height in BULB_HEIGHT.items():
        bulb = MeshBuilder()
        bulb.box(-0.1, -0.12, height - 0.1, 0.2, 0.02, 0.2, BULBS[colour])
        bulbs[colour] = bulb.build("bulb")
        bulbs[colour].reparentTo(root)
    return bulbs


class Signals:
    """The shared cycle of every crossing's lights, and the lights that show it."""

    def __init__(self, render, level):
        self.level = level
        self.index = 0
        self.left = CYCLE[0][1]
        self.lights = []
        for x in CROSSING_COLUMNS:
            # One light on each pavement, beside the crossing and facing the road
            self.lights.append(build_light(render, x + 0.85, ROAD_ROWS[0] - 0.85))
            self.lights.append(build_light(render, x + 0.85, SOUTH_ROWS[1] + 1.15))
        self.show()

    @property
    def phase(self):
        return CYCLE[self.index][0]

    def allows(self, vehicle):
        """Cars may cross on green, and people on the walk light."""
        return self.phase == ("green" if vehicle else "walk")

    def update(self, dt):
        self.left -= dt
        if self.left <= 0:
            self.index = (self.index + 1) % len(CYCLE)
            self.left = CYCLE[self.index][1]
            self.show()

    def show(self):
        lit = LIT[self.phase]
        for light in self.lights:
            for colour, bulb in light.items():
                bulb.show() if colour == lit else bulb.hide()
