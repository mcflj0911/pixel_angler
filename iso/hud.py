"""The on-screen HUD, laid out like Fishing Planet: solid light panels along the edges, bright bars for the
cast, the fight and the snag, short messages that pop up in the middle of the screen, and a dialogue box for the NPCs.
The panels are solid, so text from one panel never shows through another."""
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import CardMaker, TextNode, TransparencyAttrib

PANEL = (24, 32, 44)  # Panels are dark slate, a little see-through, so the place shows through them faintly
PANEL_ALPHA = 0.86
INK = (236, 241, 246)  # Light text on the dark panels
MUTED = (146, 162, 180)
BLUE = (46, 142, 214)
GREEN = (84, 190, 92)
GOLD = (246, 184, 52)
CORAL = (240, 96, 80)
TRACK = (58, 70, 86)  # Empty part of a bar
WHITE = (255, 255, 255)
MESSAGE_LINE = 0.052  # Height of one line of a pop-up message, in screen units
MESSAGE_CHARS = 58  # Characters in a line of a pop-up message before it wraps
CHAR_WIDTH = 0.55  # Rough width of one character, as a multiple of the text's scale, for sizing message panels
GAUGE_LEFT = 0.465  # The gauge sits in the bottom right panel, and its bars run this far across it
GAUGE_WIDTH = 0.44
GAUGE_CENTRE = GAUGE_LEFT + GAUGE_WIDTH / 2


def rgba(colour, alpha=1.0):
    """A 0 to 255 colour as the 0 to 1 RGBA that Panda3D's text and cards want."""
    return tuple(c / 255 for c in colour) + (alpha,)


def card(parent, left, right, bottom, top, name="card"):
    cm = CardMaker(name)
    cm.setFrame(left, right, bottom, top)
    node = parent.attachNewNode(cm.generate())
    node.setTransparency(TransparencyAttrib.MAlpha)
    return node


def rect(parent, left, right, bottom, top, colour, alpha=1.0, name="rect"):
    node = card(parent, left, right, bottom, top, name)
    node.setColor(*rgba(colour, alpha))
    return node


def label(parent, string, x, y, scale=0.045, colour=INK, align=TextNode.ALeft, wrap=None):
    """Text in screen units. wrap is the width in screen units to break lines at, so long text stays inside its panel."""
    return OnscreenText(string, pos=(x, y), scale=scale, fg=rgba(colour), align=align, parent=parent, mayChange=True,
                        wordwrap=wrap / scale if wrap else None)


class Bar:
    """A horizontal bar: a track, and a coloured fill that grows from the left edge."""

    def __init__(self, parent, left, right, bottom, top, colour):
        self.track = rect(parent, left, right, bottom, top, TRACK, name="track")
        # The fill is a unit-wide card placed at the left edge, so scaling it grows the bar from the left
        self.fill = card(parent, 0, 1, bottom, top, "fill")
        self.fill.setColor(*rgba(colour))
        self.fill.setX(left)
        self.width = right - left

    def set(self, fraction):
        fraction = max(0.0, min(1.0, fraction))
        self.fill.setSx(max(0.0001, fraction * self.width))

    def set_colour(self, colour):
        self.fill.setColor(*rgba(colour))


class Hud:
    """Builds every HUD element once, and updates them from a snapshot the game builds each frame."""

    def __init__(self, base):
        self.base = base
        self.log = []  # Messages as [text, seconds left], newest last
        self.bottom = base.a2dBottomCenter
        self.top_left = base.a2dTopLeft
        self.top_right = base.a2dTopRight

        # Top left: the angler's card with money, creel, reputation and the time of day
        self.status_back = rect(self.top_left, 0.02, 0.98, -0.8, -0.02, PANEL, PANEL_ALPHA, "status")
        self.status_lines = [label(self.top_left, "", 0.12, -0.14 - i * 0.075, scale=0.042) for i in range(7)]


        # Top right: the area, drag and depth
        self.area_back = rect(self.top_right, -0.98, -0.02, -0.02, -0.2, PANEL, PANEL_ALPHA, "area")
        self.area_text = label(self.top_right, "", -0.1, -0.1, scale=0.05, align=TextNode.ARight)
        self.depth_text = label(self.top_right, "", -0.1, -0.16, scale=0.04, colour=MUTED, align=TextNode.ARight)
        # Under it: the story's current chapter, and what the angler has to do for it next
        self.story_back = rect(self.top_right, -0.98, -0.02, -0.24, -0.56, PANEL, PANEL_ALPHA, "story_panel")
        self.story_title = label(self.top_right, "STORY", -0.94, -0.3, scale=0.032, colour=GOLD)
        self.story_text = label(self.top_right, "", -0.94, -0.36, scale=0.036, colour=INK, wrap=0.9)

        # Bottom left: the angler's tips. The hint for what to do next, the tide, how the fish are feeding, how strong the bite is
        # in this weather, and the bait in the creel
        corner = base.a2dBottomLeft  # Pinned to the bottom left corner of the screen
        self.tips_back = rect(corner, 0.02, 0.55, 0.03, 0.36, PANEL, PANEL_ALPHA, "tips_panel")
        self.tips_title = label(corner, "ANGLER'S TIPS", 0.07, 0.31, scale=0.032, colour=MUTED)
        self.hint_text = label(corner, "", 0.07, 0.265, scale=0.03, colour=INK, wrap=0.46)
        self.tide_text = label(corner, "", 0.07, 0.165, scale=0.032, colour=INK)
        self.feed_text = label(corner, "", 0.07, 0.125, scale=0.032, colour=INK)
        self.bite_text = label(corner, "", 0.07, 0.085, scale=0.032, colour=INK)
        self.bait_text = label(corner, "", 0.07, 0.045, scale=0.032, colour=MUTED, wrap=0.46)

        # Bottom right: one gauge at a time. The cast meter, the fight or the snag.
        self.gauge_back = rect(self.bottom, 0.42, 0.95, 0.25, 0.4, PANEL, PANEL_ALPHA, "gauge_panel")
        self.gauge_title = label(self.bottom, "", GAUGE_CENTRE, 0.33, scale=0.04, align=TextNode.ACenter)
        self.gauge_track = Bar(self.bottom, GAUGE_LEFT, GAUGE_LEFT + GAUGE_WIDTH, 0.27, 0.31, TRACK)
        self.gauge_zone = rect(self.bottom, 0, 0.1, 0.27, 0.31, GREEN, 0.55, "zone")
        self.gauge_marker = rect(self.bottom, -0.005, 0.005, 0.25, 0.33, WHITE, 1.0, "marker")  # The cast's white tick, as the controls say
        self.gauge_progress = Bar(self.bottom, GAUGE_LEFT, GAUGE_LEFT + GAUGE_WIDTH, 0.215, 0.245, GREEN)
        self.gauge_tension = Bar(self.bottom, GAUGE_LEFT, GAUGE_LEFT + GAUGE_WIDTH, 0.18, 0.205, CORAL)
        self.gauge_hint = label(self.bottom, "", GAUGE_CENTRE, 0.1, scale=0.034, colour=MUTED, align=TextNode.ACenter, wrap=0.5)
        self.gauge_nodes = [self.gauge_back, self.gauge_title, self.gauge_track.track, self.gauge_track.fill, self.gauge_zone,
                            self.gauge_marker, self.gauge_progress.track, self.gauge_progress.fill,
                            self.gauge_tension.track, self.gauge_tension.fill, self.gauge_hint]
        self.set_gauge(False)

        # Centre: messages that pop up on a panel of their own, sized to their text
        self.message_back = card(self.bottom, 0, 1, 0, 1, "message_panel")
        self.message_back.setColor(*rgba(PANEL, PANEL_ALPHA))
        self.message = label(self.bottom, "", 0, 0.5, scale=0.05, align=TextNode.ACenter, wrap=1.6)
        self.message_back.hide()
        self.ring = rect(base.render2d, -0.1, 0.1, -0.1, 0.1, WHITE, 0.0, "ring")
        self.ring.hide()
        self.wait_text = label(base.render2d, "", 0, 0, scale=0.07, colour=WHITE, align=TextNode.ACenter)
        self.wait_text.hide()

    def set_gauge(self, visible):
        for node in self.gauge_nodes:
            node.show() if visible else node.hide()

    def say(self, text, seconds=4.0):
        self.log.append([text, seconds])
        del self.log[:-3]

    def update(self, dt, snap):
        """snap is a dict the game builds each frame. Keys used here: money, creel, creel_limit, reputation, day, clock, moon,
        weather, phase, area, drag, depth, hint, tide, feeding, bite, bait, gauge, ring, wait."""
        self.status_lines[0].setText(f"${snap['money']}   Creel {snap['creel']}/{snap['creel_limit']}")
        self.status_lines[1].setText(f"Reputation {snap['reputation']}   Day {snap['day']}")
        self.status_lines[2].setText(f"{snap['clock']}  {snap['phase']}  {snap['weather']}")
        self.status_lines[3].setText(f"{snap['moon']} moon")
        self.status_lines[4].setText(snap["boat"])
        self.status_lines[5].setText(snap["caught"])
        self.story_text.setText(snap["story"])
        self.status_lines[6].setText(snap["bait"])
        self.area_text.setText(f"{snap['area']}   Drag {snap['drag']:.1f}x")
        self.depth_text.setText(snap["depth"])
        self.hint_text.setText(snap["hint"])
        self.tide_text.setText(f"Tide {snap['tide']}")
        self.feed_text.setText(snap["feeding"])
        self.bite_text.setText(f"Bites {snap['bite']} in {snap['weather']}")
        self.bait_text.setText(snap["bait"])

        for entry in self.log:
            entry[1] -= dt
        self.log = [entry for entry in self.log if entry[1] > 0]
        self.update_messages()

        gauge = snap["gauge"]
        self.set_gauge(gauge is not None)
        if gauge:
            self.gauge_title.setText(gauge["title"])
            self.gauge_hint.setText(gauge["hint"])
            # The fight shows its safe zone and marker. The cast shows only the marker, at the power that hits the target.
            self.gauge_marker.show()
            self.gauge_marker.setX(GAUGE_LEFT + GAUGE_WIDTH * gauge["marker"])
            if gauge["kind"] == "fight":
                self.gauge_zone.show()
                self.gauge_zone.setSx(gauge["zone_width"] * GAUGE_WIDTH)
                self.gauge_zone.setX(GAUGE_LEFT + GAUGE_WIDTH * gauge["zone_x"])
            else:
                self.gauge_zone.hide()
            self.gauge_progress.set(gauge["progress"])
            self.gauge_tension.set(gauge["tension"])
            self.gauge_tension.set_colour(CORAL if gauge["tension"] > 0.75 else GOLD if gauge["tension"] > 0.4 else GREEN)

        ring = snap["ring"]
        if ring:
            self.ring.show()
            self.ring.setPos(ring["x"], 0, ring["y"])
            self.ring.setScale(ring["scale"])
            self.ring.setColor(*rgba(GOLD if ring["go"] else WHITE, 0.9))
        else:
            self.ring.hide()
        if snap["wait"]:
            self.wait_text.setText(snap["wait"])
            self.wait_text.show()
        else:
            self.wait_text.hide()

    def update_messages(self):
        """Puts the messages on their panel, which grows with the number of lines and the length of the longest one."""
        self.message.setText("\n".join(entry[0] for entry in self.log))
        if not self.log:
            self.message_back.hide()
            return
        lines = sum(-(-len(entry[0]) // MESSAGE_CHARS) for entry in self.log)  # Long messages wrap onto more lines
        longest = min(MESSAGE_CHARS, max(len(entry[0]) for entry in self.log))
        width = min(1.7, longest * 0.05 * CHAR_WIDTH + 0.12)
        top, bottom = 0.545, 0.5 - MESSAGE_LINE * (lines - 1) - 0.04  # The text sits on its baseline at 0.5
        self.message_back.setPos(-width / 2, 0, bottom)
        self.message_back.setScale(width, 1, top - bottom)
        self.message_back.show()
