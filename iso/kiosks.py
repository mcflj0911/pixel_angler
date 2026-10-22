"""The kiosks: open-fronted stalls with a counter, goods on shelves, a striped awning with the shop's name on it,
and a shopkeeper standing behind the counter. Customers buy from the counter, so nothing is entered."""
from panda3d.core import TextNode

from iso.level import KIOSKS
from iso.mesh import MeshBuilder
from iso.people import build_body

WOOD = (120, 84, 56)
COUNTER = (150, 110, 72)
COUNTER_TOP = (196, 170, 130)
BACK = (232, 224, 206)
TRIM = (240, 236, 224)  # Light edging round each sign board
TEXT = (250, 250, 245)
SIGN_SCALE = 0.2  # The size of the name on its board
SIGN_WIDTH = 1.9  # The widest a name may be, so it fits the board with a margin either side
SHOPKEEPER_COAT = {"bait": (60, 120, 80), "food": (210, 110, 60), "boats": (40, 90, 150),
                   "icecream": (240, 240, 240), "souvenirs": (180, 90, 150)}
AWNING = {"bait": ((70, 150, 96), (240, 240, 232)), "food": ((236, 130, 60), (250, 246, 238)), "boats": ((40, 110, 170), (246, 244, 236)),
          "icecream": ((240, 110, 150), (255, 250, 245)), "souvenirs": ((230, 190, 60), (250, 246, 238))}
GOODS = [(200, 70, 60), (60, 120, 200), (230, 190, 60), (90, 160, 100), (230, 230, 235), (150, 100, 190)]


def build_kiosk(render, name, kiosk):
    """Builds one kiosk under render. Its footprint is two tiles wide, starting at its x and y, with the counter on row y."""
    x, y = kiosk["x"], kiosk["y"]
    stripes, _ = AWNING[name]
    mesh = MeshBuilder()
    # Corner posts, the back wall and the shelves behind the counter
    for px in (x + 0.02, x + 1.94):
        for py in (y + 0.02, y + 1.9):
            mesh.box(px, py, 0, 0.06, 0.06, 2.0, WOOD)
    mesh.box(x + 0.02, y + 1.85, 0.0, 1.96, 0.08, 1.7, BACK)
    for shelf in (1.0, 1.5):
        mesh.box(x + 0.02, y + 1.6, shelf, 1.96, 0.25, 0.05, WOOD)
        for i in range(4):
            mesh.box(x + 0.15 + i * 0.45, y + 1.65, shelf + 0.05, 0.25, 0.14, 0.18, GOODS[(i + int(shelf * 3)) % len(GOODS)])
    # The counter, its top, and the goods laid on it
    mesh.box(x, y + 0.02, 0, 2.0, 0.42, 0.85, COUNTER)
    mesh.box(x - 0.05, y - 0.02, 0.85, 2.1, 0.5, 0.06, COUNTER_TOP)
    for i in range(3):
        mesh.box(x + 0.2 + i * 0.6, y + 0.2, 0.91, 0.3, 0.2, 0.14, GOODS[(i + 2) % len(GOODS)])
    # The awning, in stripes, sticking out over the customers
    for i in range(8):
        mesh.box(x - 0.2 + i * 0.3, y - 0.3, 2.0, 0.3, 1.9, 0.1, stripes if i % 2 else AWNING[name][1])
    # A sign board hanging under the awning's front edge, in a dark shade of the awning's stripes, with a light trim
    board = tuple(int(c * 0.55) for c in stripes)
    mesh.box(x - 0.1, y - 0.33, 1.5, 2.2, 0.04, 0.4, board)
    for trim_x, trim_z, trim_w, trim_h in ((x - 0.12, 1.48, 2.24, 0.03), (x - 0.12, 1.88, 2.24, 0.03),
                                           (x - 0.12, 1.5, 0.03, 0.4), (x + 2.09, 1.5, 0.03, 0.4)):
        mesh.box(trim_x, y - 0.345, trim_z, trim_w, 0.012, trim_h, TRIM)
    node = mesh.build(f"kiosk-{name}")
    node.reparentTo(render)

    # The name is set flat on the board, facing the customers, and shrunk to fit if it is long. Lit evenly, so it stays readable.
    text = TextNode(f"sign-{name}")
    text.setText(kiosk["name"])
    text.setAlign(TextNode.ACenter)
    text.setTextColor(*[c / 255 for c in TEXT], 1)
    text.setShadow(0.04, 0.04)
    text.setShadowColor(0, 0, 0, 0.5)
    scale = min(SIGN_SCALE, SIGN_WIDTH / max(text.getWidth(), 1e-3))
    sign = render.attachNewNode(text)
    sign.setPos(x + 1.0, y - 0.355, 1.63)
    sign.setScale(scale)
    sign.setLightOff()
    return node, sign


def build_kiosks(render):
    """Builds every kiosk, with a shopkeeper behind each counter. Returns the shopkeepers' bodies, for their faces."""
    shopkeepers = []
    for name, kiosk in KIOSKS.items():
        build_kiosk(render, name, kiosk)
        body = build_body(render, f"shopkeeper-{name}", SHOPKEEPER_COAT[name], (240, 240, 235))
        body.node.setPos(kiosk["x"] + 1.0, kiosk["y"] + 0.9, 0)
        body.node.setH(180)  # Facing the customers, across the counter
        body.pose("counter")
        body.set_expression("smile")
        shopkeepers.append(body)
    return shopkeepers
