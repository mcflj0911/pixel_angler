from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode, TransparencyAttrib

from iso.hud import card, rgba

PANEL_FILL = (255, 255, 255)  # Light panels, like the HUD, so the menus feel bright
PANEL_EDGE = (150, 190, 220)
BUTTON_FILL = (236, 244, 250)
BUTTON_FILL_SELECTED = (46, 142, 214)  # Selected buttons take the HUD's blue
GOLD = (246, 184, 52)
HIGHLIGHT = (255, 255, 255)
INK = (34, 52, 70)
WHITE = (255, 255, 255)
GREY = (110, 130, 148)
GREEN = (84, 190, 92)
RED = (240, 96, 80)


def panel(parent, left, right, bottom, top, colour=PANEL_FILL, alpha=1.0, edge=PANEL_EDGE):
    """A translucent rounded-ish panel. Edge is a thin frame drawn just inside the panel."""
    node = card(parent, left, right, bottom, top, "panel")
    node.setColor(*[c / 255 for c in colour], alpha)
    if edge:
        border = 0.004
        for left_, right_, bottom_, top_ in (
            (left, right, top - border, top), (left, right, bottom, bottom + border),
            (left, left + border, bottom, top), (right - border, right, bottom, top),
        ):
            strip = card(parent, left_, right_, bottom_, top_, "edge")
            strip.setColor(*[c / 255 for c in edge], 1)
    return node


def text(parent, string, x, y, scale=0.045, colour=WHITE, align=TextNode.ALeft, shadow=True):
    """Text with a drop shadow, positioned in the parent's own coordinates. Returns the text and its shadow, so both can be removed together."""
    shadow_text = None
    if shadow:
        shadow_text = OnscreenText(string, pos=(x + 0.003, y - 0.003), scale=scale, fg=(0, 0, 0, 0.8), align=align, parent=parent, mayChange=True)
    return OnscreenText(string, pos=(x, y), scale=scale, fg=rgba(colour), align=align, parent=parent, mayChange=True), shadow_text


class Button:
    """A menu row: a filled rectangle with a label that lights up when selected or hovered."""

    def __init__(self, parent, label, x, y, w, h, scale=0.045):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.back = card(parent, x - w / 2, x + w / 2, y - h / 2, y + h / 2, "button")
        self.back.setTransparency(TransparencyAttrib.MAlpha)
        self.label, self.shadow = text(parent, label, x, y - scale * 0.35, scale=scale, align=TextNode.ACenter)
        self.selected = False
        self.set_selected(False)

    def set_selected(self, selected):
        self.selected = selected
        fill = BUTTON_FILL_SELECTED if selected else BUTTON_FILL
        self.back.setColor(*[c / 255 for c in fill], 1.0)
        self.label.setFg(rgba(WHITE if selected else INK))

    def contains(self, mouse_x, mouse_y):
        return abs(mouse_x - self.x) <= self.w / 2 and abs(mouse_y - self.y) <= self.h / 2

    def destroy(self):
        self.back.removeNode()
        self.label.destroy()
        if self.shadow:
            self.shadow.destroy()


class Menu:
    """A vertical list of buttons, driven by the arrow keys, Enter and the mouse. The owner supplies the actions."""

    def __init__(self, parent, items, top, spacing=0.11, width=0.6, height=0.085, x=0):
        """items: (label, action) pairs. top is the height of the first row, and x its centre, in screen units."""
        self.buttons = []
        self.actions = []
        for i, (label, action) in enumerate(items):
            self.buttons.append(Button(parent, label, x, top - i * spacing, width, height))
            self.actions.append(action)
        self.index = 0
        self.refresh()

    def refresh(self):
        for i, button in enumerate(self.buttons):
            button.set_selected(i == self.index)

    def move(self, step):
        self.index = (self.index + step) % len(self.buttons)
        self.refresh()

    def activate(self):
        self.actions[self.index]()

    def hover(self, mouse_x, mouse_y):
        for i, button in enumerate(self.buttons):
            if button.contains(mouse_x, mouse_y):
                if i != self.index:
                    self.index = i
                    self.refresh()
                return i
        return None

    def click(self, mouse_x, mouse_y):
        i = self.hover(mouse_x, mouse_y)
        if i is not None:
            self.actions[i]()
            return True
        return False

    def destroy(self):
        for button in self.buttons:
            button.destroy()
