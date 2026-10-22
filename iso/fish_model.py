"""The fish models. They follow the original fish from fish.py: the same tail shapes, dorsal fins, marks and extras.
Each fish is built as one root with its tail and fins on their own pivots, so the swimming can wag and flap them."""
from iso.mesh import MeshBuilder

FISH_DIM = 0.7  # Fish are darker than their colour, as if seen through the water
TILE_PX = 40  # Pixels per tile, so the fish sizes from fish.py fit the tile world
BLACK = (20, 20, 20)
WHITE = (250, 250, 250)


def shade(colour, amount):
    return tuple(int(c * amount) for c in colour)


def double_sided(mesh, a, b, c, colour):
    """A flat triangle drawn from both sides, so fins stay visible from any angle."""
    ux, uy, uz = (b[i] - a[i] for i in range(3))
    vx, vy, vz = (c[i] - a[i] for i in range(3))
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    length = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5 or 1
    n = tuple(v / length for v in n)
    mesh.quad([a, b, c, c], n, colour)
    mesh.quad([a, b, c, c], tuple(-v for v in n), colour)


def tail_mesh(length, height, style, fin):
    """The tail, built around its own pivot at the base of the tail, so it can wag from side to side.
    Round, crescent and forked tails match the side-view tail shapes."""
    mesh = MeshBuilder()
    tip = -length * 0.22
    if style == "round":
        mesh.ellipsoid(-length * 0.08, 0, 0, length * 0.1, height * 0.3, height * 0.4, fin, steps=4)
    else:
        notch = 0.2 if style == "crescent" else 0.5  # A crescent has a deeper notch than a forked tail
        base = (length * 0.02, 0, 0)
        top = (tip, 0, height * 0.6)
        bottom = (tip, 0, -height * 0.6)
        notched = (tip * notch, 0, 0)
        double_sided(mesh, base, top, notched, fin)
        double_sided(mesh, base, notched, bottom, fin)
    return mesh.build("tail_fin")


def dorsal_mesh(dorsal, length, height, fin):
    """The back fin for this species, as in the side view, built on the body's top edge."""
    mesh = MeshBuilder()
    top = height * 0.9
    if dorsal == "spiny":
        double_sided(mesh, (length * 0.0, 0, top), (length * 0.1, 0, height * 1.4), (length * 0.2, 0, top), fin)
    elif dorsal == "long":
        double_sided(mesh, (length * -0.25, 0, top), (length * -0.1, 0, height * 1.3), (length * 0.3, 0, top), fin)
    elif dorsal in ("split", "two"):
        for start in (-0.1, 0.1):
            double_sided(mesh, (length * start, 0, top), (length * (start + 0.08), 0, height * 1.3), (length * (start + 0.16), 0, top), fin)
    elif dorsal == "small":
        double_sided(mesh, (length * 0.1, 0, top), (length * 0.15, 0, height * 1.1), (length * 0.2, 0, top), fin)
    return mesh.build("dorsal")


def sail_mesh(length, height, fin):
    """The sailfish's sail. Its own node, so it can be raised when the fish bursts after bait."""
    mesh = MeshBuilder()
    double_sided(mesh, (length * -0.2, 0, height * 0.9), (length * 0.0, 0, height * 2.0), (length * 0.2, 0, height * 0.9), fin)
    return mesh.build("sail")


def marks_mesh(mesh, look, length, height, mark):
    """Spots, bars, stripes, blotches, wavy lines and scales on the flanks, on both sides of the body, drawn into the body's mesh."""
    style = look.get("marks", "none")
    for side in (-1, 1):
        y = side * height * 0.5
        if style == "spots":
            for f, v in ((0.2, -0.2), (0.32, 0.1), (0.45, -0.25), (0.5, 0.15), (0.62, -0.05), (0.7, -0.22), (0.78, 0.12), (0.4, 0.3)):
                mesh.ellipsoid(-length / 2 + length * f, y * 0.95, height * (0.5 + v * 0.5), 0.02, 0.01, 0.02, mark, steps=3)
        elif style == "bars":
            for f in (0.3, 0.42, 0.54, 0.66):
                mesh.box(-length / 2 + length * f, y * 0.98, height * 0.1, 0.02, 0.01, height * 0.8, mark)
        elif style == "stripes":
            for v in (-0.2, 0, 0.2):
                mesh.box(-length / 2 + length * 0.15, y * 0.98, height * (0.5 + v * 0.5), length * 0.75, 0.01, 0.01, mark)
        elif style == "blotches":
            for f in (0.3, 0.45, 0.6, 0.75):
                mesh.ellipsoid(-length / 2 + length * f, y * 0.97, height * 0.5, length * 0.05, 0.01, height * 0.15, mark, steps=3)
        elif style == "wavy":
            for i, f in enumerate((0.2, 0.3, 0.4, 0.5, 0.6, 0.7)):
                mesh.box(-length / 2 + length * f, y * 0.98, height * (0.75 if i % 2 else 0.9), length * 0.04, 0.01, height * 0.2, mark)
        elif style == "gold_stripe":
            mesh.box(-length / 2 + length * 0.12, y * 0.98, height * 0.5, length * 0.78, 0.01, 0.02, (250, 205, 60))
        elif style == "scales":
            for row in range(3):
                for col in range(5):
                    mesh.ellipsoid(-length / 2 + length * (0.25 + col * 0.12), y * 0.98, height * (0.25 + row * 0.25), 0.02, 0.01, 0.02, mark, steps=3)


def extras_mesh(mesh, look, length, height, mark):
    """Features on the head and the gills, such as barbels, a big mouth, a gill flap and a gill spot, drawn into the body's mesh."""
    extras = look.get("extras", [])
    for side in (-1, 1):
        y = side * height * 0.5
        if "gill" in extras:
            mesh.ellipsoid(-length / 2 + length * 0.8, y, height * 0.5, length * 0.04, 0.01, height * 0.25, mark, steps=3)
        if "gill_spot" in extras:
            mesh.ellipsoid(-length / 2 + length * 0.75, y, height * 0.6, 0.03, 0.01, 0.03, mark, steps=3)
        if "barbels" in extras:
            mesh.box(length / 2 - 0.02, side * height * 0.25, -height * 0.1, 0.02, 0.02, height * 0.4, mark)
    if "big_mouth" in extras:
        mesh.box(length / 2 - length * 0.2, -height * 0.25, height * 0.2, length * 0.2, 0.01, 0.02, BLACK)
        mesh.box(length / 2 - length * 0.2, height * 0.25, height * 0.2, length * 0.2, 0.01, 0.02, BLACK)


def build_fish(render, fish):
    """A fish seen from its side, long along X and facing +X. Returns the root, the tail pivot, the two fin pivots
    and the sail (or None), so the swimming can wag the tail, flap the fins and raise the sail."""
    length = min(1.4, max(0.35, fish.width / TILE_PX * 0.5))
    height = min(0.5, max(0.14, fish.height / TILE_PX * 0.5))
    body_colour = shade(fish.color, FISH_DIM)
    belly = shade(fish.belly or fish.color, FISH_DIM * 1.15)  # The belly is lighter, as sunlight comes down through the water
    back = shade(fish.color, FISH_DIM * 0.7)  # The back is darker, so the fish reads as lit from above
    fin = shade(fish.color, FISH_DIM * 0.85)
    mark = shade(fish.color, FISH_DIM * 0.5)
    look = fish.look
    extras = look.get("extras", [])
    body = MeshBuilder()

    # Body in three bands: dark back, flank, light belly
    body.ellipsoid(0, 0, height / 2, length / 2, height / 2, height / 2, body_colour, steps=7)
    body.ellipsoid(0, 0, height * 0.1, length * 0.42, height * 0.38, height * 0.26, belly, steps=5)
    body.ellipsoid(length * 0.04, 0, height * 0.78, length * 0.36, height * 0.2, height * 0.16, back, steps=4)
    # A snout that tapers to the front
    body.ellipsoid(length * 0.42, 0, height * 0.42, length * 0.1, height * 0.3, height * 0.3, body_colour, steps=4)
    # Anal fin underneath, and a pectoral fin on each side, which are common to every species
    double_sided(body, (length * 0.25, 0, height * 0.1), (length * 0.35, 0, -height * 0.3), (length * 0.45, 0, height * 0.1), fin)

    # The top fin is on its own pivot for the sail, and the others are part of the body
    sail = None
    dorsal = look.get("dorsal")
    if dorsal == "sail":
        sail = sail_mesh(length, height, fin)
    if "finlets" in extras:
        for x in (-length * 0.4, -length * 0.3):
            double_sided(body, (x, 0, height * 0.2), (x + 0.02, 0, height * 0.6), (x + 0.04, 0, height * 0.2), fin)
    if "bill" in extras:
        double_sided(body, (length * 0.5, 0, height * 0.5), (length * 0.85, 0, height * 0.5), (length * 0.5, 0, height * 0.4), fin)

    marks_mesh(body, look, length, height, mark)
    extras_mesh(body, look, length, height, mark)

    # Eyes: a white ball with a dark pupil, so they catch the light
    for side in (-1, 1):
        body.ellipsoid(length * 0.36, side * height * 0.42, height * 0.6, 0.04, 0.03, 0.04, WHITE, steps=3)
        body.ellipsoid(length * 0.37, side * height * 0.46, height * 0.6, 0.022, 0.02, 0.022, BLACK, steps=3)

    root = render.attachNewNode("fish")
    body.build("fish_body").reparentTo(root)
    dorsal_node = dorsal_mesh(dorsal, length, height, fin)
    dorsal_node.reparentTo(root)

    tail = root.attachNewNode("tail")
    tail.setPos(-length / 2, 0, height / 2)
    tail_mesh(length, height, look.get("tail", "fork"), fin).reparentTo(tail)

    if sail is not None:
        sail_node = root.attachNewNode("sail")
        sail_node.setPos(0, 0, 0)
        sail.reparentTo(sail_node)
    else:
        sail_node = None

    fins = []
    for side in (-1, 1):
        pivot = root.attachNewNode("pectoral")
        pivot.setPos(length * 0.12, side * height * 0.35, height * 0.3)
        mesh = MeshBuilder()
        double_sided(mesh, (0, 0, 0), (-length * 0.1, side * height * 0.3, -height * 0.1), (length * 0.04, side * height * 0.06, -height * 0.25), fin)
        mesh.build("pectoral_fin").reparentTo(pivot)
        fins.append(pivot)
    return root, tail, fins, sail_node
