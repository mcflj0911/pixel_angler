"""Waves: pale crests on the sea that roll in towards the beach, and fade out as they reach the surf. Each crest is a thin
strip lying along the shore, moving at its own pace, so the sea never looks like a copy of itself."""
import random

from iso.level import HEIGHT, WIDTH, coast
from iso.mesh import MeshBuilder

CRESTS = 36  # Crests on the water at once
CREST_LENGTH = 1.1  # Tiles along the shore
CREST_WIDTH = 0.14  # Tiles across, in the direction the wave moves
CREST_HEIGHT = 0.03
CREST_Z = -0.1  # Just above the water, which sits at -0.12
CREST_COLOUR = (236, 248, 255)
CREST_ALPHA = 0.7  # The most a crest shows, so the water still reads as water
FADE_TILES = 2.0  # Tiles over which a crest fades in from the surf, and out near the beach


class Waves:
    """A pool of crests on the open sea. Each one drifts in towards the coast, fading out as it breaks,
    then starts again further out to sea."""

    def __init__(self, render, level):
        self.level = level
        self.rng = random.Random(11)
        mesh = MeshBuilder()
        mesh.box(0, 0, 0, CREST_WIDTH, CREST_LENGTH, CREST_HEIGHT, CREST_COLOUR)
        model = mesh.build("crest", transparent=True)
        model.setDepthWrite(False)  # The crests do not hide what is under the water
        model.setLightOff()  # Pale and bright, whatever the time of day
        self.crests = []
        for _ in range(CRESTS):
            node = model.copyTo(render)
            crest = {"node": node, "x": 0.0, "y": 0.0, "speed": 0.0}
            self.spawn(crest, anywhere=True)
            self.crests.append(crest)

    def spawn(self, crest, anywhere=False):
        """Puts a crest on a random sea row, out past the surf. Crests start at the far edge, or anywhere when the pool is new."""
        crest["y"] = self.rng.randrange(HEIGHT)
        shore = coast(int(crest["y"]))
        far = WIDTH - 1.0
        crest["x"] = self.rng.uniform(shore + FADE_TILES, far) if anywhere else far
        crest["speed"] = self.rng.uniform(0.8, 1.3)  # Tiles per second towards the beach

    def update(self, dt):
        for crest in self.crests:
            crest["x"] -= crest["speed"] * dt
            shore = coast(int(crest["y"]))
            if crest["x"] < shore + 1.0:
                self.spawn(crest)
                shore = coast(int(crest["y"]))
            # Fades in once it is out past the surf, and fades out as it nears the beach
            reach = (crest["x"] - shore - 1.0) / FADE_TILES
            alpha = max(0.0, min(1.0, reach)) * CREST_ALPHA
            node = crest["node"]
            node.setPos(crest["x"], crest["y"] + 0.5, CREST_Z)
            node.setColorScale(1, 1, 1, alpha)
