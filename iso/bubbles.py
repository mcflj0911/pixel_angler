"""Speech bubbles: what the people say, in a box above their heads. Each bubble follows its speaker across the screen, and
goes when its time is up. A bubble with no time stays until it is cleared, which is how the angler's talk stays up.
A name tag is a small gold label with a person's name, shown while the angler is near them."""
from panda3d.core import TextNode

HEAD_HEIGHT = 2.1  # World height the bubble points at: just over the speaker's head
TEXT_SCALE = 0.04  # Screen units per line of text
TAG_SCALE = 0.032  # The name tags are smaller than the words
WRAP = 0.95  # Screen units the words wrap at
GAP = 0.03  # Screen units between the bubble's bottom edge and the head it points at
INK = (0.13, 0.2, 0.27, 1)
FILL = (1, 1, 1, 0.95)
TAG_FILL = (1, 0.85, 0.35, 0.95)


class Bubbles:
    """The bubbles on screen, one per key. A key is a speaker, so a new line from them replaces the one still up."""

    def __init__(self, game):
        self.game = game
        self.root = game.aspect2d.attachNewNode("bubbles")
        self.bubbles = {}  # key -> {"speaker", "node", "bottom", "time"}

    def say(self, key, speaker, text, seconds=None, tag=False):
        """Shows text above the speaker. seconds of None keeps it up until it is cleared. A tag is a name in a small gold label."""
        self.clear(key)
        scale = TAG_SCALE if tag else TEXT_SCALE
        node_text = TextNode("bubble")
        node_text.setText(text)
        node_text.setAlign(TextNode.ACenter)
        node_text.setTextColor(*INK)
        node_text.setWordwrap(WRAP / scale)
        node_text.setCardColor(*(TAG_FILL if tag else FILL))
        node_text.setCardAsMargin(0.6, 0.6, 0.5, 0.5)
        node = self.root.attachNewNode(node_text)
        node.setScale(scale)
        bottom = node_text.getCardActual()[2]  # The box's bottom edge, in text units before the scale
        self.bubbles[key] = {"speaker": speaker, "node": node, "bottom": bottom * scale, "time": seconds}

    def clear(self, key):
        bubble = self.bubbles.pop(key, None)
        if bubble:
            bubble["node"].removeNode()

    def clear_all(self):
        for key in list(self.bubbles):
            self.clear(key)

    def speaking(self, person):
        """Whether this person has a speech bubble up, which a name tag must not cover."""
        return any(bubble["speaker"] is person and not key.startswith("name-") for key, bubble in self.bubbles.items())

    def update(self, dt):
        """Moves each bubble to sit over its speaker's head, hides it while the head is off screen, and drops it when its time is up."""
        self.root.show() if self.game.screen == "fishing" else self.root.hide()
        for key in list(self.bubbles):
            bubble = self.bubbles[key]
            if bubble["time"] is not None:
                bubble["time"] -= dt
                if bubble["time"] <= 0:
                    self.clear(key)
                    continue
            speaker = bubble["speaker"]
            point = self.game.screen_point(speaker.x, speaker.y, HEAD_HEIGHT)
            node = bubble["node"]
            if point is None:
                node.hide()
                continue
            node.show()
            node.setPos(point[0], 0, point[1] + GAP - bubble["bottom"])  # The bottom edge of the box sits just above the head
